from __future__ import annotations

from app.db.models import (
    DispatchCallbackBindingModel,
    DispatchTurnModel,
    FlowModel,
    NodeSessionModel,
)
from app.db.session import get_session_factory
from app.runtime.control.dispatch.callbacks import validate_callback_session_key
from app.runtime.control.failures import RuntimeOperationError, stale_dispatch_error
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class NodeMcpBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    dispatch_id: str
    node_session_id: str
    callback_session_key: str


async def load_current_node_mcp_binding(task_id: str) -> NodeMcpBinding:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await _load_current_node_mcp_binding(session, task_id)


async def load_node_mcp_binding_by_session_key(
    session_key: str,
    *,
    expected_task_id: str | None = None,
) -> NodeMcpBinding:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await _load_node_mcp_binding_by_session_key(
            session,
            session_key,
            expected_task_id=expected_task_id,
        )


async def _load_current_node_mcp_binding(
    session: AsyncSession,
    task_id: str,
) -> NodeMcpBinding:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    if flow is None or flow.current_open_dispatch_id is None:
        raise RuntimeError(f"task '{task_id}' has no current open dispatch")
    dispatch_id = flow.current_open_dispatch_id
    node_session = await session.scalar(
        select(NodeSessionModel).where(
            NodeSessionModel.dispatch_id == dispatch_id,
            NodeSessionModel.session_status == "live",
            NodeSessionModel.closed_at.is_(None),
        )
    )
    if node_session is None:
        raise RuntimeError(f"dispatch '{dispatch_id}' has no live node session")
    return await _build_node_mcp_binding(
        session,
        task_id=task_id,
        dispatch_id=dispatch_id,
        node_session=node_session,
    )


async def _load_node_mcp_binding_by_session_key(
    session: AsyncSession,
    session_key: str,
    *,
    expected_task_id: str | None = None,
) -> NodeMcpBinding:
    node_session = await session.scalar(
        select(NodeSessionModel).where(
            NodeSessionModel.session_key == session_key,
            NodeSessionModel.session_status == "live",
            NodeSessionModel.closed_at.is_(None),
        )
    )
    if node_session is None or node_session.dispatch_id is None:
        raise RuntimeError(f"session key '{session_key}' has no live node session")
    dispatch = await session.get(DispatchTurnModel, node_session.dispatch_id)
    if dispatch is None:
        raise RuntimeError(f"session key '{session_key}' has no live dispatch")
    if expected_task_id is not None and expected_task_id != dispatch.task_id:
        raise ValueError(
            f"session key '{session_key}' is not bound to task '{expected_task_id}'"
        )
    return await _build_node_mcp_binding(
        session,
        task_id=dispatch.task_id,
        dispatch_id=dispatch.dispatch_id,
        node_session=node_session,
    )


async def _build_node_mcp_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    node_session: NodeSessionModel,
) -> NodeMcpBinding:
    callback_binding = await session.scalar(
        select(DispatchCallbackBindingModel).where(
            DispatchCallbackBindingModel.task_id == task_id,
            DispatchCallbackBindingModel.dispatch_id == dispatch_id,
            DispatchCallbackBindingModel.binding_status == "live",
            DispatchCallbackBindingModel.revoked_at.is_(None),
        )
    )
    if callback_binding is None:
        raise RuntimeError(f"dispatch '{dispatch_id}' has no live callback binding")
    return NodeMcpBinding(
        task_id=task_id,
        dispatch_id=dispatch_id,
        node_session_id=node_session.node_session_id,
        callback_session_key=callback_binding.session_key,
    )


async def validate_node_mcp_binding(
    session: AsyncSession,
    binding: NodeMcpBinding,
) -> None:
    await validate_callback_session_key(
        session,
        task_id=binding.task_id,
        session_key=binding.callback_session_key,
    )
    callback_binding = await session.scalar(
        select(DispatchCallbackBindingModel).where(
            DispatchCallbackBindingModel.task_id == binding.task_id,
            DispatchCallbackBindingModel.session_key == binding.callback_session_key,
        )
    )
    if callback_binding is None or callback_binding.dispatch_id != binding.dispatch_id:
        raise stale_dispatch_error("stale callback session key")
    dispatch = await session.get(DispatchTurnModel, binding.dispatch_id)
    if dispatch is None:
        raise stale_dispatch_error("stale callback session key")
    node_session = await session.get(NodeSessionModel, binding.node_session_id)
    if node_session is None or node_session.dispatch_id != binding.dispatch_id:
        raise stale_dispatch_error("stale callback session key")
    if node_session.session_status != "live" or node_session.closed_at is not None:
        raise stale_dispatch_error("stale callback session key")
    if dispatch.gateway_session_key != node_session.session_key:
        raise stale_dispatch_error("stale callback session key")


async def load_validated_node_mcp_binding_by_session_key(
    session_key: str,
    *,
    expected_task_id: str | None = None,
) -> NodeMcpBinding:
    session_factory = get_session_factory()
    async with session_factory() as session:
        binding = await _load_node_mcp_binding_by_session_key(
            session,
            session_key,
            expected_task_id=expected_task_id,
        )
        try:
            await validate_node_mcp_binding(session, binding)
        except RuntimeOperationError as exc:
            raise RuntimeError(exc.summary) from exc
        return binding


__all__ = [
    "NodeMcpBinding",
    "load_current_node_mcp_binding",
    "load_node_mcp_binding_by_session_key",
    "load_validated_node_mcp_binding_by_session_key",
    "validate_node_mcp_binding",
]
