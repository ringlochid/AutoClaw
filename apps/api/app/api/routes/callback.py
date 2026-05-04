from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.runtime.contracts import ParentRootToolName
from app.runtime.control import (
    accept_boundary,
    call_parent_tool,
    record_checkpoint,
    validate_callback_session_key,
)
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


def _raise_runtime_error(exc: Exception) -> NoReturn:
    summary = str(exc)
    if isinstance(exc, FileNotFoundError) or "unknown " in summary or "missing " in summary:
        status_code = status.HTTP_404_NOT_FOUND
        code = "missing_target"
        retryable = False
    elif "stale" in summary:
        status_code = status.HTTP_409_CONFLICT
        code = "stale_write_conflict"
        retryable = True
    elif isinstance(exc, ValueError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        code = "semantic_invalid"
        retryable = False
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        code = "unexpected_failure"
        retryable = False
    raise HTTPException(
        status_code=status_code,
        detail={
            "ok": False,
            "code": code,
            "summary": summary,
            "retryable": retryable,
            "field_path": None,
            "suggested_next_step": None,
        },
    ) from exc


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
        await session.commit()
        return result
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await session.rollback()
        _raise_runtime_error(exc)


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
        await session.commit()
        return result
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await session.rollback()
        _raise_runtime_error(exc)


@router.post("/tasks/{task_id}/tools/{tool_name}", response_model=ParentToolSuccess)
async def post_tool(
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
    session: DBSession,
    session_key: str = Header(..., alias="X-Autoclaw-Session-Key"),
) -> ParentToolSuccess:
    if payload.tool_name != tool_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tool_name path/body mismatch",
        )
    try:
        await validate_callback_session_key(session, task_id=task_id, session_key=session_key)
        result = await call_parent_tool(session, task_id, tool_name, payload)
        await session.commit()
        return result
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await session.rollback()
        _raise_runtime_error(exc)
