from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssignmentModel,
    AttemptModel,
    DispatchTurnModel,
    FlowNodeModel,
)
from app.runtime.contracts import PromptSendMode
from app.runtime.control.dispatch_control import (
    open_dispatch_for_attempt as _open_dispatch_for_attempt,
)

__all__ = [
    "flow_node_by_key",
    "open_dispatch_for_attempt",
]


async def flow_node_by_key(
    session: AsyncSession,
    flow_revision_id: str,
    node_key: str,
) -> FlowNodeModel:
    node = await session.scalar(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == flow_revision_id,
            FlowNodeModel.node_key == node_key,
        )
    )
    if node is None:
        raise ValueError(f"unknown node_key '{node_key}'")
    return node


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
    return await _open_dispatch_for_attempt(
        session,
        task_id=task_id,
        node=node,
        assignment=assignment,
        attempt=attempt,
        send_mode=send_mode,
        previous_dispatch_id=previous_dispatch_id,
        staged_child_assignment_id=staged_child_assignment_id,
        phase=phase,
    )
