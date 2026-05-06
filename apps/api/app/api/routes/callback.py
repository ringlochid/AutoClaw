from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import raise_operation_failure, raise_runtime_exception
from app.db.session import get_db_session
from app.runtime.contracts import ParentRootToolName
from app.runtime.control import (
    accept_boundary,
    call_parent_tool,
    record_checkpoint,
    validate_callback_session_key,
)
from app.runtime.post_commit import commit_runtime_session, rollback_runtime_session
from app.schemas.operation_failure import OperationFailureCode
from app.schemas.runtime import (
    BoundaryRead,
    BoundaryWrite,
    CheckpointRead,
    CheckpointWrite,
    ParentToolCall,
    ParentToolSuccess,
)

router = APIRouter(prefix="/callback", tags=["callback"])
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/tasks/{task_id}/checkpoint", response_model=CheckpointRead)
async def post_checkpoint(
    task_id: str,
    payload: CheckpointWrite,
    session: DBSession,
    session_key: str = Header(..., alias="X-Autoclaw-Session-Key"),
) -> CheckpointRead:
    try:
        await validate_callback_session_key(session, task_id=task_id, session_key=session_key)
        result = await record_checkpoint(session, task_id, payload)
        await commit_runtime_session(session)
        return result
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await rollback_runtime_session(session)
        raise_runtime_exception(exc)


@router.post("/tasks/{task_id}/boundary", response_model=BoundaryRead)
async def post_boundary(
    task_id: str,
    payload: BoundaryWrite,
    session: DBSession,
    session_key: str = Header(..., alias="X-Autoclaw-Session-Key"),
) -> BoundaryRead:
    try:
        await validate_callback_session_key(session, task_id=task_id, session_key=session_key)
        result = await accept_boundary(session, task_id, payload)
        await commit_runtime_session(session)
        return result
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await rollback_runtime_session(session)
        raise_runtime_exception(exc)


@router.post("/tasks/{task_id}/tools/{tool_name}", response_model=ParentToolSuccess)
async def post_tool(
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
    session: DBSession,
    session_key: str = Header(..., alias="X-Autoclaw-Session-Key"),
) -> ParentToolSuccess:
    if payload.tool_name != tool_name:
        raise_operation_failure(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=OperationFailureCode.INVALID_REQUEST_SHAPE,
            summary="tool_name path/body mismatch",
            retryable=False,
            field_path="tool_name",
        )
    try:
        await validate_callback_session_key(session, task_id=task_id, session_key=session_key)
        result = await call_parent_tool(session, task_id, tool_name, payload)
        await commit_runtime_session(session)
        return result
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await rollback_runtime_session(session)
        raise_runtime_exception(exc)
