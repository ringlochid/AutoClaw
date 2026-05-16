from __future__ import annotations

from dataclasses import dataclass
from typing import cast, overload

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchTurnModel
from app.runtime.contracts import ParentRootToolName
from app.runtime.control.boundary.service import accept_boundary
from app.runtime.control.checkpoint.recording import record_checkpoint
from app.runtime.control.dispatch.callbacks import validate_callback_session_key
from app.runtime.control.parent_tools import call_parent_tool, validate_parent_tool_call
from app.runtime.effects.writes import DeferredRuntimeWrite, run_runtime_write
from app.runtime.projection.runtime_state import CurrentRuntimeState, dispatch_runtime_state
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
    authority = await validate_callback_session_key(
        session,
        task_id=task_id,
        session_key=session_key,
    )
    dispatch = await session.get(DispatchTurnModel, authority.dispatch_id)
    assert dispatch is not None
    state = await dispatch_runtime_state(session, task_id=task_id, dispatch=dispatch)
    return await execute_bound_node_operation(
        session,
        task_id=task_id,
        operation=operation,
        state=state,
        dispatch=dispatch,
    )


@overload
async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: CheckpointNodeOperation,
    state: object | None = None,
    dispatch: object | None = None,
) -> CheckpointRead: ...


@overload
async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: BoundaryNodeOperation,
    state: object | None = None,
    dispatch: object | None = None,
) -> BoundaryRead: ...


@overload
async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: ParentToolNodeOperation,
    state: object | None = None,
    dispatch: object | None = None,
) -> ParentToolSuccess: ...


async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: NodeOperation,
    state: object | None = None,
    dispatch: object | None = None,
) -> NodeOperationResult:
    return await run_runtime_write(
        session,
        lambda: _apply_node_operation(
            session,
            task_id=task_id,
            operation=operation,
            state=cast(CurrentRuntimeState | None, state),
            dispatch=cast(DispatchTurnModel | None, dispatch),
        ),
    )


async def _apply_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: NodeOperation,
    state: CurrentRuntimeState | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> NodeOperationResult | DeferredRuntimeWrite[NodeOperationResult]:
    if isinstance(operation, CheckpointNodeOperation):
        return await record_checkpoint(
            session,
            task_id,
            operation.payload,
            state=state,
            dispatch=dispatch,
        )
    if isinstance(operation, BoundaryNodeOperation):
        return cast(
            DeferredRuntimeWrite[NodeOperationResult] | NodeOperationResult,
            await accept_boundary(
                session,
                task_id,
                operation.payload,
                read_after_commit=True,
                state=state,
                dispatch=dispatch,
            ),
        )
    validate_parent_tool_call(operation.tool_name, operation.payload)
    return cast(
        DeferredRuntimeWrite[NodeOperationResult] | NodeOperationResult,
        await call_parent_tool(
            session,
            task_id,
            operation.tool_name,
            operation.payload,
            read_after_commit=True,
            state=state,
            dispatch=dispatch,
        ),
    )


__all__ = [
    "BoundaryNodeOperation",
    "CheckpointNodeOperation",
    "NodeOperation",
    "NodeOperationResult",
    "ParentToolNodeOperation",
    "execute_bound_node_operation",
    "execute_node_operation",
]
