from __future__ import annotations

from app.runtime.effects import wait_for_runtime_effects
from autoclaw.db.models import FlowModel, NodeSessionModel
from autoclaw.db.session import get_session_factory
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class NodeToolContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    session_key: str


async def load_current_node_tool_context(task_id: str) -> NodeToolContext:
    session_factory = get_session_factory()
    last_error: RuntimeError | None = None
    for _ in range(20):
        async with session_factory() as session:
            try:
                return await _load_current_node_tool_context(session, task_id)
            except RuntimeError as exc:
                last_error = exc
        await wait_for_runtime_effects(task_id=task_id)
    assert last_error is not None
    raise last_error


async def _load_current_node_tool_context(
    session: AsyncSession,
    task_id: str,
) -> NodeToolContext:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    if flow is None or flow.current_open_dispatch_id is None:
        raise RuntimeError(f"task '{task_id}' has no current open dispatch")

    node_session = await session.scalar(
        select(NodeSessionModel)
        .where(
            NodeSessionModel.dispatch_id == flow.current_open_dispatch_id,
            NodeSessionModel.session_status == "live",
            NodeSessionModel.closed_at.is_(None),
        )
        .order_by(NodeSessionModel.opened_at.desc())
        .limit(1)
    )
    if node_session is None:
        raise RuntimeError(f"dispatch '{flow.current_open_dispatch_id}' has no live node session")

    return NodeToolContext(
        task_id=task_id,
        session_key=node_session.session_key,
    )


__all__ = ["NodeToolContext", "load_current_node_tool_context"]
