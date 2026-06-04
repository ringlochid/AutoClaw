from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.api.deps import require_api_key
from autoclaw.api.errors import raise_runtime_exception
from autoclaw.db.session import get_db_session
from autoclaw.runtime.control.observability import operator_snapshot, operator_trace
from autoclaw.schemas.runtime import (
    OperatorFlowSnapshotResponse,
    OperatorFlowTraceQuery,
    OperatorFlowTraceResponse,
)

router = APIRouter(prefix="/operator", tags=["operator"], dependencies=[Depends(require_api_key)])
type DBSession = Annotated[AsyncSession, Depends(get_db_session)]
type OperatorTraceParams = Annotated[OperatorFlowTraceQuery, Query()]


@router.get("/tasks/{task_id}/snapshot", response_model=OperatorFlowSnapshotResponse)
async def get_operator_snapshot(
    task_id: str,
    session: DBSession,
) -> OperatorFlowSnapshotResponse:
    try:
        return await operator_snapshot(session, task_id)
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.get("/tasks/{task_id}/trace", response_model=OperatorFlowTraceResponse)
async def get_operator_trace(
    task_id: str,
    session: DBSession,
    query: OperatorTraceParams,
) -> OperatorFlowTraceResponse:
    try:
        return await operator_trace(
            session,
            task_id,
            scope=query.scope,
            q=query.q,
            cursor=query.cursor,
            limit=query.limit,
            sort=query.sort,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)
