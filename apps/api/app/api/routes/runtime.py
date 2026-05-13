from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_key
from app.api.errors import raise_runtime_exception
from app.db.session import get_db_session
from app.runtime.control.flow.service import (
    cancel_runtime_flow,
    continue_runtime_flow,
    list_runtime_flows,
    pause_runtime_flow,
    runtime_flow_read,
)
from app.runtime.effects import commit_runtime_session, rollback_runtime_session
from app.schemas.runtime import (
    RuntimeFlowControlQuery,
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
    RuntimeTaskListQuery,
)

router = APIRouter(prefix="/runtime", tags=["runtime"], dependencies=[Depends(require_api_key)])
type DBSession = Annotated[AsyncSession, Depends(get_db_session)]
type RuntimeTaskListParams = Annotated[RuntimeTaskListQuery, Query()]
type RuntimeFlowControlParams = Annotated[RuntimeFlowControlQuery, Query()]


@router.get("/tasks", response_model=RuntimeFlowSummaryListResponse)
async def get_runtime_tasks(
    session: DBSession,
    query: RuntimeTaskListParams,
) -> RuntimeFlowSummaryListResponse:
    try:
        return await list_runtime_flows(
            session,
            q=query.q,
            cursor=query.cursor,
            limit=query.limit,
            sort=query.sort,
            status=query.status,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.get("/tasks/{task_id}", response_model=RuntimeFlowRead)
async def get_runtime_task(
    task_id: str,
    session: DBSession,
) -> RuntimeFlowRead:
    try:
        return await runtime_flow_read(session, task_id)
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post("/tasks/{task_id}/continue", response_model=RuntimeFlowRead)
async def continue_task(
    task_id: str,
    session: DBSession,
    query: RuntimeFlowControlParams,
) -> RuntimeFlowRead:
    try:
        flow = await continue_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=query.expected_active_flow_revision_id,
        )
        await commit_runtime_session(session)
        return flow
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await rollback_runtime_session(session)
        raise_runtime_exception(exc)


@router.post("/tasks/{task_id}/pause", response_model=RuntimeFlowPauseResponse)
async def pause_task(
    task_id: str,
    session: DBSession,
    query: RuntimeFlowControlParams,
) -> RuntimeFlowPauseResponse:
    try:
        flow = await pause_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=query.expected_active_flow_revision_id,
        )
        await commit_runtime_session(session)
        return flow
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await rollback_runtime_session(session)
        raise_runtime_exception(exc)


@router.post("/tasks/{task_id}/cancel", response_model=RuntimeFlowRead)
async def cancel_task(
    task_id: str,
    session: DBSession,
    query: RuntimeFlowControlParams,
) -> RuntimeFlowRead:
    try:
        flow = await cancel_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=query.expected_active_flow_revision_id,
        )
        await commit_runtime_session(session)
        return flow
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        await rollback_runtime_session(session)
        raise_runtime_exception(exc)
