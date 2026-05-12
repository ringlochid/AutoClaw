from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssignmentModel,
    DispatchCallbackBindingModel,
    DispatchTurnModel,
    FlowNodeModel,
)
from app.runtime.contracts import FlowStatus
from app.runtime.control.clock import utc_now
from app.runtime.control.flow_queries import require_flow_for_task
from app.runtime.ids import dispatch_callback_binding_id


async def validate_callback_session_key(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
) -> None:
    binding = await session.scalar(
        select(DispatchCallbackBindingModel).where(
            DispatchCallbackBindingModel.task_id == task_id,
            DispatchCallbackBindingModel.session_key == session_key,
        )
    )
    if binding is None:
        raise ValueError("invalid callback session key")
    if binding.binding_status != "live" or binding.revoked_at is not None:
        raise ValueError("stale callback session key")
    flow = await require_flow_for_task(session, task_id)
    if flow.status != FlowStatus.RUNNING.value:
        raise ValueError("inactive callback session key")
    dispatch = await session.get(DispatchTurnModel, binding.dispatch_id)
    if dispatch is None or dispatch.task_id != task_id:
        raise ValueError("stale callback session key")
    if flow.current_open_dispatch_id != binding.dispatch_id:
        raise ValueError("stale callback session key")
    if dispatch.dispatch_id != flow.current_open_dispatch_id:
        raise ValueError("stale callback session key")
    if dispatch.control_state != "live" or dispatch.closed_at is not None:
        raise ValueError("stale callback session key")
    if dispatch.assignment_id != binding.assignment_id or dispatch.attempt_id != binding.attempt_id:
        raise ValueError("stale callback session key")
    if flow.current_node_key != dispatch.node_key:
        raise ValueError("stale callback session key")

    assignment = await session.get(AssignmentModel, binding.assignment_id)
    if assignment is None or assignment.task_id != task_id:
        raise ValueError("stale callback session key")
    if assignment.current_attempt_id != binding.attempt_id:
        raise ValueError("stale callback session key")

    current_assignment_id = await session.scalar(
        select(FlowNodeModel.current_assignment_id).where(
            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
            FlowNodeModel.node_key == dispatch.node_key,
        )
    )
    if current_assignment_id != binding.assignment_id:
        raise ValueError("stale callback session key")


async def revoke_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    binding = await _live_callback_binding(session, task_id=task_id, dispatch_id=dispatch_id)
    if binding is None:
        return
    binding.binding_status = "revoked"
    binding.revoked_at = utc_now()
    await session.flush()


async def create_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    attempt_id: str,
    assignment_id: str,
) -> DispatchCallbackBindingModel:
    binding = DispatchCallbackBindingModel(
        dispatch_callback_binding_id=dispatch_callback_binding_id(dispatch_id),
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
        assignment_id=assignment_id,
        task_id=task_id,
        session_key=__import__("secrets").token_urlsafe(24),
        binding_status="live",
    )
    session.add(binding)
    await session.flush()
    return binding


async def _live_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> DispatchCallbackBindingModel | None:
    result = await session.execute(
        select(DispatchCallbackBindingModel).where(
            DispatchCallbackBindingModel.task_id == task_id,
            DispatchCallbackBindingModel.dispatch_id == dispatch_id,
            DispatchCallbackBindingModel.binding_status == "live",
            DispatchCallbackBindingModel.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()
