from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.db.models import (
    AssignmentModel,
    AttemptModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    NodeSessionModel,
)
from autoclaw.runtime.control.clock import utc_now
from autoclaw.runtime.control.dispatch.gateway import record_gateway_wait_timeout
from autoclaw.runtime.control.dispatch.opening import (
    activate_dispatch_turn,
    prepare_dispatch_turn,
)
from autoclaw.runtime.control.failures import (
    illegal_state_error,
    missing_resource_error,
)
from autoclaw.runtime.control.flow.queries import require_flow_for_task
from autoclaw.runtime.control.workspace_leases import release_workspace_root_lease
from autoclaw.schemas.runtime.contracts import (
    DispatchDeliveryStatus,
    FlowStatus,
)

REPLACEMENT_BLOCKING_CONTROL_STATES = {
    "launching",
    "live",
    "abort_requested",
    "ambiguous",
}
WAITING_INACTIVITY_CONTROL_STATES = {"launching", "live"}
INACTIVITY_PROVEN_DELIVERY_STATUSES = {
    DispatchDeliveryStatus.PROVIDER_COMPLETED.value,
    DispatchDeliveryStatus.PROVIDER_FAILED.value,
}


async def resolve_foreground_dispatch_gate(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
) -> DispatchTurnModel | None:
    if flow.current_open_dispatch_id is None:
        return None
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
    if dispatch is None:
        raise missing_resource_error(f"missing dispatch '{flow.current_open_dispatch_id}'")
    if dispatch_inactivity_proven(dispatch) and (
        dispatch_waiting_for_inactivity(dispatch) or dispatch.control_state == "abort_requested"
    ):
        return await fence_foreground_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
        )
    if dispatch_deadline_expired(dispatch):
        reason = dispatch.control_state_reason or "foreground_dispatch"
        await record_gateway_wait_timeout(
            session,
            dispatch=dispatch,
            detail=f"{reason}:timed_out",
        )
        if flow.status in {FlowStatus.PAUSED.value, FlowStatus.CANCELLED.value}:
            return await fence_foreground_dispatch(
                session,
                task_id=task_id,
                flow=flow,
                dispatch=dispatch,
                reason=f"{reason}:timed_out",
                delivery_status=DispatchDeliveryStatus.TRANSPORT_AMBIGUOUS.value,
            )
        await mark_dispatch_ambiguous(
            session,
            dispatch=dispatch,
            reason=f"{reason}:timed_out",
        )
        _stage_dispatch_outputs(session, task_id=task_id, dispatch_id=dispatch.dispatch_id)
        raise illegal_state_error("foreground dispatch timed out before inactivity was proven")
    if dispatch.control_state == "abort_requested":
        raise illegal_state_error("current dispatch is still awaiting inactivity proof after abort")
    if dispatch.control_state == "ambiguous":
        if flow.status in {FlowStatus.PAUSED.value, FlowStatus.CANCELLED.value}:
            return await fence_foreground_dispatch(
                session,
                task_id=task_id,
                flow=flow,
                dispatch=dispatch,
                reason=dispatch.control_state_reason or "foreground_dispatch:cleanup",
                delivery_status=dispatch.delivery_status,
            )
        raise illegal_state_error("foreground dispatch timed out before inactivity was proven")
    if dispatch.control_state == "fenced":
        await session.refresh(flow, attribute_names=["current_open_dispatch_id"])
        if flow.current_open_dispatch_id == dispatch.dispatch_id:
            flow.current_open_dispatch_id = None
        await session.flush()
        return dispatch
    raise illegal_state_error("current dispatch is still awaiting inactivity proof")


async def open_dispatch_for_attempt(
    session: AsyncSession,
    *,
    task_id: str,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    previous_dispatch_id: str | None,
    staged_child_assignment_id: str | None = None,
    stage_launch_projection_outputs: bool = False,
) -> DispatchTurnModel:
    flow = await require_flow_for_task(session, task_id)
    if flow.current_open_dispatch_id is not None:
        raise illegal_state_error(
            "cannot open a replacement dispatch while another dispatch is current"
        )
    await _ensure_previous_dispatch_replaced_legally(
        session,
        task_id=task_id,
        previous_dispatch_id=previous_dispatch_id,
    )
    previous_dispatch = (
        None
        if previous_dispatch_id is None
        else await session.get(DispatchTurnModel, previous_dispatch_id)
    )
    dispatch = await prepare_dispatch_turn(
        session,
        task_id=task_id,
        flow=flow,
        node=node,
        assignment=assignment,
        attempt=attempt,
        previous_dispatch=previous_dispatch,
        staged_child_assignment_id=staged_child_assignment_id,
    )
    return await activate_dispatch_turn(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
        assignment=assignment,
        attempt=attempt,
        stage_launch_projection_outputs=stage_launch_projection_outputs,
    )


async def fence_foreground_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    reason: str | None = None,
    delivery_status: str | None = None,
) -> DispatchTurnModel:
    await mark_dispatch_fenced(
        session,
        dispatch=dispatch,
        reason=reason or _foreground_inactivity_reason(dispatch),
        delivery_status=delivery_status,
    )
    await session.refresh(flow, attribute_names=["current_open_dispatch_id", "status"])
    if flow.current_open_dispatch_id == dispatch.dispatch_id:
        flow.current_open_dispatch_id = None
    if flow.status in {
        FlowStatus.SUCCEEDED.value,
        FlowStatus.BLOCKED.value,
        FlowStatus.CANCELLED.value,
    }:
        await release_workspace_root_lease(session, task_id=task_id)
    _stage_dispatch_outputs(session, task_id=task_id, dispatch_id=dispatch.dispatch_id)
    await session.flush()
    return dispatch


def stage_previous_dispatch_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    previous_dispatch_id: str | None,
) -> None:
    if previous_dispatch_id is None:
        return
    _stage_dispatch_outputs(
        session,
        task_id=task_id,
        dispatch_id=previous_dispatch_id,
    )


def dispatch_deadline_expired(dispatch: DispatchTurnModel) -> bool:
    deadline = dispatch.control_deadline_at
    if deadline is not None and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return (
        dispatch.control_state in REPLACEMENT_BLOCKING_CONTROL_STATES
        and deadline is not None
        and deadline <= utc_now()
    )


def dispatch_waiting_for_inactivity(dispatch: DispatchTurnModel) -> bool:
    return (
        dispatch.accepted_boundary is not None
        and dispatch.control_state in WAITING_INACTIVITY_CONTROL_STATES
        and dispatch.fenced_at is None
    )


def dispatch_inactivity_proven(dispatch: DispatchTurnModel) -> bool:
    return dispatch.delivery_status in INACTIVITY_PROVEN_DELIVERY_STATUSES


async def mark_dispatch_fenced(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    reason: str,
    delivery_status: str | None = None,
) -> None:
    fenced_at = utc_now()
    resolved_delivery_status = (
        delivery_status
        if delivery_status is not None
        else (
            dispatch.delivery_status
            if dispatch.delivery_status in INACTIVITY_PROVEN_DELIVERY_STATUSES
            else DispatchDeliveryStatus.PROVIDER_COMPLETED.value
        )
    )
    dispatch.control_state = "fenced"
    dispatch.control_state_reason = reason
    dispatch.control_deadline_at = None
    dispatch.fenced_at = dispatch.fenced_at or fenced_at
    dispatch.delivery_status = resolved_delivery_status
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_state = resolved_delivery_status
        delivery_state.last_controller_terminal_at = fenced_at
        delivery_state.updated_at = fenced_at
    await _close_node_sessions_for_dispatch(
        session,
        dispatch_id=dispatch.dispatch_id,
        status="fenced",
        closed_at=fenced_at,
    )
    await session.flush()


async def mark_dispatch_ambiguous(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    reason: str,
) -> None:
    ambiguous_at = utc_now()
    dispatch.control_state = "ambiguous"
    dispatch.control_state_reason = reason
    dispatch.control_deadline_at = None
    dispatch.delivery_status = DispatchDeliveryStatus.TRANSPORT_AMBIGUOUS.value
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_state = DispatchDeliveryStatus.TRANSPORT_AMBIGUOUS.value
        delivery_state.last_controller_terminal_at = ambiguous_at
        delivery_state.updated_at = ambiguous_at
    await session.flush()


def _foreground_inactivity_reason(dispatch: DispatchTurnModel) -> str:
    if dispatch.control_state == "abort_requested":
        reason = dispatch.control_state_reason or "abort_requested"
        return f"{reason}:inactive_proven"
    if dispatch.accepted_boundary is not None:
        return f"boundary:{dispatch.accepted_boundary}:inactive_proven"
    reason = dispatch.control_state_reason or "foreground_dispatch"
    return f"{reason}:inactive_proven"


async def _ensure_previous_dispatch_replaced_legally(
    session: AsyncSession,
    *,
    task_id: str,
    previous_dispatch_id: str | None,
) -> None:
    if previous_dispatch_id is None:
        return
    previous_dispatch = await session.get(DispatchTurnModel, previous_dispatch_id)
    if previous_dispatch is None or previous_dispatch.task_id != task_id:
        raise missing_resource_error(f"missing previous dispatch '{previous_dispatch_id}'")
    if previous_dispatch.control_state in REPLACEMENT_BLOCKING_CONTROL_STATES:
        raise illegal_state_error(
            "replacement dispatch is illegal until the previous dispatch is proven inactive"
        )
    if previous_dispatch.control_state != "fenced":
        raise illegal_state_error("replacement dispatch requires a fenced previous dispatch")


def _stage_dispatch_outputs(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    from autoclaw.runtime.effects import stage_dispatch_open_outputs

    stage_dispatch_open_outputs(session, task_id=task_id, dispatch_id=dispatch_id)


async def _close_node_sessions_for_dispatch(
    session: AsyncSession,
    *,
    dispatch_id: str,
    status: str,
    closed_at: datetime,
) -> None:
    rows = await session.scalars(
        select(NodeSessionModel).where(
            NodeSessionModel.dispatch_id == dispatch_id,
            NodeSessionModel.closed_at.is_(None),
        )
    )
    for row in rows:
        row.closed_at = closed_at
        row.session_status = status
