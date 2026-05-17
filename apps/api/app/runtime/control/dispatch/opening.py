from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssignmentModel,
    AttemptModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
    FlowNodeModel,
)
from app.runtime.contracts import (
    DispatchDeliveryStatus,
    EgressBoundary,
    FlowStatus,
    NodeKind,
    PromptFamily,
    PromptSendMode,
)
from app.runtime.control.clock import utc_now
from app.runtime.control.dispatch.gateway import (
    OPENCLAW_GATEWAY_TRANSPORT_FAMILY,
    GatewayDispatchLaunchError,
    perform_gateway_dispatch_launch,
)
from app.runtime.control.dispatch.gateway_launch_state import (
    GatewayDispatchContext,
    record_gateway_dispatch_acceptance,
    record_gateway_dispatch_launch_failure,
    record_gateway_dispatch_post_acceptance_failure,
    record_gateway_dispatch_post_send_failure,
)
from app.runtime.control.flow.queries import next_node_sequence_number
from app.runtime.ids import dispatch_id_for_task
from app.runtime.openclaw import OpenClawLaunchResult

LOGGER = logging.getLogger(__name__)


async def prepare_dispatch_turn(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    send_mode: PromptSendMode,
    previous_dispatch: DispatchTurnModel | None,
    staged_child_assignment_id: str | None,
) -> DispatchTurnModel:
    dispatch = await _build_dispatch_turn(
        session,
        task_id=task_id,
        flow=flow,
        node=node,
        assignment=assignment,
        attempt=attempt,
        send_mode=send_mode,
        previous_dispatch=previous_dispatch,
        staged_child_assignment_id=staged_child_assignment_id,
    )
    session.add(dispatch)
    flow.current_open_dispatch_id = dispatch.dispatch_id
    flow.current_node_key = node.node_key
    flow.status = FlowStatus.RUNNING.value
    flow.updated_at = utc_now()
    attempt.status = "running"
    await session.flush()
    _add_dispatch_state_rows(
        session,
        task_id=task_id,
        dispatch=dispatch,
        node=node,
        assignment=assignment,
        attempt=attempt,
        send_mode=send_mode,
    )
    await session.flush()
    await link_previous_dispatch_opening(
        session,
        previous_dispatch_id=dispatch.previous_dispatch_id,
        dispatch_id=dispatch.dispatch_id,
    )
    return dispatch


async def activate_dispatch_turn(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    stage_launch_projection_outputs: bool,
) -> DispatchTurnModel:
    await _commit_dispatch_outputs(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
        attempt_id=attempt.attempt_id if stage_launch_projection_outputs else None,
    )
    context = GatewayDispatchContext(task_id, flow, dispatch, assignment, attempt)
    try:
        launch_result, prompt_path, content_hash = await perform_gateway_dispatch_launch(
            session,
            dispatch=dispatch,
            assignment_key=assignment.assignment_key,
            attempt_id=attempt.attempt_id,
        )
    except GatewayDispatchLaunchError as exc:
        await _record_gateway_launch_failure_and_commit(
            session,
            context=context,
            error=exc.error,
            session_key=exc.session_key if exc.request_sent else None,
        )
        raise exc.error from exc
    except Exception as exc:
        await _record_gateway_launch_failure_and_commit(
            session,
            context=context,
            error=exc,
            session_key=None,
        )
        raise
    await _persist_dispatch_acceptance(
        session,
        context=context,
        launch_result=launch_result,
        prompt_path=prompt_path,
        content_hash=content_hash,
    )
    return dispatch


async def link_previous_dispatch_opening(
    session: AsyncSession,
    *,
    previous_dispatch_id: str | None,
    dispatch_id: str,
) -> None:
    if previous_dispatch_id is None:
        return
    previous_dispatch = await session.get(DispatchTurnModel, previous_dispatch_id)
    if previous_dispatch is not None:
        previous_dispatch.superseded_by_dispatch_id = dispatch_id
    previous_delivery_state = await session.get(
        DispatchDeliveryStateModel,
        previous_dispatch_id,
    )
    if previous_delivery_state is not None:
        previous_delivery_state.superseded_by_dispatch_id = dispatch_id
    previous_watchdog_state = await session.get(
        DispatchWatchdogStateModel,
        previous_dispatch_id,
    )
    if previous_watchdog_state is not None:
        previous_watchdog_state.superseded_by_dispatch_id = dispatch_id


async def _build_dispatch_turn(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    send_mode: PromptSendMode,
    previous_dispatch: DispatchTurnModel | None,
    staged_child_assignment_id: str | None,
) -> DispatchTurnModel:
    dispatch_id = dispatch_id_for_task(
        task_id,
        node.node_key,
        await next_node_sequence_number(session, DispatchTurnModel, task_id, node.node_key),
    )
    prompt_name = (
        PromptFamily.WORKER_DISPATCH.value
        if node.structural_kind == NodeKind.WORKER.value
        else PromptFamily.PARENT_ROOT_DISPATCH.value
    )
    rendered_at = utc_now()
    return DispatchTurnModel(
        dispatch_id=dispatch_id,
        flow_id=flow.flow_id,
        flow_revision_id=flow.active_flow_revision_id,
        flow_node_id=node.flow_node_id,
        task_id=task_id,
        node_key=node.node_key,
        assignment_id=assignment.assignment_id,
        assignment_key=assignment.assignment_key,
        attempt_id=attempt.attempt_id,
        prompt_name=prompt_name,
        delivery_status=DispatchDeliveryStatus.PREPARED.value,
        control_state="launching",
        control_state_reason="launch_requested",
        prompt_path="",
        content_hash="",
        previous_dispatch_id=None if previous_dispatch is None else previous_dispatch.dispatch_id,
        relevant_checkpoint_attempt_id=_relevant_checkpoint_attempt_id(
            previous_dispatch,
            node_key=node.node_key,
            attempt=attempt,
        ),
        staged_child_assignment_id=staged_child_assignment_id,
        rendered_at=rendered_at,
        opened_at=rendered_at,
    )


def _add_dispatch_state_rows(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    send_mode: PromptSendMode,
) -> None:
    session.add_all(
        [
            DispatchDeliveryStateModel(
                dispatch_id=dispatch.dispatch_id,
                task_id=task_id,
                attempt_id=attempt.attempt_id,
                assignment_key=assignment.assignment_key,
                node_key=node.node_key,
                transport_family=OPENCLAW_GATEWAY_TRANSPORT_FAMILY,
                transport_state=DispatchDeliveryStatus.PREPARED.value,
                previous_dispatch_id=dispatch.previous_dispatch_id,
            ),
            DispatchContinuityStateModel(
                dispatch_id=dispatch.dispatch_id,
                task_id=task_id,
                attempt_id=attempt.attempt_id,
                assignment_key=assignment.assignment_key,
                node_key=node.node_key,
                session_key_present=False,
            ),
            DispatchWatchdogStateModel(
                dispatch_id=dispatch.dispatch_id,
                task_id=task_id,
                attempt_id=attempt.attempt_id,
                assignment_key=assignment.assignment_key,
                node_key=node.node_key,
                watchdog_state="clear",
                previous_dispatch_id=dispatch.previous_dispatch_id,
            ),
        ]
    )


async def _persist_dispatch_acceptance(
    session: AsyncSession,
    *,
    context: GatewayDispatchContext,
    launch_result: OpenClawLaunchResult,
    prompt_path: str,
    content_hash: str,
) -> None:
    try:
        await record_gateway_dispatch_acceptance(
            session,
            context=context,
            launch_result=launch_result,
            prompt_path=prompt_path,
            content_hash=content_hash,
        )
        await _commit_dispatch_outputs(
            session,
            task_id=context.task_id,
            dispatch_id=context.dispatch.dispatch_id,
        )
    except Exception as exc:
        try:
            await record_gateway_dispatch_post_acceptance_failure(
                session,
                flow_id=context.flow.flow_id,
                dispatch_id=context.dispatch.dispatch_id,
                attempt_id=context.attempt.attempt_id,
                launch_result=launch_result,
                prompt_path=prompt_path,
                content_hash=content_hash,
                error=exc,
            )
            await _commit_dispatch_outputs(
                session,
                task_id=context.task_id,
                dispatch_id=context.dispatch.dispatch_id,
            )
        except Exception:  # pragma: no cover - cleanup escalation
            LOGGER.exception(
                "failed to clean up accepted OpenClaw run after local "
                "post-launch persistence failure"
            )
        raise


async def _record_gateway_launch_failure_and_commit(
    session: AsyncSession,
    *,
    context: GatewayDispatchContext,
    error: Exception,
    session_key: str | None,
) -> None:
    if session_key is None:
        await record_gateway_dispatch_launch_failure(session, context=context, error=error)
    else:
        await record_gateway_dispatch_post_send_failure(
            session,
            context=context,
            session_key=session_key,
            error=error,
        )
    await _commit_dispatch_outputs(
        session,
        task_id=context.task_id,
        dispatch_id=context.dispatch.dispatch_id,
    )


def _relevant_checkpoint_attempt_id(
    previous_dispatch: DispatchTurnModel | None,
    *,
    node_key: str,
    attempt: AttemptModel,
) -> str | None:
    if previous_dispatch is None:
        return None
    if (
        previous_dispatch.attempt_id == attempt.attempt_id
        and previous_dispatch.node_key == node_key
    ):
        return previous_dispatch.relevant_checkpoint_attempt_id
    if (
        previous_dispatch.attempt_id is None
        or previous_dispatch.attempt_id == attempt.attempt_id
        or previous_dispatch.accepted_boundary is None
        or previous_dispatch.accepted_boundary == EgressBoundary.YIELD.value
    ):
        return None
    return previous_dispatch.attempt_id


async def _commit_dispatch_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    attempt_id: str | None = None,
) -> None:
    from app.runtime.effects import (
        commit_runtime_session,
        stage_dispatch_open_outputs,
        stage_launch_outputs,
    )

    if attempt_id is None:
        stage_dispatch_open_outputs(session, task_id=task_id, dispatch_id=dispatch_id)
    else:
        stage_launch_outputs(
            session,
            task_id=task_id,
            attempt_id=attempt_id,
            dispatch_id=dispatch_id,
        )
    await commit_runtime_session(session)
