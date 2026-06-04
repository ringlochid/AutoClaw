from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import DispatchDeliveryStateModel, DispatchTurnModel, FlowModel
from app.runtime.contracts import FlowStatus
from app.runtime.control.failures import RuntimeOperationError
from app.runtime.control.flow.reads import latest_unreplaced_fenced_dispatch
from app.runtime.control.flow.resume import resolve_flow_resume_target
from app.runtime.effects.dispatch_reconcile import dispatch_requires_lifecycle_reconcile


async def task_pending_reconcile(
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None:
            return False
        if flow.current_open_dispatch_id is None:
            return flow.status == FlowStatus.RUNNING.value and await task_can_auto_open_dispatch(
                session,
                task_id=task_id,
                flow=flow,
            )
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        if dispatch is None:
            return False
        if fenced_current_dispatch_needs_flow_cleanup(flow, dispatch):
            return True
        lingering_boundary_dispatch = await latest_lingering_boundary_dispatch(
            session,
            task_id=task_id,
            current_open_dispatch_id=flow.current_open_dispatch_id,
        )
        if lingering_boundary_dispatch is not None:
            lingering_delivery_state = await session.get(
                DispatchDeliveryStateModel,
                lingering_boundary_dispatch.dispatch_id,
            )
            if dispatch_requires_lifecycle_reconcile(
                lingering_boundary_dispatch,
                delivery_state=lingering_delivery_state,
            ):
                return True
        delivery_state = await session.get(
            DispatchDeliveryStateModel,
            flow.current_open_dispatch_id,
        )
        if dispatch_requires_lifecycle_reconcile(
            dispatch,
            delivery_state=delivery_state,
        ):
            return True
        return False


async def task_can_auto_open_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
) -> bool:
    previous_dispatch = await latest_unreplaced_fenced_dispatch(session, task_id=task_id)
    if previous_dispatch is None or previous_dispatch.accepted_boundary is None:
        return False
    try:
        resume_target = await resolve_flow_resume_target(
            session,
            flow=flow,
            previous_dispatch=previous_dispatch,
        )
    except RuntimeOperationError as exc:
        if exc.summary == "current semantic target is incomplete":
            return False
        raise
    return resume_target.dispatch_open_inputs() is not None


async def runtime_predicate_value(
    predicate: Callable[[], bool | Awaitable[bool]],
) -> bool:
    value = predicate()
    if isinstance(value, bool):
        return value
    return bool(await value)


def fenced_current_dispatch_needs_flow_cleanup(
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> bool:
    return (
        flow.current_open_dispatch_id == dispatch.dispatch_id and dispatch.control_state == "fenced"
    )


async def latest_lingering_boundary_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    current_open_dispatch_id: str | None,
) -> DispatchTurnModel | None:
    return cast(
        DispatchTurnModel | None,
        await session.scalar(
            select(DispatchTurnModel)
            .where(
                DispatchTurnModel.task_id == task_id,
                DispatchTurnModel.dispatch_id != (current_open_dispatch_id or ""),
                DispatchTurnModel.accepted_boundary.is_not(None),
                DispatchTurnModel.closed_at.is_not(None),
                DispatchTurnModel.fenced_at.is_(None),
                DispatchTurnModel.control_state.not_in(("fenced", "ambiguous")),
            )
            .order_by(DispatchTurnModel.rendered_at.desc())
        ),
    )


__all__ = [
    "fenced_current_dispatch_needs_flow_cleanup",
    "latest_lingering_boundary_dispatch",
    "runtime_predicate_value",
    "task_can_auto_open_dispatch",
    "task_pending_reconcile",
]
