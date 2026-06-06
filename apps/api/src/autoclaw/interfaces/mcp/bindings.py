from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.persistence.models import FlowModel, NodeSessionModel
from autoclaw.persistence.session import get_session_factory
from autoclaw.runtime.post_commit import wait_for_runtime_effects


class NodeToolContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    session_key: str


async def load_current_node_tool_context(task_id: str) -> NodeToolContext:
    session_factory = get_session_factory()
    initial_error = await _read_current_node_tool_context(session_factory, task_id)
    if not isinstance(initial_error, RuntimeError):
        return initial_error

    await wait_for_runtime_effects(task_id=task_id)

    final_error = await _read_current_node_tool_context(session_factory, task_id)
    if isinstance(final_error, RuntimeError):
        raise final_error
    return final_error


async def _read_current_node_tool_context(
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> NodeToolContext | RuntimeError:
    async with session_factory() as session:
        try:
            return await _load_current_node_tool_context(session, task_id)
        except RuntimeError as exc:
            return exc


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
