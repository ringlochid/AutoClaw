from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.runtime.control import operator_snapshot, operator_trace
from app.schemas.runtime import OperatorFlowSnapshotResponse, OperatorFlowTraceResponse

router = APIRouter(prefix="/operator", tags=["operator"])
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


@router.get("/tasks/{task_id}/snapshot", response_model=OperatorFlowSnapshotResponse)
async def get_operator_snapshot(
    task_id: str,
    session: DBSession,
) -> OperatorFlowSnapshotResponse:
    try:
        return await operator_snapshot(session, task_id)
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        _raise_runtime_error(exc)


@router.get("/tasks/{task_id}/trace", response_model=OperatorFlowTraceResponse)
async def get_operator_trace(
    task_id: str,
    session: DBSession,
    *,
    scope: str = Query(default="current"),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    sort: str = Query(default="occurred_at_desc"),
) -> OperatorFlowTraceResponse:
    del cursor
    try:
        return await operator_trace(
            session,
            task_id,
            scope=scope,
            q=q,
            limit=limit,
            sort=sort,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        _raise_runtime_error(exc)
