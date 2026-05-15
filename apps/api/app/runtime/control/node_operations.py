from __future__ import annotations

from dataclasses import dataclass
from typing import overload

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.contracts import ParentRootToolName
from app.runtime.control.boundary.service import accept_boundary
from app.runtime.control.checkpoint.recording import record_checkpoint
from app.runtime.control.dispatch.callbacks import validate_callback_session_key
from app.runtime.control.parent_tools import call_parent_tool, validate_parent_tool_call
from app.runtime.effects.writes import run_runtime_write
from app.schemas.runtime import (
    BoundaryRead,
    BoundaryWrite,
    CheckpointRead,
    CheckpointWrite,
    ParentToolCall,
    ParentToolSuccess,
)

NodeOperationResult = CheckpointRead | BoundaryRead | ParentToolSuccess


@dataclass(frozen=True)
class CheckpointNodeOperation:
    payload: CheckpointWrite


@dataclass(frozen=True)
class BoundaryNodeOperation:
    payload: BoundaryWrite


@dataclass(frozen=True)
class ParentToolNodeOperation:
    tool_name: ParentRootToolName
    payload: ParentToolCall


NodeOperation = CheckpointNodeOperation | BoundaryNodeOperation | ParentToolNodeOperation


@overload
async def execute_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    operation: CheckpointNodeOperation,
) -> CheckpointRead: ...


@overload
async def execute_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    operation: BoundaryNodeOperation,
) -> BoundaryRead: ...


@overload
async def execute_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    operation: ParentToolNodeOperation,
) -> ParentToolSuccess: ...


async def execute_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    operation: NodeOperation,
) -> NodeOperationResult:
    await validate_callback_session_key(session, task_id=task_id, session_key=session_key)
    return await execute_bound_node_operation(
        session,
        task_id=task_id,
        operation=operation,
    )


@overload
async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: CheckpointNodeOperation,
) -> CheckpointRead: ...


@overload
async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: BoundaryNodeOperation,
) -> BoundaryRead: ...


@overload
async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: ParentToolNodeOperation,
) -> ParentToolSuccess: ...


async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: NodeOperation,
) -> NodeOperationResult:
    return await run_runtime_write(
        session,
        lambda: _apply_node_operation(session, task_id=task_id, operation=operation),
    )


async def _apply_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: NodeOperation,
) -> NodeOperationResult:
    if isinstance(operation, CheckpointNodeOperation):
        return await record_checkpoint(session, task_id, operation.payload)
    if isinstance(operation, BoundaryNodeOperation):
        return await accept_boundary(session, task_id, operation.payload)
    validate_parent_tool_call(operation.tool_name, operation.payload)
    return await call_parent_tool(session, task_id, operation.tool_name, operation.payload)


__all__ = [
    "BoundaryNodeOperation",
    "CheckpointNodeOperation",
    "NodeOperation",
    "NodeOperationResult",
    "ParentToolNodeOperation",
    "execute_bound_node_operation",
    "execute_node_operation",
]
