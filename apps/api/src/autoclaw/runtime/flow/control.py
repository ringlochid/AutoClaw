from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload
from sqlalchemy.sql.elements import ColumnElement

from autoclaw.persistence.models import (
    AttemptModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    FlowWaitModel,
    HumanRequestModel,
    TransientLocalizationModel,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.command_run.service import request_command_run_cancellation
from autoclaw.runtime.contracts import (
    HumanRequestResolutionSurface,
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    TaskEventSource,
    TaskEventType,
)
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime.dispatch.preparation import DispatchOpeningDependencies
from autoclaw.runtime.errors import (
    RuntimeOperationError,
    illegal_state_error,
    missing_resource_error,
    stale_flow_revision_error,
)
from autoclaw.runtime.flow.continuation import continue_paused_flow
from autoclaw.runtime.flow.reads import read_runtime_flow
from autoclaw.runtime.post_commit import (
    CommandRunCancellationRequested,
    DispatchCleanupRequested,
    HumanRequestTerminal,
    RuntimeEffectPublisher,
    RuntimeEffectSignal,
    TransientCleanupRequested,
)
from autoclaw.runtime.task_events import append_task_event

logger = logging.getLogger(__name__)


async def pause_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    expected_control_revision: int,
    actor_ref: str | None = None,
    event_source: TaskEventSource = TaskEventSource.CONTROL_API,
    runtime_effect_publisher: RuntimeEffectPublisher | None = None,
    clock: Callable[[], datetime] = utc_now,
) -> RuntimeFlowPauseResponse:
    """Pause one exact running flow while retaining any external wait."""

    flow = await _read_control_flow(session, task_id)
    _require_control_snapshot(
        flow,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
        expected_control_revision=expected_control_revision,
        allowed_statuses={"running"},
    )
    paused_at = clock()
    closed_dispatch_id = await _close_current_dispatch(
        session,
        flow=flow,
        closed_reason="paused",
        closed_at=paused_at,
    )
    changed = await _update_flow_to_paused(
        session,
        flow=flow,
        expected_control_revision=expected_control_revision,
        actor_ref=actor_ref,
        paused_at=paused_at,
    )
    if not changed:
        await session.rollback()
        raise _flow_control_conflict("another controller transition won before pause")
    await append_task_event(
        session,
        task_id=flow.task_id,
        event_type=TaskEventType.TASK_PAUSED,
        event_source=event_source,
        occurred_at=paused_at,
        flow_revision_id=expected_active_flow_revision_id,
        dispatch_id=closed_dispatch_id,
        actor_ref=actor_ref,
        payload={
            "pause_reason": "paused_by_operator",
            "control_revision": expected_control_revision + 1,
        },
    )
    await _commit_or_rollback(session)
    _publish_cleanup(runtime_effect_publisher, closed_dispatch_id)
    return RuntimeFlowPauseResponse(flow=await read_runtime_flow(session, task_id))


async def continue_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    expected_control_revision: int,
    dependencies: DispatchOpeningDependencies,
    actor_ref: str | None = None,
    event_source: TaskEventSource = TaskEventSource.CONTROL_API,
) -> RuntimeFlowRead:
    """Open one exact paused-flow successor before returning."""

    flow = await _read_control_flow(session, task_id)
    _require_control_snapshot(
        flow,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
        expected_control_revision=expected_control_revision,
        allowed_statuses={"paused"},
    )
    result = await continue_paused_flow(
        session,
        task_id=task_id,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
        expected_control_revision=expected_control_revision,
        dependencies=dependencies,
    )
    if result.outcome != "opened" or result.dispatch_id is None:
        raise _flow_control_conflict("paused flow did not open one successor")
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.TASK_RESUMED,
        event_source=event_source,
        flow_revision_id=expected_active_flow_revision_id,
        dispatch_id=result.dispatch_id,
        actor_ref=actor_ref,
        payload={"control_revision": expected_control_revision + 1},
    )
    await _commit_or_rollback(session)
    return await read_runtime_flow(session, task_id)


async def cancel_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    expected_control_revision: int,
    actor_ref: str | None = None,
    event_source: TaskEventSource = TaskEventSource.CONTROL_API,
    runtime_effect_publisher: RuntimeEffectPublisher | None = None,
    clock: Callable[[], datetime] = utc_now,
) -> RuntimeFlowRead:
    """Cancel one exact nonterminal flow without opening a successor."""

    flow = await _read_control_flow(session, task_id)
    _require_control_snapshot(
        flow,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
        expected_control_revision=expected_control_revision,
        allowed_statuses={"running", "paused"},
    )
    cancelled_at = clock()
    closed_dispatch_id = await _close_current_dispatch(
        session,
        flow=flow,
        closed_reason="cancelled",
        closed_at=cancelled_at,
    )
    human_signal, command_signal = await _cancel_external_wait(
        session,
        flow=flow,
        actor_ref=actor_ref,
        event_source=event_source,
        cancelled_at=cancelled_at,
    )
    await _cancel_execution_rows(session, flow=flow, cancelled_at=cancelled_at)
    changed = await _update_flow_to_cancelled(
        session,
        flow=flow,
        expected_control_revision=expected_control_revision,
        cancelled_at=cancelled_at,
    )
    if not changed:
        await session.rollback()
        raise _flow_control_conflict("another controller transition won before cancellation")
    await append_task_event(
        session,
        task_id=flow.task_id,
        event_type=TaskEventType.TASK_CANCELLED,
        event_source=event_source,
        occurred_at=cancelled_at,
        flow_revision_id=expected_active_flow_revision_id,
        dispatch_id=closed_dispatch_id,
        actor_ref=actor_ref,
        payload={"control_revision": expected_control_revision + 1},
    )
    transient_cleanup_signals = await _read_expired_transient_cleanup_signals(
        session,
        task_id=flow.task_id,
    )
    await _commit_or_rollback(session)
    _publish_cleanup(runtime_effect_publisher, closed_dispatch_id)
    _publish_human_terminal(runtime_effect_publisher, human_signal)
    _publish_command_cancellation(runtime_effect_publisher, command_signal)
    _publish_transient_cleanup(runtime_effect_publisher, transient_cleanup_signals)
    return await read_runtime_flow(session, task_id)


async def _read_control_flow(session: AsyncSession, task_id: str) -> FlowModel:
    flow = await session.scalar(
        select(FlowModel)
        .options(raiseload("*"))
        .where(FlowModel.task_id == task_id)
        .execution_options(populate_existing=True)
    )
    if flow is None:
        raise missing_resource_error(f"unknown task_id '{task_id}'")
    return flow


def _require_control_snapshot(
    flow: FlowModel,
    *,
    expected_active_flow_revision_id: str,
    expected_control_revision: int,
    allowed_statuses: set[str],
) -> None:
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise stale_flow_revision_error("the active flow revision changed before control")
    if flow.control_revision != expected_control_revision:
        raise _flow_control_conflict("the flow control revision changed before control")
    if flow.status not in allowed_statuses:
        raise _flow_control_conflict(f"flow cannot be controlled from status '{flow.status}'")


async def _close_current_dispatch(
    session: AsyncSession,
    *,
    flow: FlowModel,
    closed_reason: str,
    closed_at: datetime,
) -> str | None:
    if flow.current_dispatch_id is None:
        return None
    closed_dispatch_id = await session.scalar(
        update(DispatchTurnModel)
        .where(
            DispatchTurnModel.dispatch_id == flow.current_dispatch_id,
            DispatchTurnModel.task_id == flow.task_id,
            DispatchTurnModel.flow_id == flow.flow_id,
            DispatchTurnModel.status.in_(("starting", "open")),
        )
        .values(
            status="closed",
            closed_at=closed_at,
            closed_reason=closed_reason,
            next_provider_start_at=None,
            provider_start_retry_kind=None,
        )
        .returning(DispatchTurnModel.dispatch_id)
    )
    if closed_dispatch_id is None:
        await session.rollback()
        raise _flow_control_conflict("the current dispatch changed before control")
    return closed_dispatch_id


async def _update_flow_to_paused(
    session: AsyncSession,
    *,
    flow: FlowModel,
    expected_control_revision: int,
    actor_ref: str | None,
    paused_at: datetime,
) -> bool:
    return bool(
        await session.scalar(
            update(FlowModel)
            .where(*_flow_snapshot_conditions(flow, expected_control_revision))
            .values(
                status="paused",
                current_dispatch_id=None,
                pause_reason="paused_by_operator",
                pause_details={"summary": "Paused by operator."},
                paused_at=paused_at,
                paused_by_actor_ref=actor_ref,
                control_revision=FlowModel.control_revision + 1,
                updated_at=paused_at,
            )
            .returning(FlowModel.flow_id)
        )
    )


async def _update_flow_to_cancelled(
    session: AsyncSession,
    *,
    flow: FlowModel,
    expected_control_revision: int,
    cancelled_at: datetime,
) -> bool:
    return bool(
        await session.scalar(
            update(FlowModel)
            .where(*_flow_snapshot_conditions(flow, expected_control_revision))
            .values(
                status="cancelled",
                terminal_outcome=None,
                current_dispatch_id=None,
                waiting_cause="none",
                waiting_source_id=None,
                pause_reason=None,
                pause_details=None,
                paused_at=None,
                paused_by_actor_ref=None,
                control_revision=FlowModel.control_revision + 1,
                updated_at=cancelled_at,
            )
            .returning(FlowModel.flow_id)
        )
    )


def _flow_snapshot_conditions(
    flow: FlowModel, expected_control_revision: int
) -> tuple[ColumnElement[bool], ...]:
    current_condition = (
        FlowModel.current_dispatch_id.is_(None)
        if flow.current_dispatch_id is None
        else FlowModel.current_dispatch_id == flow.current_dispatch_id
    )
    source_condition = (
        FlowModel.waiting_source_id.is_(None)
        if flow.waiting_source_id is None
        else FlowModel.waiting_source_id == flow.waiting_source_id
    )
    return (
        FlowModel.flow_id == flow.flow_id,
        FlowModel.task_id == flow.task_id,
        FlowModel.status == flow.status,
        FlowModel.active_flow_revision_id == flow.active_flow_revision_id,
        FlowModel.control_revision == expected_control_revision,
        current_condition,
        FlowModel.waiting_cause == flow.waiting_cause,
        source_condition,
    )


async def _cancel_external_wait(
    session: AsyncSession,
    *,
    flow: FlowModel,
    actor_ref: str | None,
    event_source: TaskEventSource,
    cancelled_at: datetime,
) -> tuple[HumanRequestTerminal | None, CommandRunCancellationRequested | None]:
    wait = await session.scalar(
        select(FlowWaitModel).options(raiseload("*")).where(FlowWaitModel.flow_id == flow.flow_id)
    )
    if flow.waiting_cause == "none":
        if wait is not None or flow.waiting_source_id is not None:
            raise illegal_state_error("flow wait authority is inconsistent")
        return None, None
    if wait is None or flow.waiting_source_id is None:
        raise illegal_state_error("flow wait authority is incomplete")
    human_signal: HumanRequestTerminal | None = None
    command_signal: CommandRunCancellationRequested | None = None
    if flow.waiting_cause == "human_request":
        request_id = await _cancel_human_request(
            session,
            flow=flow,
            wait=wait,
            actor_ref=actor_ref,
            event_source=event_source,
            cancelled_at=cancelled_at,
        )
        human_signal = HumanRequestTerminal(request_id=request_id)
    elif flow.waiting_cause == "command_run":
        command_signal = await _request_waiting_command_cancellation(
            session,
            flow=flow,
            wait=wait,
            actor_ref=actor_ref,
            event_source=event_source,
        )
    else:
        raise illegal_state_error(f"unsupported flow waiting cause '{flow.waiting_cause}'")
    await session.execute(delete(FlowWaitModel).where(FlowWaitModel.flow_id == flow.flow_id))
    return human_signal, command_signal


async def _cancel_human_request(
    session: AsyncSession,
    *,
    flow: FlowModel,
    wait: FlowWaitModel,
    actor_ref: str | None,
    event_source: TaskEventSource,
    cancelled_at: datetime,
) -> str:
    request_id = wait.human_request_id
    if request_id is None or request_id != flow.waiting_source_id:
        raise illegal_state_error("flow human-request wait source is inconsistent")
    changed = await session.scalar(
        update(HumanRequestModel)
        .where(
            HumanRequestModel.request_id == request_id,
            HumanRequestModel.task_id == flow.task_id,
            HumanRequestModel.flow_id == flow.flow_id,
            HumanRequestModel.status == "open",
        )
        .values(
            status="cancelled",
            resolution_kind="cancelled",
            item_responses_json=None,
            resolution_policy_basis_json=None,
            resolution_summary="Cancelled because the task was cancelled.",
            resolved_by_actor_ref=actor_ref,
            resolved_by_surface=_human_resolution_surface(event_source).value,
            resolved_at=cancelled_at,
        )
        .returning(HumanRequestModel.request_id)
    )
    if changed is None:
        raise _flow_control_conflict("the waiting human request changed before task cancellation")
    await append_task_event(
        session,
        task_id=flow.task_id,
        event_type=TaskEventType.HUMAN_REQUEST_CANCELLED,
        event_source=event_source,
        occurred_at=cancelled_at,
        flow_revision_id=flow.active_flow_revision_id,
        dispatch_id=wait.source_dispatch_id,
        actor_ref=actor_ref,
        payload={"request_id": request_id, "resolution_kind": "cancelled"},
    )
    return request_id


async def _request_waiting_command_cancellation(
    session: AsyncSession,
    *,
    flow: FlowModel,
    wait: FlowWaitModel,
    actor_ref: str | None,
    event_source: TaskEventSource,
) -> CommandRunCancellationRequested | None:
    run_id = wait.command_run_id
    if run_id is None or run_id != flow.waiting_source_id:
        raise illegal_state_error("flow command-run wait source is inconsistent")
    source, changed = await request_command_run_cancellation(
        session,
        task_id=flow.task_id,
        run_id=run_id,
        actor_ref=actor_ref,
        event_source=event_source,
        is_already_requested_allowed=True,
    )
    if not changed:
        return None
    return CommandRunCancellationRequested(
        run_id=source.run_id,
        ownership_revision=source.ownership_revision,
    )


async def _cancel_execution_rows(
    session: AsyncSession,
    *,
    flow: FlowModel,
    cancelled_at: datetime,
) -> None:
    await session.execute(
        update(AttemptModel)
        .where(
            AttemptModel.flow_id == flow.flow_id,
            AttemptModel.status.in_(("pending", "running")),
        )
        .values(status="cancelled", terminal_outcome=None, closed_at=cancelled_at)
    )
    await session.execute(
        update(FlowNodeModel)
        .where(
            FlowNodeModel.flow_id == flow.flow_id,
            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
            FlowNodeModel.state.in_(("ready", "running", "waiting", "paused")),
        )
        .values(state="cancelled")
    )


async def _read_expired_transient_cleanup_signals(
    session: AsyncSession,
    *,
    task_id: str,
) -> tuple[TransientCleanupRequested, ...]:
    rows = tuple(
        (
            await session.execute(
                select(
                    TransientLocalizationModel.transient_localization_id,
                    TransientLocalizationModel.expires_at,
                )
                .where(
                    TransientLocalizationModel.task_id == task_id,
                    TransientLocalizationModel.retention_status == "expired",
                )
                .order_by(TransientLocalizationModel.transient_localization_id)
            )
        ).all()
    )
    signals: list[TransientCleanupRequested] = []
    for transient_localization_id, expires_at in rows:
        if expires_at is None:
            raise illegal_state_error(
                f"expired transient '{transient_localization_id}' has no retention generation"
            )
        signals.append(
            TransientCleanupRequested(
                transient_localization_id=transient_localization_id,
                expires_at=expires_at,
            )
        )
    return tuple(signals)


def _human_resolution_surface(event_source: TaskEventSource) -> HumanRequestResolutionSurface:
    if event_source == TaskEventSource.OPERATOR_MCP:
        return HumanRequestResolutionSurface.OPERATOR_MCP
    if event_source == TaskEventSource.CONTROL_API:
        return HumanRequestResolutionSurface.CONTROL_API
    return HumanRequestResolutionSurface.CONTROLLER


async def _commit_or_rollback(session: AsyncSession) -> None:
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise


def _publish_cleanup(
    publisher: RuntimeEffectPublisher | None,
    dispatch_id: str | None,
) -> None:
    if publisher is None or dispatch_id is None:
        return
    _publish_effect(publisher, DispatchCleanupRequested(dispatch_id=dispatch_id))


def _publish_command_cancellation(
    publisher: RuntimeEffectPublisher | None,
    signal: CommandRunCancellationRequested | None,
) -> None:
    if publisher is None or signal is None:
        return
    _publish_effect(publisher, signal)


def _publish_human_terminal(
    publisher: RuntimeEffectPublisher | None,
    signal: HumanRequestTerminal | None,
) -> None:
    if publisher is None or signal is None:
        return
    _publish_effect(publisher, signal)


def _publish_transient_cleanup(
    publisher: RuntimeEffectPublisher | None,
    signals: tuple[TransientCleanupRequested, ...],
) -> None:
    if publisher is None:
        return
    for signal in signals:
        _publish_effect(publisher, signal)


def _publish_effect(publisher: RuntimeEffectPublisher, signal: RuntimeEffectSignal) -> None:
    try:
        publisher.publish(signal)
    except Exception:
        logger.exception("post-commit flow-control signal publication failed")


def _flow_control_conflict(summary: str) -> RuntimeOperationError:
    return RuntimeOperationError(
        code=OperationFailureCode.CONFLICT,
        summary=summary,
        is_retryable=False,
        suggested_next_step="Reread the task and retry only against its current revisions.",
    )


__all__ = ["cancel_flow", "continue_flow", "pause_flow"]
