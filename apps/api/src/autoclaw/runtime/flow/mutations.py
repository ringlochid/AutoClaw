from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    AttemptModel,
    CommandRunModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowWaitStateModel,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.command_runs import record_command_run_terminal_result
from autoclaw.runtime.contracts import (
    CommandRunState,
    CommandRunTerminalResultRead,
    FlowStatus,
    HumanRequestResolutionKind,
    HumanRequestResolutionSurface,
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    TaskEventSource,
    TaskEventType,
    WaitingCause,
)
from autoclaw.runtime.dispatch.control import (
    dispatch_deadline_expired,
    dispatch_inactivity_proven,
    dispatch_waiting_for_inactivity,
    fence_foreground_dispatch,
    fence_foreground_dispatch_after_timeout,
    mark_dispatch_abort_requested,
    open_dispatch_for_attempt,
    request_dispatch_abort_after_close_timeout,
    resolve_foreground_dispatch_gate,
    stage_previous_dispatch_outputs,
)
from autoclaw.runtime.errors import (
    illegal_state_error,
    missing_resource_error,
    stale_flow_revision_error,
)
from autoclaw.runtime.flow.queries import require_flow_for_task
from autoclaw.runtime.flow.reads import latest_fenced_dispatch, runtime_flow_read
from autoclaw.runtime.flow.resume import (
    ensure_flow_interruptible,
    ensure_flow_resumeable,
    resolve_flow_resume_target,
)
from autoclaw.runtime.human_request.records import record_human_request_terminal_result
from autoclaw.runtime.post_commit.cases import stage_operator_outputs
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from autoclaw.runtime.task_events import append_task_event
from autoclaw.runtime.workspace_leases import release_workspace_root_lease


async def continue_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    actor_ref: str | None = None,
) -> RuntimeFlowRead:
    flow = await require_flow_for_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise stale_flow_revision_error("stale active flow revision")
    if flow.status != FlowStatus.PAUSED.value:
        raise illegal_state_error(
            "continue is legal only for paused flows",
            suggested_next_step=(
                "Reread the current runtime status before retrying. Ordinary child handoff, "
                "parent wake, and retry progression now happen automatically once the prior "
                "dispatch is proven inactive; use continue only to resume a paused flow."
            ),
        )
    pause_wait_state = await _require_pause_resume_wait_state(session, flow=flow)
    resolved_previous_dispatch = await resolve_foreground_dispatch_gate(
        session,
        task_id=task_id,
        flow=flow,
    )
    if resolved_previous_dispatch is None:
        resolved_previous_dispatch = await latest_fenced_dispatch(
            session,
            task_id=task_id,
        )
    resume_target = await resolve_flow_resume_target(
        session,
        flow=flow,
        previous_dispatch=resolved_previous_dispatch,
    )
    await ensure_flow_resumeable(session, resume_target.attempt)
    dispatch_open_inputs = resume_target.dispatch_open_inputs()
    if flow.current_open_dispatch_id is None and dispatch_open_inputs is None:
        raise illegal_state_error(
            "current semantic target is incomplete",
            suggested_next_step=(
                "Inspect the current node assignment and attempt currentness, then repair "
                "the incomplete semantic target before continuing this task."
            ),
        )
    if pause_wait_state is not None:
        await session.delete(pause_wait_state)
    flow.status = FlowStatus.RUNNING.value
    flow.updated_at = utc_now()
    assert resume_target.attempt is not None
    assert resume_target.node is not None
    await _append_task_control_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.TASK_RESUMED,
        flow=flow,
        attempt_id=resume_target.attempt.attempt_id,
        node_key=resume_target.node.node_key,
        actor_ref=actor_ref,
    )
    await session.flush()
    await _open_resumed_dispatch_if_needed(
        session,
        task_id=task_id,
        flow=flow,
        dispatch_open_inputs=dispatch_open_inputs,
    )
    await session.flush()
    return await runtime_flow_read(session, task_id)


async def pause_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    actor_ref: str | None = None,
) -> RuntimeFlowPauseResponse:
    flow = await require_flow_for_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise stale_flow_revision_error("stale active flow revision")
    if flow.status in {
        FlowStatus.SUCCEEDED.value,
        FlowStatus.BLOCKED.value,
        FlowStatus.CANCELLED.value,
    }:
        raise illegal_state_error("terminal flow cannot be paused")
    state = await current_runtime_state(session, task_id)
    await ensure_flow_interruptible(session, state.current_attempt, action="pause")
    paused_dispatch_id = flow.current_open_dispatch_id
    if paused_dispatch_id is not None:
        await _pause_active_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            paused_dispatch_id=paused_dispatch_id,
        )
    flow.status = FlowStatus.PAUSED.value
    flow.updated_at = utc_now()
    await _record_pause_wait_state(
        session,
        task_id=task_id,
        flow=flow,
        paused_dispatch_id=paused_dispatch_id,
    )
    await _append_task_control_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.TASK_PAUSED,
        flow=flow,
        attempt_id=state.current_attempt.attempt_id,
        node_key=state.current_node.node_key,
        dispatch_id=paused_dispatch_id,
        actor_ref=actor_ref,
    )
    await session.flush()
    if paused_dispatch_id is not None:
        stage_operator_outputs(session, task_id=task_id, dispatch_id=paused_dispatch_id)
    return RuntimeFlowPauseResponse(flow=await runtime_flow_read(session, task_id))


async def cancel_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    actor_ref: str | None = None,
) -> RuntimeFlowRead:
    flow = await require_flow_for_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise stale_flow_revision_error("stale active flow revision")
    state = await current_runtime_state(session, task_id)
    await ensure_flow_interruptible(session, state.current_attempt, action="cancel")
    cancelled_dispatch_id = flow.current_open_dispatch_id
    if cancelled_dispatch_id is not None:
        dispatch = await session.get(DispatchTurnModel, cancelled_dispatch_id)
        if dispatch is None:
            raise missing_resource_error(f"missing dispatch '{cancelled_dispatch_id}'")
        if dispatch.control_state == "abort_requested":
            if dispatch_inactivity_proven(dispatch):
                await fence_foreground_dispatch(
                    session,
                    task_id=task_id,
                    flow=flow,
                    dispatch=dispatch,
                )
                return await _finish_cancelled_flow(
                    session,
                    task_id,
                    flow,
                    cancelled_dispatch_id,
                    actor_ref=actor_ref,
                )
            if dispatch_deadline_expired(dispatch):
                await fence_foreground_dispatch_after_timeout(
                    session,
                    task_id=task_id,
                    flow=flow,
                    dispatch=dispatch,
                )
                stage_operator_outputs(session, task_id=task_id, dispatch_id=cancelled_dispatch_id)
                await session.flush()
                return await runtime_flow_read(session, task_id)
            return await _finish_cancelled_flow(
                session,
                task_id,
                flow,
                cancelled_dispatch_id,
                actor_ref=actor_ref,
            )
        if dispatch.control_state == "ambiguous":
            await fence_foreground_dispatch(
                session,
                task_id=task_id,
                flow=flow,
                dispatch=dispatch,
                reason=dispatch.control_state_reason or "cancel_requested:cleanup",
                delivery_status=dispatch.delivery_status,
            )
        elif dispatch.control_state == "fenced":
            flow.current_open_dispatch_id = None
        else:
            await _mark_dispatch_cancel_requested(session, dispatch)
    await _cancel_active_external_wait(
        session,
        task_id=task_id,
        flow=flow,
        actor_ref=actor_ref,
    )
    return await _finish_cancelled_flow(
        session,
        task_id,
        flow,
        cancelled_dispatch_id,
        actor_ref=actor_ref,
    )


async def _pause_active_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: Any,
    paused_dispatch_id: str,
) -> None:
    dispatch = await session.get(DispatchTurnModel, paused_dispatch_id)
    if dispatch is None:
        raise missing_resource_error(f"missing dispatch '{paused_dispatch_id}'")
    paused_at = utc_now()
    delivery_state = await session.get(DispatchDeliveryStateModel, paused_dispatch_id)
    if dispatch_inactivity_proven(dispatch) and (
        dispatch_waiting_for_inactivity(dispatch) or dispatch.control_state == "abort_requested"
    ):
        await fence_foreground_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
        )
        return
    if dispatch_deadline_expired(dispatch):
        if dispatch.control_state == "live":
            await request_dispatch_abort_after_close_timeout(
                session,
                task_id=task_id,
                dispatch=dispatch,
            )
            return
        await fence_foreground_dispatch_after_timeout(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
        )
        return
    if dispatch.control_state == "ambiguous":
        await fence_foreground_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
            reason=dispatch.control_state_reason or "pause_requested:cleanup",
            delivery_status=dispatch.delivery_status,
        )
        return
    if dispatch.control_state == "fenced":
        flow.current_open_dispatch_id = None
        return
    dispatch.closed_at = dispatch.closed_at or paused_at
    if dispatch.accepted_boundary is None:
        await mark_dispatch_abort_requested(
            session,
            dispatch=dispatch,
            reason="pause_requested",
            requested_at=paused_at,
        )
    if delivery_state is not None:
        delivery_state.updated_at = paused_at


async def _mark_dispatch_cancel_requested(
    session: AsyncSession,
    dispatch: DispatchTurnModel,
) -> None:
    closed_at = utc_now()
    await mark_dispatch_abort_requested(
        session,
        dispatch=dispatch,
        reason="cancel_requested",
        requested_at=closed_at,
    )
    if dispatch.attempt_id is not None:
        attempt = await session.get(AttemptModel, dispatch.attempt_id)
        if attempt is not None and attempt.closed_at is None:
            attempt.closed_at = closed_at
            attempt.status = "cancelled"


async def _finish_cancelled_flow(
    session: AsyncSession,
    task_id: str,
    flow: Any,
    cancelled_dispatch_id: str | None,
    *,
    actor_ref: str | None,
) -> RuntimeFlowRead:
    flow.status = FlowStatus.CANCELLED.value
    flow.updated_at = utc_now()
    await _append_task_control_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.TASK_CANCELLED,
        flow=flow,
        attempt_id=None,
        node_key=flow.current_node_key,
        dispatch_id=cancelled_dispatch_id,
        actor_ref=actor_ref,
    )
    if flow.current_open_dispatch_id is None:
        await release_workspace_root_lease(session, task_id=task_id)
    await session.flush()
    if cancelled_dispatch_id is not None:
        stage_operator_outputs(session, task_id=task_id, dispatch_id=cancelled_dispatch_id)
    return await runtime_flow_read(session, task_id)


async def _open_resumed_dispatch_if_needed(
    session: AsyncSession,
    *,
    task_id: str,
    flow: Any,
    dispatch_open_inputs: Any,
) -> None:
    if flow.current_open_dispatch_id is not None or dispatch_open_inputs is None:
        return
    node, assignment, attempt, previous_dispatch_id, staged_child_assignment_id = (
        dispatch_open_inputs
    )
    await open_dispatch_for_attempt(
        session,
        task_id=task_id,
        node=node,
        assignment=assignment,
        attempt=attempt,
        previous_dispatch_id=previous_dispatch_id,
        staged_child_assignment_id=staged_child_assignment_id,
    )
    stage_previous_dispatch_outputs(
        session,
        task_id=task_id,
        previous_dispatch_id=previous_dispatch_id,
    )


async def _cancel_active_external_wait(
    session: AsyncSession,
    *,
    task_id: str,
    flow: Any,
    actor_ref: str | None,
) -> None:
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    if wait_state is None:
        return

    cancelled_at = utc_now()
    if (
        wait_state.waiting_cause == WaitingCause.WAITING_FOR_HUMAN_REQUEST.value
        and wait_state.pending_human_request_id is not None
    ):
        await record_human_request_terminal_result(
            session,
            task_id=task_id,
            request_id=wait_state.pending_human_request_id,
            resolution_kind=HumanRequestResolutionKind.CANCELLED,
            event_source=TaskEventSource.CONTROL_API,
            actor_ref=actor_ref,
            resolved_by_actor_ref=actor_ref,
            resolved_by_surface=HumanRequestResolutionSurface.CONTROL_API,
            policy_basis="task_cancelled",
            note="human request cancelled because the task was cancelled",
            resolved_at=cancelled_at,
        )
        return

    if (
        wait_state.waiting_cause == WaitingCause.WAITING_FOR_COMMAND_RUN.value
        and wait_state.command_run_id is not None
    ):
        command_run = await session.get(CommandRunModel, wait_state.command_run_id)
        if command_run is None:
            return
        await record_command_run_terminal_result(
            session,
            task_id=task_id,
            result=CommandRunTerminalResultRead(
                run_id=command_run.run_id,
                state=CommandRunState.CANCELLED,
                summary="command run cancelled because the task was cancelled",
                exit_code=None,
                signal=None,
                log_ref=command_run.latest_log_ref,
                ended_at=cancelled_at,
            ),
            event_source=TaskEventSource.CONTROL_API,
            actor_ref=actor_ref,
        )
        return
    await session.delete(wait_state)


async def _append_task_control_event(
    session: AsyncSession,
    *,
    task_id: str,
    event_type: TaskEventType,
    flow: Any,
    attempt_id: str | None,
    node_key: str | None,
    dispatch_id: str | None = None,
    actor_ref: str | None = None,
) -> None:
    await append_task_event(
        session,
        task_id=task_id,
        event_type=event_type,
        event_source=TaskEventSource.CONTROL_API,
        occurred_at=flow.updated_at,
        flow_revision_id=flow.active_flow_revision_id,
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
        node_key=node_key,
        actor_ref=actor_ref,
        payload={"status": flow.status},
    )


async def _record_pause_wait_state(
    session: AsyncSession,
    *,
    task_id: str,
    flow: Any,
    paused_dispatch_id: str | None,
) -> None:
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    if wait_state is None:
        session.add(
            FlowWaitStateModel(
                flow_id=flow.flow_id,
                task_id=task_id,
                waiting_cause=WaitingCause.PAUSED_BY_OPERATOR.value,
                created_by_dispatch_id=paused_dispatch_id,
                created_at=flow.updated_at,
                updated_at=flow.updated_at,
            )
        )
        return
    if wait_state.waiting_cause != WaitingCause.PAUSED_BY_OPERATOR.value:
        return
    wait_state.created_by_dispatch_id = wait_state.created_by_dispatch_id or paused_dispatch_id
    wait_state.updated_at = flow.updated_at


async def _require_pause_resume_wait_state(
    session: AsyncSession,
    *,
    flow: Any,
) -> FlowWaitStateModel | None:
    wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
    if wait_state is None:
        return None
    if wait_state.waiting_cause == WaitingCause.PAUSED_BY_OPERATOR.value:
        return wait_state
    if wait_state.waiting_cause == WaitingCause.WAITING_FOR_HUMAN_REQUEST.value:
        raise illegal_state_error(
            "continue is illegal while a human request wait is still active",
            suggested_next_step=(
                "Resolve or cancel the active human request through its dedicated control "
                "surface before using continue."
            ),
        )
    if wait_state.waiting_cause == WaitingCause.WAITING_FOR_COMMAND_RUN.value:
        raise illegal_state_error(
            "continue is illegal while a command run wait is still active",
            suggested_next_step=(
                "Wait for the active command run to finish or cancel it through the "
                "dedicated control surface before using continue."
            ),
        )
    raise illegal_state_error(
        f"continue is illegal while the task is waiting for {wait_state.waiting_cause}",
        suggested_next_step="Wait for the current controller-owned wait to clear first.",
    )


__all__ = [
    "cancel_runtime_flow",
    "continue_runtime_flow",
    "pause_runtime_flow",
]
