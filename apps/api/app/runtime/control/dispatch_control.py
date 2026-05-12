from __future__ import annotations

from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssignmentModel,
    AttemptModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
)
from app.runtime.contracts import (
    DispatchDeliveryStatus,
    FlowStatus,
    PromptSendMode,
)
from app.runtime.control.clock import utc_now
from app.runtime.control.dispatch_opening import (
    activate_dispatch_turn,
    prepare_dispatch_turn,
)
from app.runtime.control.flow_queries import require_flow_for_task
from app.runtime.control.surfaces import queue_dispatch_materialization
from app.runtime.control.workspace_leases import release_workspace_root_lease

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
    DispatchDeliveryStatus.TRANSPORT_FAILED.value,
}


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
) -> None:
    fenced_at = utc_now()
    delivery_status = (
        dispatch.delivery_status
        if dispatch.delivery_status in INACTIVITY_PROVEN_DELIVERY_STATUSES
        else DispatchDeliveryStatus.PROVIDER_COMPLETED.value
    )
    dispatch.control_state = "fenced"
    dispatch.control_state_reason = reason
    dispatch.control_deadline_at = None
    dispatch.fenced_at = dispatch.fenced_at or fenced_at
    dispatch.delivery_status = delivery_status
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_state = delivery_status
        delivery_state.controller_observation_state = "fenced"
        delivery_state.last_controller_terminal_at = fenced_at
        delivery_state.updated_at = fenced_at
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
        delivery_state.controller_observation_state = "ambiguous"
        delivery_state.last_controller_terminal_at = ambiguous_at
        delivery_state.updated_at = ambiguous_at
    await session.flush()


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
        raise ValueError(f"missing dispatch '{flow.current_open_dispatch_id}'")
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
        await mark_dispatch_ambiguous(
            session,
            dispatch=dispatch,
            reason=f"{reason}:timed_out",
        )
        queue_dispatch_materialization(
            session,
            task_id=task_id,
            dispatch_id=dispatch.dispatch_id,
        )
        raise ValueError("foreground dispatch timed out before inactivity was proven")
    if dispatch.control_state == "abort_requested":
        raise ValueError("current dispatch is still awaiting inactivity proof after abort")
    if dispatch.control_state == "ambiguous":
        raise ValueError("foreground dispatch timed out before inactivity was proven")
    if dispatch.control_state == "fenced":
        flow.current_open_dispatch_id = None
        await session.flush()
        return dispatch
    raise ValueError("current dispatch is still awaiting inactivity proof")


async def open_dispatch_for_attempt(
    session: AsyncSession,
    *,
    task_id: str,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    send_mode: PromptSendMode,
    previous_dispatch_id: str | None,
    staged_child_assignment_id: str | None = None,
    phase: str = "execution",
) -> DispatchTurnModel:
    flow = await require_flow_for_task(session, task_id)
    if flow.current_open_dispatch_id is not None:
        raise ValueError("cannot open a replacement dispatch while another dispatch is current")
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
        send_mode=send_mode,
        previous_dispatch=previous_dispatch,
        staged_child_assignment_id=staged_child_assignment_id,
        phase=phase,
    )
    return await activate_dispatch_turn(
        session,
        task_id=task_id,
        dispatch=dispatch,
        node=node,
        assignment=assignment,
        attempt=attempt,
    )


def _foreground_inactivity_reason(dispatch: DispatchTurnModel) -> str:
    if dispatch.control_state == "abort_requested":
        reason = dispatch.control_state_reason or "abort_requested"
        return f"{reason}:inactive_proven"
    if dispatch.accepted_boundary is not None:
        return f"boundary:{dispatch.accepted_boundary}:inactive_proven"
    reason = dispatch.control_state_reason or "foreground_dispatch"
    return f"{reason}:inactive_proven"


async def fence_foreground_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> DispatchTurnModel:
    await mark_dispatch_fenced(
        session,
        dispatch=dispatch,
        reason=_foreground_inactivity_reason(dispatch),
    )
    flow.current_open_dispatch_id = None
    if flow.status in {
        FlowStatus.SUCCEEDED.value,
        FlowStatus.BLOCKED.value,
        FlowStatus.CANCELLED.value,
    }:
        await release_workspace_root_lease(session, task_id=task_id)
    queue_dispatch_materialization(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
    )
    await session.flush()
    return dispatch


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
        raise ValueError(f"missing previous dispatch '{previous_dispatch_id}'")
    if previous_dispatch.control_state in REPLACEMENT_BLOCKING_CONTROL_STATES:
        raise ValueError(
            "replacement dispatch is illegal until the previous dispatch is proven inactive"
        )
    if previous_dispatch.control_state != "fenced":
        raise ValueError("replacement dispatch requires a fenced previous dispatch")
