from __future__ import annotations

import asyncio
from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import get_settings
from autoclaw.persistence.models import DispatchDeliveryStateModel, DispatchTurnModel, FlowModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.dispatch import control as dispatch_control
from autoclaw.runtime.dispatch import gateway as dispatch_gateway
from autoclaw.runtime.dispatch.openclaw.lifecycle import close_dispatch_runtime
from autoclaw.runtime.post_commit.cases import stage_dispatch_open_outputs


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


async def transition_dispatch_to_abort_requested(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> None:
    await dispatch_control.request_dispatch_abort_after_close_timeout(
        session,
        task_id=task_id,
        dispatch=dispatch,
    )


async def fence_dispatch_after_abort_timeout(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> None:
    await dispatch_control.fence_foreground_dispatch_after_timeout(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
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
        return False, changed
    try:
        wait_result = await dispatch_gateway.wait_for_gateway_dispatch(
            dispatch=dispatch,
            timeout_ms=gateway_wait_timeout_ms(dispatch),
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


def gateway_wait_timeout_ms(dispatch: DispatchTurnModel) -> int:
    configured_slice_timeout_ms = max(1, get_settings().runtime.provider_wait_timeout_slice_ms)
    deadline = dispatch.control_deadline_at
    if deadline is None:
        return configured_slice_timeout_ms
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    remaining_ms = max(1, int((deadline - utc_now()).total_seconds() * 1000))
    return min(configured_slice_timeout_ms, remaining_ms)


async def _mark_gateway_wait_ambiguous(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> None:
    await dispatch_control.mark_foreground_dispatch_ambiguous_after_timeout(
        session,
        task_id=task_id,
        dispatch=dispatch,
    )
    await close_dispatch_runtime(dispatch.dispatch_id)


def _terminal_truth_commit_wait_settings() -> tuple[float, float]:
    runtime_settings = get_settings().runtime
    return (
        max(0.0, runtime_settings.terminal_truth_commit_grace_seconds),
        max(0.001, runtime_settings.terminal_truth_commit_poll_interval_seconds),
    )


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
    if dispatch.control_state == "live":
        await transition_dispatch_to_abort_requested(
            session,
            task_id=task_id,
            dispatch=dispatch,
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
    if dispatch.control_state == "abort_requested":
        await fence_dispatch_after_abort_timeout(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
        )
        return False, True
    await _mark_gateway_wait_ambiguous(session, task_id=task_id, dispatch=dispatch)
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
        wait_seconds, poll_interval_seconds = _terminal_truth_commit_wait_settings()
        deadline = loop.time() + wait_seconds
        while loop.time() < deadline:
            await asyncio.sleep(poll_interval_seconds)
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


__all__ = [
    "dispatch_requires_lifecycle_reconcile",
    "fence_dispatch_after_abort_timeout",
    "gateway_wait_timeout_ms",
    "reconcile_gateway_dispatch",
    "transition_dispatch_to_abort_requested",
]
