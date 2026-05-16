from __future__ import annotations

from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchDeliveryStateModel, DispatchTurnModel, FlowModel
from app.runtime.control.clock import utc_now
from app.runtime.control.dispatch import control as dispatch_control
from app.runtime.control.dispatch import gateway as dispatch_gateway
from app.runtime.effects.cases import stage_dispatch_open_outputs

_GATEWAY_WAIT_POLL_INTERVAL_MS = 250


def dispatch_requires_lifecycle_reconcile(
    dispatch: DispatchTurnModel,
    *,
    delivery_state: DispatchDeliveryStateModel | None,
) -> bool:
    return dispatch.control_state not in {"fenced", "ambiguous"} and (
        dispatch_control.dispatch_deadline_expired(dispatch)
        or dispatch_control.dispatch_waiting_for_inactivity(dispatch)
        or dispatch.control_state == "abort_requested"
        or _dispatch_waiting_for_first_progress(
            dispatch,
            delivery_state=delivery_state,
        )
    )


async def reconcile_gateway_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> tuple[bool, bool]:
    changed = False
    if dispatch.control_state == "abort_requested":
        try:
            changed = (
                await dispatch_gateway.abort_gateway_dispatch(session, dispatch=dispatch) or changed
            )
        except Exception as exc:
            changed = await _record_gateway_operation_failure(
                session,
                task_id=task_id,
                dispatch=dispatch,
                operation="sessions.abort",
                error=exc,
            )
            return True, changed
    if dispatch.gateway_run_id is None:
        return True, changed
    try:
        wait_result = await dispatch_gateway.wait_for_gateway_dispatch(
            dispatch=dispatch,
            timeout_ms=_gateway_wait_timeout_ms(dispatch),
        )
    except Exception as exc:
        changed = await _record_gateway_operation_failure(
            session,
            task_id=task_id,
            dispatch=dispatch,
            operation="agent.wait",
            error=exc,
        )
        return True, changed
    if wait_result.status.value == "timeout":
        if dispatch_control.dispatch_deadline_expired(dispatch):
            await mark_gateway_wait_ambiguous(session, task_id=task_id, dispatch=dispatch)
            return False, True
        return True, changed
    await dispatch_gateway.record_gateway_wait_terminal(
        session, dispatch=dispatch, wait_result=wait_result
    )
    await dispatch_control.fence_foreground_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    )
    return False, True


def _dispatch_waiting_for_first_progress(
    dispatch: DispatchTurnModel,
    *,
    delivery_state: DispatchDeliveryStateModel | None,
) -> bool:
    return (
        dispatch.control_state == "live"
        and dispatch.accepted_boundary is None
        and dispatch.gateway_run_id is not None
        and delivery_state is not None
        and delivery_state.transport_state == "accepted"
        and delivery_state.last_provider_signal_at is None
        and delivery_state.last_controller_progress_at is None
        and delivery_state.last_controller_terminal_at is None
    )


async def mark_gateway_wait_ambiguous(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> None:
    reason = dispatch.control_state_reason or "foreground_dispatch"
    await dispatch_gateway.record_gateway_wait_timeout(
        session,
        dispatch=dispatch,
        detail=f"{reason}:timed_out",
    )
    await dispatch_control.mark_dispatch_ambiguous(
        session,
        dispatch=dispatch,
        reason=f"{reason}:timed_out",
    )
    stage_dispatch_open_outputs(session, task_id=task_id, dispatch_id=dispatch.dispatch_id)


async def _record_gateway_operation_failure(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
    operation: str,
    error: Exception,
) -> bool:
    changed = await dispatch_gateway.record_gateway_transport_failure(
        session,
        dispatch=dispatch,
        operation=operation,
        error=error,
    )
    if changed:
        stage_dispatch_open_outputs(session, task_id=task_id, dispatch_id=dispatch.dispatch_id)
    return changed


def _gateway_wait_timeout_ms(dispatch: DispatchTurnModel) -> int:
    deadline = dispatch.control_deadline_at
    if deadline is None:
        return _GATEWAY_WAIT_POLL_INTERVAL_MS
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    remaining_ms = max(1, int((deadline - utc_now()).total_seconds() * 1000))
    return min(_GATEWAY_WAIT_POLL_INTERVAL_MS, remaining_ms)


__all__ = [
    "dispatch_requires_lifecycle_reconcile",
    "mark_gateway_wait_ambiguous",
    "reconcile_gateway_dispatch",
]
