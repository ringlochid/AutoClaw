from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import AttemptModel, DispatchDeliveryStateModel, DispatchTurnModel
from autoclaw.runtime.clock import dispatch_control_deadline, utc_now
from autoclaw.runtime.contracts import (
    DispatchDeliveryStatus,
    FlowStatus,
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
)
from autoclaw.runtime.dispatch.control import (
    dispatch_deadline_expired,
    dispatch_inactivity_proven,
    dispatch_waiting_for_inactivity,
    fence_foreground_dispatch,
    open_dispatch_for_attempt,
    resolve_foreground_dispatch_gate,
    stage_previous_dispatch_outputs,
)
from autoclaw.runtime.dispatch.gateway import record_gateway_wait_timeout
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
from autoclaw.runtime.post_commit.cases import stage_operator_outputs
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from autoclaw.runtime.workspace_leases import release_workspace_root_lease


async def continue_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
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
    flow.status = FlowStatus.RUNNING.value
    flow.updated_at = utc_now()
    await session.flush()
    if flow.current_open_dispatch_id is None and dispatch_open_inputs is not None:
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
    await session.flush()
    return await runtime_flow_read(session, task_id)


async def pause_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
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
        elif dispatch_deadline_expired(dispatch):
            reason = dispatch.control_state_reason or "pause_requested"
            await record_gateway_wait_timeout(
                session,
                dispatch=dispatch,
                detail=f"{reason}:timed_out",
            )
            await fence_foreground_dispatch(
                session,
                task_id=task_id,
                flow=flow,
                dispatch=dispatch,
                reason=f"{reason}:timed_out",
                delivery_status=DispatchDeliveryStatus.TRANSPORT_AMBIGUOUS.value,
            )
        elif dispatch.control_state == "ambiguous":
            await fence_foreground_dispatch(
                session,
                task_id=task_id,
                flow=flow,
                dispatch=dispatch,
                reason=dispatch.control_state_reason or "pause_requested:cleanup",
                delivery_status=dispatch.delivery_status,
            )
        elif dispatch.control_state == "fenced":
            flow.current_open_dispatch_id = None
        else:
            dispatch.closed_at = dispatch.closed_at or paused_at
            if dispatch.accepted_boundary is None:
                dispatch.abort_requested_at = dispatch.abort_requested_at or paused_at
                dispatch.control_state = "abort_requested"
                dispatch.control_state_reason = "pause_requested"
                dispatch.control_deadline_at = (
                    dispatch.control_deadline_at or dispatch_control_deadline(base=paused_at)
                )
            if delivery_state is not None:
                delivery_state.updated_at = paused_at
    flow.status = FlowStatus.PAUSED.value
    flow.updated_at = utc_now()
    await session.flush()
    if paused_dispatch_id is not None:
        stage_operator_outputs(session, task_id=task_id, dispatch_id=paused_dispatch_id)
    return RuntimeFlowPauseResponse(flow=await runtime_flow_read(session, task_id))


async def cancel_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
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
                return await _finish_cancelled_flow(session, task_id, flow, cancelled_dispatch_id)
            if dispatch_deadline_expired(dispatch):
                await record_gateway_wait_timeout(
                    session,
                    dispatch=dispatch,
                    detail="cancel_requested:timed_out",
                )
                await fence_foreground_dispatch(
                    session,
                    task_id=task_id,
                    flow=flow,
                    dispatch=dispatch,
                    reason="cancel_requested:timed_out",
                    delivery_status=DispatchDeliveryStatus.TRANSPORT_AMBIGUOUS.value,
                )
                stage_operator_outputs(session, task_id=task_id, dispatch_id=cancelled_dispatch_id)
                await session.flush()
                return await runtime_flow_read(session, task_id)
            return await _finish_cancelled_flow(session, task_id, flow, cancelled_dispatch_id)
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
            await _mark_dispatch_cancel_requested(session, cancelled_dispatch_id, dispatch)
    return await _finish_cancelled_flow(session, task_id, flow, cancelled_dispatch_id)


async def _mark_dispatch_cancel_requested(
    session: AsyncSession,
    cancelled_dispatch_id: str,
    dispatch: DispatchTurnModel,
) -> None:
    closed_at = utc_now()
    dispatch.abort_requested_at = dispatch.abort_requested_at or closed_at
    dispatch.control_state = "abort_requested"
    dispatch.control_state_reason = "cancel_requested"
    dispatch.control_deadline_at = dispatch_control_deadline(base=closed_at)
    dispatch.closed_at = dispatch.closed_at or closed_at
    if dispatch.attempt_id is not None:
        attempt = await session.get(AttemptModel, dispatch.attempt_id)
        if attempt is not None and attempt.closed_at is None:
            attempt.closed_at = closed_at
            attempt.status = "cancelled"
    delivery_state = await session.get(DispatchDeliveryStateModel, cancelled_dispatch_id)
    if delivery_state is not None:
        delivery_state.updated_at = closed_at


async def _finish_cancelled_flow(
    session: AsyncSession,
    task_id: str,
    flow: Any,
    cancelled_dispatch_id: str | None,
) -> RuntimeFlowRead:
    flow.status = FlowStatus.CANCELLED.value
    flow.updated_at = utc_now()
    if flow.current_open_dispatch_id is None:
        await release_workspace_root_lease(session, task_id=task_id)
    await session.flush()
    if cancelled_dispatch_id is not None:
        stage_operator_outputs(session, task_id=task_id, dispatch_id=cancelled_dispatch_id)
    return await runtime_flow_read(session, task_id)


__all__ = [
    "cancel_runtime_flow",
    "continue_runtime_flow",
    "pause_runtime_flow",
]
