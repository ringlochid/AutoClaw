from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import DispatchTurnModel, FlowModel
from autoclaw.runtime.contracts import TaskEventSource, TaskEventType
from autoclaw.runtime.dispatch.opening import StartingDispatchBasis, stage_starting_dispatch
from autoclaw.runtime.dispatch.preparation import (
    DispatchOpeningDependencies,
    PreparedDispatchRequest,
    prepare_dispatch_request,
)
from autoclaw.runtime.dispatch.prompt_snapshot import build_ordinary_dispatch_request
from autoclaw.runtime.post_commit import (
    DispatchCleanupRequested,
    WatchdogDue,
)
from autoclaw.runtime.providers import ProviderResolutionError
from autoclaw.runtime.task_events import append_task_event
from autoclaw.runtime.watchdog.context import (
    WatchdogRecoverySnapshot,
    dispatch_owns_external_source,
    read_watchdog_recovery_snapshot,
)
from autoclaw.runtime.watchdog.deadline import calculate_watchdog_due_at
from autoclaw.runtime.watchdog.predicates import (
    dispatch_has_no_external_source,
    dispatch_has_no_successor,
    nullable_datetime_matches,
    watchdog_context_is_current,
    watchdog_replacement_count_matches,
)

type WatchdogDueHandler = Callable[[AsyncSession, WatchdogDue], Awaitable[None]]
type WatchdogRecoveryOutcome = Literal["opened", "skipped", "paused"]


@dataclass(frozen=True, slots=True)
class WatchdogRecoveryResult:
    outcome: WatchdogRecoveryOutcome
    dispatch_id: str | None = None


def create_watchdog_due_handler(
    dependencies: DispatchOpeningDependencies,
) -> WatchdogDueHandler:
    """Create the exact stale-dispatch recovery route."""

    async def handle(session: AsyncSession, signal: WatchdogDue) -> None:
        await recover_stale_dispatch(
            session,
            signal=signal,
            dependencies=dependencies,
        )

    return handle


async def recover_stale_dispatch(
    session: AsyncSession,
    *,
    signal: WatchdogDue,
    dependencies: DispatchOpeningDependencies,
) -> WatchdogRecoveryResult:
    """Conditionally replace one exact stale dispatch or pause on its recovery cap."""

    observed_at = dependencies.clock()
    candidate_dispatch_id = f"dispatch.{uuid4().hex}"
    timeout_seconds = dependencies.settings.runtime.watchdog_inactivity_timeout_seconds
    replacement_limit = dependencies.settings.runtime.watchdog_same_attempt_replacement_limit
    try:
        snapshot = await read_watchdog_recovery_snapshot(
            session,
            signal=signal,
            candidate_dispatch_id=candidate_dispatch_id,
            dependencies=dependencies,
            now=observed_at,
            inactivity_timeout_seconds=timeout_seconds,
        )
        if snapshot is None:
            await session.rollback()
            return WatchdogRecoveryResult(outcome="skipped")
        if snapshot.same_attempt_replacement_count >= replacement_limit:
            await session.rollback()
            committed = await _pause_watchdog_snapshot(
                session,
                snapshot=snapshot,
                paused_at=dependencies.clock(),
                pause_reason="runtime_recovery_exhausted",
                failure_code=None,
            )
            if not committed:
                return WatchdogRecoveryResult(outcome="skipped")
            _publish_cleanup(dependencies, signal.dispatch_id)
            return WatchdogRecoveryResult(outcome="paused")

        request = build_ordinary_dispatch_request(snapshot.dispatch.prompt)
        await session.rollback()
        prepared = prepare_dispatch_request(
            dependencies=dependencies,
            paths=snapshot.dispatch.paths,
            dispatch_id=candidate_dispatch_id,
            due_at=dependencies.clock(),
            provider=snapshot.dispatch.provider,
            capabilities=snapshot.dispatch.capabilities,
            request=request,
        )
    except (ProviderResolutionError, ValueError, OSError) as exc:
        await session.rollback()
        failure_code = str(getattr(exc, "code", "watchdog_dispatch_preparation_failed"))
        committed = await _pause_failed_watchdog_signal(
            session,
            signal=signal,
            paused_at=dependencies.clock(),
            inactivity_timeout_seconds=timeout_seconds,
            failure_code=failure_code,
        )
        if committed:
            _publish_cleanup(dependencies, signal.dispatch_id)
            return WatchdogRecoveryResult(outcome="paused")
        return WatchdogRecoveryResult(outcome="skipped")

    committed = await _commit_watchdog_replacement(
        session,
        snapshot=snapshot,
        prepared=prepared,
        committed_at=dependencies.clock(),
    )
    if not committed:
        return WatchdogRecoveryResult(outcome="skipped")
    _publish_dispatch_start(dependencies, prepared)
    return WatchdogRecoveryResult(outcome="opened", dispatch_id=prepared.dispatch_id)


async def _commit_watchdog_replacement(
    session: AsyncSession,
    *,
    snapshot: WatchdogRecoverySnapshot,
    prepared: PreparedDispatchRequest,
    committed_at: datetime,
) -> bool:
    dispatch = snapshot.dispatch
    prompt = dispatch.prompt
    if _as_utc(committed_at) < snapshot.authoritative_due_at:
        await session.rollback()
        return False

    closed_dispatch_id = await session.scalar(
        update(DispatchTurnModel)
        .where(
            DispatchTurnModel.dispatch_id == prompt.predecessor_dispatch_id,
            DispatchTurnModel.task_id == prompt.task_id,
            DispatchTurnModel.flow_id == prompt.flow_id,
            DispatchTurnModel.assignment_id == prompt.assignment_id,
            DispatchTurnModel.attempt_id == prompt.attempt_id,
            DispatchTurnModel.node_key == prompt.node_key,
            DispatchTurnModel.status == "open",
            DispatchTurnModel.adapter_started_at == snapshot.adapter_started_at,
            nullable_datetime_matches(
                DispatchTurnModel.last_node_activity_at,
                snapshot.last_node_activity_at,
            ),
            DispatchTurnModel.node_activity_revision == snapshot.activity_revision,
            watchdog_context_is_current(snapshot),
            watchdog_replacement_count_matches(snapshot),
            dispatch_has_no_external_source(prompt.predecessor_dispatch_id),
            dispatch_has_no_successor(prompt.predecessor_dispatch_id),
        )
        .values(
            status="closed",
            closed_at=committed_at,
            closed_reason="watchdog_superseded",
            next_provider_start_at=None,
            provider_start_retry_kind=None,
        )
        .returning(DispatchTurnModel.dispatch_id)
    )
    if closed_dispatch_id is None:
        await session.rollback()
        return False

    updated_flow_id = await session.scalar(
        update(FlowModel)
        .where(
            FlowModel.flow_id == prompt.flow_id,
            FlowModel.task_id == prompt.task_id,
            FlowModel.compiled_plan_id == dispatch.compiled_plan_id,
            FlowModel.status == "running",
            FlowModel.active_flow_revision_id == prompt.flow_revision_id,
            FlowModel.current_dispatch_id == prompt.predecessor_dispatch_id,
            FlowModel.waiting_cause == "none",
            FlowModel.control_revision == dispatch.flow_control_revision,
            watchdog_replacement_count_matches(snapshot),
            dispatch_has_no_external_source(prompt.predecessor_dispatch_id),
            dispatch_has_no_successor(prompt.predecessor_dispatch_id),
        )
        .values(
            current_dispatch_id=prepared.dispatch_id,
            control_revision=FlowModel.control_revision + 1,
            updated_at=committed_at,
        )
        .returning(FlowModel.flow_id)
    )
    if updated_flow_id is None:
        await session.rollback()
        return False

    stage_starting_dispatch(
        session,
        basis=StartingDispatchBasis(
            task_id=prompt.task_id,
            flow_id=prompt.flow_id,
            assignment_id=prompt.assignment_id,
            attempt_id=prompt.attempt_id,
            node_key=prompt.node_key,
            opened_reason="watchdog_recovery",
            predecessor_dispatch_id=prompt.predecessor_dispatch_id,
            flow_start_source_flow_id=None,
        ),
        prepared=prepared,
    )
    await append_task_event(
        session,
        task_id=prompt.task_id,
        event_type=TaskEventType.DISPATCH_OPENED,
        event_source=TaskEventSource.CONTROLLER,
        occurred_at=committed_at,
        flow_revision_id=prompt.flow_revision_id,
        dispatch_id=prepared.dispatch_id,
        attempt_id=prompt.attempt_id,
        node_key=prompt.node_key,
        payload={
            "opened_reason": "watchdog_recovery",
            "predecessor_dispatch_id": prompt.predecessor_dispatch_id,
            "recovery_count": snapshot.same_attempt_replacement_count + 1,
            "status": "starting",
        },
    )
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return True


async def _pause_watchdog_snapshot(
    session: AsyncSession,
    *,
    snapshot: WatchdogRecoverySnapshot,
    paused_at: datetime,
    pause_reason: str,
    failure_code: str | None,
) -> bool:
    dispatch = snapshot.dispatch
    prompt = dispatch.prompt
    closed_dispatch_id = await session.scalar(
        update(DispatchTurnModel)
        .where(
            DispatchTurnModel.dispatch_id == prompt.predecessor_dispatch_id,
            DispatchTurnModel.task_id == prompt.task_id,
            DispatchTurnModel.flow_id == prompt.flow_id,
            DispatchTurnModel.assignment_id == prompt.assignment_id,
            DispatchTurnModel.attempt_id == prompt.attempt_id,
            DispatchTurnModel.status == "open",
            DispatchTurnModel.adapter_started_at == snapshot.adapter_started_at,
            nullable_datetime_matches(
                DispatchTurnModel.last_node_activity_at,
                snapshot.last_node_activity_at,
            ),
            DispatchTurnModel.node_activity_revision == snapshot.activity_revision,
            watchdog_context_is_current(snapshot),
            watchdog_replacement_count_matches(snapshot),
            dispatch_has_no_external_source(prompt.predecessor_dispatch_id),
            dispatch_has_no_successor(prompt.predecessor_dispatch_id),
        )
        .values(
            status="closed",
            closed_at=paused_at,
            closed_reason="control_failed",
            next_provider_start_at=None,
            provider_start_retry_kind=None,
        )
        .returning(DispatchTurnModel.dispatch_id)
    )
    if closed_dispatch_id is None:
        await session.rollback()
        return False
    return await _commit_watchdog_pause(
        session,
        task_id=prompt.task_id,
        flow_id=prompt.flow_id,
        flow_revision_id=prompt.flow_revision_id,
        dispatch_id=prompt.predecessor_dispatch_id,
        attempt_id=prompt.attempt_id,
        node_key=prompt.node_key,
        compiled_plan_id=dispatch.compiled_plan_id,
        control_revision=dispatch.flow_control_revision,
        paused_at=paused_at,
        pause_reason=pause_reason,
        failure_code=failure_code,
    )


async def _pause_failed_watchdog_signal(
    session: AsyncSession,
    *,
    signal: WatchdogDue,
    paused_at: datetime,
    inactivity_timeout_seconds: int,
    failure_code: str,
) -> bool:
    row = (
        await session.execute(
            select(DispatchTurnModel, FlowModel)
            .options(raiseload("*"))
            .join(FlowModel, FlowModel.flow_id == DispatchTurnModel.flow_id)
            .where(DispatchTurnModel.dispatch_id == signal.dispatch_id)
        )
    ).one_or_none()
    if row is None:
        await session.rollback()
        return False
    dispatch, flow = row
    if (
        dispatch.status != "open"
        or dispatch.adapter_started_at is None
        or dispatch.node_activity_revision != signal.activity_revision
        or flow.status != "running"
        or flow.current_dispatch_id != dispatch.dispatch_id
        or flow.waiting_cause != "none"
        or await dispatch_owns_external_source(session, dispatch_id=dispatch.dispatch_id)
    ):
        await session.rollback()
        return False
    due_at = calculate_watchdog_due_at(
        adapter_started_at=dispatch.adapter_started_at,
        last_node_activity_at=dispatch.last_node_activity_at,
        inactivity_timeout_seconds=inactivity_timeout_seconds,
    )
    if due_at != _as_utc(signal.due_at) or _as_utc(paused_at) < due_at:
        await session.rollback()
        return False
    dispatch_id = dispatch.dispatch_id
    task_id = dispatch.task_id
    flow_id = dispatch.flow_id
    assignment_id = dispatch.assignment_id
    attempt_id = dispatch.attempt_id
    node_key = dispatch.node_key
    adapter_started_at = dispatch.adapter_started_at
    last_node_activity_at = dispatch.last_node_activity_at
    compiled_plan_id = flow.compiled_plan_id
    flow_revision_id = flow.active_flow_revision_id
    control_revision = flow.control_revision
    assert flow_revision_id is not None
    await session.rollback()

    closed_dispatch_id = await session.scalar(
        update(DispatchTurnModel)
        .where(
            DispatchTurnModel.dispatch_id == dispatch_id,
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.flow_id == flow_id,
            DispatchTurnModel.assignment_id == assignment_id,
            DispatchTurnModel.attempt_id == attempt_id,
            DispatchTurnModel.status == "open",
            DispatchTurnModel.adapter_started_at == adapter_started_at,
            nullable_datetime_matches(
                DispatchTurnModel.last_node_activity_at,
                last_node_activity_at,
            ),
            DispatchTurnModel.node_activity_revision == signal.activity_revision,
            dispatch_has_no_external_source(dispatch_id),
            dispatch_has_no_successor(dispatch_id),
        )
        .values(
            status="closed",
            closed_at=paused_at,
            closed_reason="control_failed",
            next_provider_start_at=None,
            provider_start_retry_kind=None,
        )
        .returning(DispatchTurnModel.dispatch_id)
    )
    if closed_dispatch_id is None:
        await session.rollback()
        return False
    return await _commit_watchdog_pause(
        session,
        task_id=task_id,
        flow_id=flow_id,
        flow_revision_id=flow_revision_id,
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
        node_key=node_key,
        compiled_plan_id=compiled_plan_id,
        control_revision=control_revision,
        paused_at=paused_at,
        pause_reason="runtime_transition_failed",
        failure_code=failure_code,
    )


async def _commit_watchdog_pause(
    session: AsyncSession,
    *,
    task_id: str,
    flow_id: str,
    flow_revision_id: str,
    dispatch_id: str,
    attempt_id: str,
    node_key: str,
    compiled_plan_id: str,
    control_revision: int,
    paused_at: datetime,
    pause_reason: str,
    failure_code: str | None,
) -> bool:
    details: dict[str, object] = {
        "source": "watchdog",
        "source_dispatch_id": dispatch_id,
    }
    if failure_code is not None:
        details["failure_code"] = failure_code
    updated_flow_id = await session.scalar(
        update(FlowModel)
        .where(
            FlowModel.flow_id == flow_id,
            FlowModel.task_id == task_id,
            FlowModel.compiled_plan_id == compiled_plan_id,
            FlowModel.status == "running",
            FlowModel.active_flow_revision_id == flow_revision_id,
            FlowModel.current_dispatch_id == dispatch_id,
            FlowModel.waiting_cause == "none",
            FlowModel.control_revision == control_revision,
            dispatch_has_no_external_source(dispatch_id),
            dispatch_has_no_successor(dispatch_id),
        )
        .values(
            status="paused",
            current_dispatch_id=None,
            pause_reason=pause_reason,
            pause_details=details,
            paused_at=paused_at,
            paused_by_actor_ref="controller.runtime",
            control_revision=FlowModel.control_revision + 1,
            updated_at=paused_at,
        )
        .returning(FlowModel.flow_id)
    )
    if updated_flow_id is None:
        await session.rollback()
        return False
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.TASK_PAUSED,
        event_source=TaskEventSource.CONTROLLER,
        occurred_at=paused_at,
        flow_revision_id=flow_revision_id,
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
        node_key=node_key,
        actor_ref="controller.runtime",
        payload={"reason": pause_reason, **details},
    )
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return True


def _publish_dispatch_start(
    dependencies: DispatchOpeningDependencies,
    prepared: PreparedDispatchRequest,
) -> None:
    from autoclaw.runtime.dispatch.ordinary_continuation import publish_dispatch_start_due

    publish_dispatch_start_due(dependencies, prepared)


def _publish_cleanup(
    dependencies: DispatchOpeningDependencies,
    dispatch_id: str,
) -> None:
    try:
        dependencies.post_commit_publisher.publish(DispatchCleanupRequested(dispatch_id))
    except Exception:
        pass


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "WatchdogDueHandler",
    "WatchdogRecoveryResult",
    "create_watchdog_due_handler",
    "recover_stale_dispatch",
]
