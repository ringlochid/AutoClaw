from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import raise_runtime_exception
from app.db.session import get_db_session
from app.runtime.contracts import ParentRootToolName
from app.runtime.control.failures import invalid_request_shape_error
from app.runtime.control.node_operations import (
    BoundaryNodeOperation,
    CheckpointNodeOperation,
    ParentToolNodeOperation,
    execute_node_operation,
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


def _require_callback_session_key(session_key: str | None) -> str:
    if session_key is None:
        raise invalid_request_shape_error("callback session_key is required")
    return session_key


@router.post("/tasks/{task_id}/checkpoint", response_model=CheckpointRead)
async def post_checkpoint(
    task_id: str,
    payload: CheckpointWrite,
    session: DBSession,
    session_key: str | None = Query(default=None),
) -> CheckpointRead:
    try:
        return await execute_node_operation(
            session,
            task_id=task_id,
            session_key=_require_callback_session_key(session_key),
            operation=CheckpointNodeOperation(payload=payload),
            invalid_summary="invalid callback session key",
            stale_summary="stale callback session key",
            inactive_summary="inactive callback session key",
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post("/tasks/{task_id}/boundary", response_model=BoundaryRead)
async def post_boundary(
    task_id: str,
    payload: BoundaryWrite,
    session: DBSession,
    session_key: str | None = Query(default=None),
) -> BoundaryRead:
    try:
        return await execute_node_operation(
            session,
            task_id=task_id,
            session_key=_require_callback_session_key(session_key),
            operation=BoundaryNodeOperation(payload=payload),
            invalid_summary="invalid callback session key",
            stale_summary="stale callback session key",
            inactive_summary="inactive callback session key",
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post("/tasks/{task_id}/tools/{tool_name}", response_model=ParentToolSuccess)
async def post_tool(
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
    session: DBSession,
    session_key: str | None = Query(default=None),
) -> ParentToolSuccess:
    try:
        return await execute_node_operation(
            session,
            task_id=task_id,
            session_key=_require_callback_session_key(session_key),
            operation=ParentToolNodeOperation(tool_name=tool_name, payload=payload),
            invalid_summary="invalid callback session key",
            stale_summary="stale callback session key",
            inactive_summary="inactive callback session key",
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)
