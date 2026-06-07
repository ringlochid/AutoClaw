from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import DispatchDeliveryStateModel, DispatchTurnModel, FlowModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import DispatchDeliveryStatus, FlowStatus
from autoclaw.runtime.dispatch import control as dispatch_control
from autoclaw.runtime.dispatch import gateway as dispatch_gateway
from autoclaw.runtime.post_commit.cases import stage_dispatch_open_outputs
from autoclaw.runtime.post_commit.dispatch_reconcile import (
    dispatch_requires_lifecycle_reconcile,
    mark_gateway_wait_ambiguous,
    reconcile_gateway_dispatch,
)
from autoclaw.runtime.post_commit.task_reconcile_state import (
    fenced_current_dispatch_needs_flow_cleanup,
    latest_lingering_boundary_dispatch,
)

LOGGER = logging.getLogger(__name__)


async def reconcile_current_dispatch(
    session: AsyncSession,
    *,
    flow: FlowModel,
    task_id: str,
    dispatch: DispatchTurnModel | None,
    has_pending_runtime_work: bool,
    has_changed_runtime_truth: bool,
) -> tuple[bool, bool]:
    if dispatch is None:
        return has_pending_runtime_work, has_changed_runtime_truth
    aggressive_cleanup = flow.status in {FlowStatus.PAUSED.value, FlowStatus.CANCELLED.value}
    delivery_state = await session.get(
        DispatchDeliveryStateModel,
        flow.current_open_dispatch_id,
    )
    if fenced_current_dispatch_needs_flow_cleanup(flow, dispatch):
        flow.current_open_dispatch_id = None
        return has_pending_runtime_work, True
    if dispatch.control_state == "ambiguous":
        return await _reconcile_ambiguous_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
            aggressive_cleanup=aggressive_cleanup,
            pending=has_pending_runtime_work,
            changed=has_changed_runtime_truth,
        )
    if dispatch.control_state == "fenced":
        return False, has_changed_runtime_truth
    if dispatch_control.dispatch_inactivity_proven(dispatch):
        await dispatch_control.fence_foreground_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
        )
        return has_pending_runtime_work, True
    if dispatch_control.dispatch_deadline_expired(dispatch):
        return await _reconcile_expired_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
            aggressive_cleanup=aggressive_cleanup,
            pending=has_pending_runtime_work,
        )
    if not dispatch_requires_lifecycle_reconcile(
        dispatch,
        delivery_state=delivery_state,
    ):
        return has_pending_runtime_work, has_changed_runtime_truth
    task_pending, task_changed = await reconcile_gateway_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    )
    return task_pending, has_changed_runtime_truth or task_changed


async def reconcile_lingering_boundary_dispatch(
    session: AsyncSession,
    *,
    flow: FlowModel,
    task_id: str,
    current_open_dispatch_id: str | None,
    has_pending_runtime_work: bool,
    has_changed_runtime_truth: bool,
) -> tuple[bool, bool]:
    lingering_boundary_dispatch = await latest_lingering_boundary_dispatch(
        session,
        task_id=task_id,
        current_open_dispatch_id=current_open_dispatch_id,
    )
    if lingering_boundary_dispatch is None:
        return has_pending_runtime_work, has_changed_runtime_truth
    lingering_delivery_state = await session.get(
        DispatchDeliveryStateModel,
        lingering_boundary_dispatch.dispatch_id,
    )
    if not dispatch_requires_lifecycle_reconcile(
        lingering_boundary_dispatch,
        delivery_state=lingering_delivery_state,
    ):
        return has_pending_runtime_work, has_changed_runtime_truth
    lingering_pending, lingering_changed = await reconcile_gateway_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=lingering_boundary_dispatch,
    )
    return (
        has_pending_runtime_work or lingering_pending,
        has_changed_runtime_truth or lingering_changed,
    )


async def load_current_dispatch(
    session: AsyncSession,
    *,
    flow: FlowModel,
    task_id: str,
) -> tuple[DispatchTurnModel | None, bool]:
    if flow.current_open_dispatch_id is None:
        return None, False
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
    if dispatch is not None:
        return dispatch, False
    LOGGER.warning(
        "missing current dispatch %s for task %s during lifecycle reconciliation",
        flow.current_open_dispatch_id,
        task_id,
    )
    flow.current_open_dispatch_id = None
    flow.updated_at = utc_now()
    await session.flush()
    return None, True


async def _request_boundary_dispatch_abort(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> None:
    boundary = dispatch.accepted_boundary or "foreground_dispatch"
    requested_at = utc_now()
    await dispatch_control.mark_dispatch_abort_requested(
        session,
        dispatch=dispatch,
        reason=f"boundary:{boundary}:abort_requested",
        requested_at=requested_at,
    )
    stage_dispatch_open_outputs(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
    )


async def _fence_dispatch_with_timeout_ambiguity(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    reason: str,
) -> None:
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


def _boundary_abort_timeout_reason(dispatch: DispatchTurnModel) -> str:
    return dispatch.control_state_reason or (
        f"boundary:{dispatch.accepted_boundary}:abort_requested"
    )


def _should_begin_boundary_abort(dispatch: DispatchTurnModel) -> bool:
    return dispatch.control_state == "live" and dispatch.accepted_boundary is not None


def _should_force_fence_boundary_abort(dispatch: DispatchTurnModel) -> bool:
    return dispatch.control_state == "abort_requested" and dispatch.accepted_boundary is not None


async def _reconcile_ambiguous_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    aggressive_cleanup: bool,
    pending: bool,
    changed: bool,
) -> tuple[bool, bool]:
    if not aggressive_cleanup:
        return False, changed
    await dispatch_control.fence_foreground_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
        reason=dispatch.control_state_reason or "foreground_dispatch:cleanup",
        delivery_status=dispatch.delivery_status,
    )
    return pending, True


async def _reconcile_expired_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    aggressive_cleanup: bool,
    pending: bool,
) -> tuple[bool, bool]:
    if aggressive_cleanup:
        reason = dispatch.control_state_reason or "foreground_dispatch"
        await _fence_dispatch_with_timeout_ambiguity(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
            reason=reason,
        )
        return pending, True
    if _should_begin_boundary_abort(dispatch):
        await _request_boundary_dispatch_abort(
            session,
            task_id=task_id,
            dispatch=dispatch,
        )
        return True, True
    if _should_force_fence_boundary_abort(dispatch):
        await _fence_dispatch_with_timeout_ambiguity(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
            reason=_boundary_abort_timeout_reason(dispatch),
        )
        return pending, True
    await mark_gateway_wait_ambiguous(
        session,
        task_id=task_id,
        dispatch=dispatch,
    )
    return pending, True


__all__ = [
    "load_current_dispatch",
    "reconcile_current_dispatch",
    "reconcile_lingering_boundary_dispatch",
]
