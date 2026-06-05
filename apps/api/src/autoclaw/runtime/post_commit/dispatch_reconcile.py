from __future__ import annotations

import asyncio
from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import DispatchDeliveryStateModel, DispatchTurnModel, FlowModel
from autoclaw.runtime.clock import dispatch_control_deadline, utc_now
from autoclaw.runtime.contracts import DispatchDeliveryStatus
from autoclaw.runtime.dispatch import control as dispatch_control
from autoclaw.runtime.dispatch import gateway as dispatch_gateway
from autoclaw.runtime.dispatch.openclaw.lifecycle import close_dispatch_runtime
from autoclaw.runtime.post_commit.cases import stage_dispatch_open_outputs

_GATEWAY_WAIT_POLL_INTERVAL_MS = 250
_RUNTIME_TERMINAL_COMMIT_WAIT_SECONDS = 0.5
_RUNTIME_TERMINAL_COMMIT_POLL_INTERVAL_SECONDS = 0.01


def dispatch_requires_lifecycle_reconcile(
    dispatch: DispatchTurnModel,
    *,
    delivery_state: DispatchDeliveryStateModel | None,
) -> bool:
    return dispatch.control_state not in {"fenced", "ambiguous"} and (
        dispatch_control.dispatch_inactivity_proven(dispatch)
        or dispatch_control.dispatch_deadline_expired(dispatch)
        or dispatch_control.dispatch_waiting_for_inactivity(dispatch)
        or dispatch.control_state == "abort_requested"
        or _dispatch_waiting_for_first_progress(
            dispatch,
            delivery_state=delivery_state,
        )
    )


async def transition_boundary_dispatch_to_abort_requested(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
    delivery_state: DispatchDeliveryStateModel | None,
) -> None:
    boundary = dispatch.accepted_boundary or "foreground_dispatch"
    requested_at = utc_now()
    dispatch.abort_requested_at = dispatch.abort_requested_at or requested_at
    dispatch.control_state = "abort_requested"
    dispatch.control_state_reason = f"boundary:{boundary}:abort_requested"
    dispatch.control_deadline_at = dispatch_control_deadline(base=requested_at)
    dispatch.closed_at = dispatch.closed_at or requested_at
    if delivery_state is not None:
        delivery_state.updated_at = requested_at
    stage_dispatch_open_outputs(session, task_id=task_id, dispatch_id=dispatch.dispatch_id)


async def fence_boundary_dispatch_after_timeout(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> None:
    reason = dispatch.control_state_reason or (
        f"boundary:{dispatch.accepted_boundary or 'foreground_dispatch'}:abort_requested"
    )
    await dispatch_gateway.record_gateway_wait_timeout(
        session,
        dispatch=dispatch,
        detail=f"{reason}:timed_out",
    )
    await dispatch_control.fence_foreground_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
        reason=f"{reason}:timed_out",
        delivery_status=DispatchDeliveryStatus.TRANSPORT_AMBIGUOUS.value,
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
    if await _fence_if_terminal_truth_committed(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    ):
        return False, True
    if dispatch.gateway_run_id is None:
        return True, changed
    try:
        wait_result = await dispatch_gateway.wait_for_gateway_dispatch(
            dispatch=dispatch,
            timeout_ms=_gateway_wait_timeout_ms(dispatch),
        )
    except Exception as exc:
        return await _reconcile_gateway_wait_exception(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
            error=exc,
        )
    if wait_result.status.value == "timeout":
        return await _reconcile_gateway_wait_timeout(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
            changed=changed,
        )
    if await _fence_if_terminal_truth_committed(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    ):
        return False, True
    await dispatch_gateway.record_gateway_wait_terminal(
        session, dispatch=dispatch, wait_result=wait_result
    )
    await dispatch_control.fence_foreground_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    )
    await close_dispatch_runtime(dispatch.dispatch_id)
    return False, True


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
    await close_dispatch_runtime(dispatch.dispatch_id)


async def _reconcile_gateway_wait_exception(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    error: Exception,
) -> tuple[bool, bool]:
    if await _fence_if_terminal_truth_committed(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    ):
        return False, True
    changed = await _record_gateway_operation_failure(
        session,
        task_id=task_id,
        dispatch=dispatch,
        operation="agent.wait",
        error=error,
    )
    return True, changed


async def _reconcile_gateway_wait_timeout(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    changed: bool,
) -> tuple[bool, bool]:
    if await _fence_if_terminal_truth_committed(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    ):
        return False, True
    if not dispatch_control.dispatch_deadline_expired(dispatch):
        return True, changed
    if dispatch.accepted_boundary is not None and dispatch.control_state == "live":
        delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
        await transition_boundary_dispatch_to_abort_requested(
            session,
            task_id=task_id,
            dispatch=dispatch,
            delivery_state=delivery_state,
        )
        return True, True
    if await _fence_if_terminal_truth_committed(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
        wait_for_runtime_close=True,
    ):
        return False, True
    if dispatch.accepted_boundary is not None and dispatch.control_state == "abort_requested":
        await fence_boundary_dispatch_after_timeout(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
        )
        return False, True
    await mark_gateway_wait_ambiguous(session, task_id=task_id, dispatch=dispatch)
    return False, True


async def _fence_if_terminal_truth_committed(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    wait_for_runtime_close: bool = False,
) -> bool:
    dispatch_id = dispatch.dispatch_id
    refreshed_dispatch = await _refresh_dispatch_runtime_state(
        session,
        dispatch_id=dispatch_id,
    )
    if refreshed_dispatch is None:
        return False
    dispatch = refreshed_dispatch
    if not dispatch_control.dispatch_inactivity_proven(dispatch):
        if not wait_for_runtime_close:
            return False
        # Release the current transaction before polling so the parallel ingest
        # writer can commit terminal truth that arrived during `agent.wait`.
        await session.rollback()
        refreshed_dispatch = await _refresh_dispatch_runtime_state(
            session,
            dispatch_id=dispatch_id,
        )
        if refreshed_dispatch is None:
            return False
        dispatch = refreshed_dispatch
        loop = asyncio.get_running_loop()
        deadline = loop.time() + _RUNTIME_TERMINAL_COMMIT_WAIT_SECONDS
        while loop.time() < deadline:
            await asyncio.sleep(_RUNTIME_TERMINAL_COMMIT_POLL_INTERVAL_SECONDS)
            refreshed_dispatch = await _refresh_dispatch_runtime_state(
                session,
                dispatch_id=dispatch_id,
            )
            if refreshed_dispatch is None:
                return False
            dispatch = refreshed_dispatch
            if dispatch_control.dispatch_inactivity_proven(dispatch):
                break
        if not dispatch_control.dispatch_inactivity_proven(dispatch):
            return False
    await dispatch_control.fence_foreground_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    )
    await close_dispatch_runtime(dispatch.dispatch_id)
    return True


async def _refresh_dispatch_runtime_state(
    session: AsyncSession,
    *,
    dispatch_id: str,
) -> DispatchTurnModel | None:
    dispatch = await session.get(
        DispatchTurnModel,
        dispatch_id,
        populate_existing=True,
    )
    await session.get(
        DispatchDeliveryStateModel,
        dispatch_id,
        populate_existing=True,
    )
    return dispatch


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
    "fence_boundary_dispatch_after_timeout",
    "mark_gateway_wait_ambiguous",
    "reconcile_gateway_dispatch",
    "transition_boundary_dispatch_to_abort_requested",
]
