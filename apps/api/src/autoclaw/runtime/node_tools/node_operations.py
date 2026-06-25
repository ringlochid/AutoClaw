from __future__ import annotations

from dataclasses import dataclass
from typing import cast, overload

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import DispatchTurnModel
from autoclaw.runtime.boundary.service import accept_boundary
from autoclaw.runtime.checkpoint.recording import record_checkpoint
from autoclaw.runtime.contracts import (
    BoundaryRead,
    BoundaryWrite,
    CheckpointRead,
    CheckpointWrite,
    HumanRequestOpenRequest,
    HumanRequestOpenResponse,
    ParentRootToolName,
    ParentToolCall,
    ParentToolSuccess,
)
from autoclaw.runtime.dispatch.authority import validate_node_session_key
from autoclaw.runtime.human_requests import open_human_request
from autoclaw.runtime.node_tools.parent_tools import call_parent_tool, validate_parent_tool_call
from autoclaw.runtime.post_commit.writes import DeferredRuntimeWrite, commit_runtime_write
from autoclaw.runtime.projection.runtime_state import CurrentRuntimeState, dispatch_runtime_state

NodeOperationResult = CheckpointRead | BoundaryRead | ParentToolSuccess | HumanRequestOpenResponse


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


@dataclass(frozen=True)
class HumanRequestOpenNodeOperation:
    payload: HumanRequestOpenRequest


NodeOperation = (
    CheckpointNodeOperation
    | BoundaryNodeOperation
    | ParentToolNodeOperation
    | HumanRequestOpenNodeOperation
)


@overload
async def execute_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    operation: CheckpointNodeOperation,
    invalid_summary: str = "invalid session key",
    stale_summary: str = "stale session key",
    inactive_summary: str = "inactive session key",
) -> CheckpointRead: ...


@overload
async def execute_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    operation: BoundaryNodeOperation,
    invalid_summary: str = "invalid session key",
    stale_summary: str = "stale session key",
    inactive_summary: str = "inactive session key",
) -> BoundaryRead: ...


@overload
async def execute_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    operation: ParentToolNodeOperation,
    invalid_summary: str = "invalid session key",
    stale_summary: str = "stale session key",
    inactive_summary: str = "inactive session key",
) -> ParentToolSuccess: ...


@overload
async def execute_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    operation: HumanRequestOpenNodeOperation,
    invalid_summary: str = "invalid session key",
    stale_summary: str = "stale session key",
    inactive_summary: str = "inactive session key",
) -> HumanRequestOpenResponse: ...


async def execute_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
    operation: NodeOperation,
    invalid_summary: str = "invalid session key",
    stale_summary: str = "stale session key",
    inactive_summary: str = "inactive session key",
) -> NodeOperationResult:
    authority = await validate_node_session_key(
        session,
        task_id=task_id,
        session_key=session_key,
        invalid_summary=invalid_summary,
        stale_summary=stale_summary,
        inactive_summary=inactive_summary,
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


@overload
async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: HumanRequestOpenNodeOperation,
    state: object | None = None,
    dispatch: object | None = None,
) -> HumanRequestOpenResponse: ...


async def execute_bound_node_operation(
    session: AsyncSession,
    *,
    task_id: str,
    operation: NodeOperation,
    state: object | None = None,
    dispatch: object | None = None,
) -> NodeOperationResult:
    return await commit_runtime_write(
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
                should_read_after_commit=True,
                state=state,
                dispatch=dispatch,
            ),
        )
    if isinstance(operation, HumanRequestOpenNodeOperation):
        assert state is not None
        assert dispatch is not None
        return await open_human_request(
            session,
            task_id=task_id,
            request=operation.payload,
            state=state,
            dispatch=dispatch,
        )
    validate_parent_tool_call(operation.tool_name, operation.payload)
    return cast(
        DeferredRuntimeWrite[NodeOperationResult] | NodeOperationResult,
        await call_parent_tool(
            session,
            task_id,
            operation.tool_name,
            operation.payload,
            should_read_after_commit=True,
            state=state,
            dispatch=dispatch,
        ),
    )


__all__ = [
    "BoundaryNodeOperation",
    "CheckpointNodeOperation",
    "HumanRequestOpenNodeOperation",
    "NodeOperation",
    "NodeOperationResult",
    "ParentToolNodeOperation",
    "execute_bound_node_operation",
    "execute_node_operation",
]
