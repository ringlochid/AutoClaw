from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.runtime.control import (
    cancel_runtime_flow,
    continue_runtime_flow,
    list_runtime_flows,
    pause_runtime_flow,
    runtime_flow_read,
)
from app.schemas.runtime import (
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
)

router = APIRouter(prefix="/runtime", tags=["runtime"])
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


@router.get("/tasks", response_model=RuntimeFlowSummaryListResponse)
async def get_runtime_tasks(
    session: DBSession,
    *,
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    sort: str = Query(default="updated_at_desc"),
    status_filter: str = Query(default="any", alias="status"),
) -> RuntimeFlowSummaryListResponse:
    del cursor
    try:
        return await list_runtime_flows(
            session,
            q=q,
            limit=limit,
            sort=sort,
            status=status_filter,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        _raise_runtime_error(exc)


@router.get("/tasks/{task_id}", response_model=RuntimeFlowRead)
async def get_runtime_task(
    task_id: str,
    session: DBSession,
) -> RuntimeFlowRead:
    try:
        return await runtime_flow_read(session, task_id)
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        _raise_runtime_error(exc)


@router.post("/tasks/{task_id}/continue", response_model=RuntimeFlowRead)
async def continue_task(
    task_id: str,
    session: DBSession,
    *,
    expected_active_flow_revision_id: str = Query(...),
) -> RuntimeFlowRead:
    try:
        flow = await continue_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=expected_active_flow_revision_id,
        )
        await session.commit()
        return flow
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await session.rollback()
        _raise_runtime_error(exc)


@router.post("/tasks/{task_id}/pause", response_model=RuntimeFlowPauseResponse)
async def pause_task(
    task_id: str,
    session: DBSession,
    *,
    expected_active_flow_revision_id: str = Query(...),
) -> RuntimeFlowPauseResponse:
    try:
        flow = await pause_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=expected_active_flow_revision_id,
        )
        await session.commit()
        return flow
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await session.rollback()
        _raise_runtime_error(exc)


@router.post("/tasks/{task_id}/cancel", response_model=RuntimeFlowRead)
async def cancel_task(
    task_id: str,
    session: DBSession,
    *,
    expected_active_flow_revision_id: str = Query(...),
) -> RuntimeFlowRead:
    try:
        flow = await cancel_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=expected_active_flow_revision_id,
        )
        await session.commit()
        return flow
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await session.rollback()
        _raise_runtime_error(exc)
