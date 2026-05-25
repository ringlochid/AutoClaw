from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchDeliveryStateModel, DispatchTurnModel, FlowModel
from app.runtime.contracts import DispatchDeliveryStatus, FlowStatus
from app.runtime.control.dispatch import control as dispatch_control
from app.runtime.control.dispatch import gateway as dispatch_gateway
from app.runtime.effects.dispatch_reconcile import (
    dispatch_requires_lifecycle_reconcile,
    mark_gateway_wait_ambiguous,
    reconcile_gateway_dispatch,
)
from app.runtime.effects.task_reconcile_state import (
    fenced_current_dispatch_needs_flow_cleanup,
    latest_lingering_boundary_dispatch,
)

LOGGER = logging.getLogger(__name__)


async def load_current_dispatch(
    session: AsyncSession,
    *,
    flow: FlowModel,
    task_id: str,
) -> DispatchTurnModel | None:
    if flow.current_open_dispatch_id is None:
        return None
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
    if dispatch is not None:
        return dispatch
    LOGGER.warning(
        "missing current dispatch %s for task %s during lifecycle reconciliation",
        flow.current_open_dispatch_id,
        task_id,
    )
    return None


async def reconcile_lingering_boundary_dispatch(
    session: AsyncSession,
    *,
    flow: FlowModel,
    task_id: str,
    current_open_dispatch_id: str | None,
    pending: bool,
    changed: bool,
) -> tuple[bool, bool]:
    lingering_boundary_dispatch = await latest_lingering_boundary_dispatch(
        session,
        task_id=task_id,
        current_open_dispatch_id=current_open_dispatch_id,
    )
    if lingering_boundary_dispatch is None:
        return pending, changed
    lingering_delivery_state = await session.get(
        DispatchDeliveryStateModel,
        lingering_boundary_dispatch.dispatch_id,
    )
    if not dispatch_requires_lifecycle_reconcile(
        lingering_boundary_dispatch,
        delivery_state=lingering_delivery_state,
    ):
        return pending, changed
    lingering_pending, lingering_changed = await reconcile_gateway_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=lingering_boundary_dispatch,
    )
    return pending or lingering_pending, changed or lingering_changed


async def reconcile_current_dispatch(
    session: AsyncSession,
    *,
    flow: FlowModel,
    task_id: str,
    dispatch: DispatchTurnModel | None,
    pending: bool,
    changed: bool,
) -> tuple[bool, bool]:
    if dispatch is None:
        return pending, changed
    aggressive_cleanup = flow.status in {FlowStatus.PAUSED.value, FlowStatus.CANCELLED.value}
    delivery_state = await session.get(
        DispatchDeliveryStateModel,
        flow.current_open_dispatch_id,
    )
    if fenced_current_dispatch_needs_flow_cleanup(flow, dispatch):
        flow.current_open_dispatch_id = None
        return pending, True
    if dispatch.control_state == "ambiguous":
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
    if dispatch.control_state == "fenced":
        return False, changed
    if dispatch_control.dispatch_inactivity_proven(dispatch):
        await dispatch_control.fence_foreground_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
        )
        return pending, True
    if dispatch_control.dispatch_deadline_expired(dispatch):
        if aggressive_cleanup:
            reason = dispatch.control_state_reason or "foreground_dispatch"
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
            return pending, True
        await mark_gateway_wait_ambiguous(
            session,
            task_id=task_id,
            dispatch=dispatch,
        )
        return pending, True
    if not dispatch_requires_lifecycle_reconcile(
        dispatch,
        delivery_state=delivery_state,
    ):
        return pending, changed
    task_pending, task_changed = await reconcile_gateway_dispatch(
        session,
        task_id=task_id,
        flow=flow,
        dispatch=dispatch,
    )
    return task_pending, changed or task_changed


__all__ = [
    "load_current_dispatch",
    "reconcile_current_dispatch",
    "reconcile_lingering_boundary_dispatch",
]
