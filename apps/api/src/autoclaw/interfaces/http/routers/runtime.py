from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.interfaces.http.dependencies import (
    read_control_actor_ref,
    require_api_key,
)
from autoclaw.interfaces.http.errors import raise_runtime_exception
from autoclaw.persistence.session import get_db_session
from autoclaw.runtime.contracts import (
    RuntimeFlowControlQuery,
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
    RuntimeTaskListQuery,
)
from autoclaw.runtime.flow.service import (
    cancel_runtime_flow,
    continue_runtime_flow,
    list_runtime_flows,
    pause_runtime_flow,
    runtime_flow_read,
)
from autoclaw.runtime.post_commit.operations import write_runtime_operation

router = APIRouter(prefix="/runtime", tags=["runtime"], dependencies=[Depends(require_api_key)])
type DBSession = Annotated[AsyncSession, Depends(get_db_session)]
type ControlActorRefDep = Annotated[str | None, Depends(read_control_actor_ref)]
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
    actor_ref: ControlActorRefDep,
) -> RuntimeFlowRead:
    try:
        return await write_runtime_operation(
            lambda active_session: continue_runtime_flow(
                active_session,
                task_id,
                expected_active_flow_revision_id=query.expected_active_flow_revision_id,
                actor_ref=actor_ref,
            ),
            session=session,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post("/tasks/{task_id}/pause", response_model=RuntimeFlowPauseResponse)
async def pause_task(
    task_id: str,
    session: DBSession,
    query: RuntimeFlowControlParams,
    actor_ref: ControlActorRefDep,
) -> RuntimeFlowPauseResponse:
    try:
        return await write_runtime_operation(
            lambda active_session: pause_runtime_flow(
                active_session,
                task_id,
                expected_active_flow_revision_id=query.expected_active_flow_revision_id,
                actor_ref=actor_ref,
            ),
            session=session,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)


@router.post("/tasks/{task_id}/cancel", response_model=RuntimeFlowRead)
async def cancel_task(
    task_id: str,
    session: DBSession,
    query: RuntimeFlowControlParams,
    actor_ref: ControlActorRefDep,
) -> RuntimeFlowRead:
    try:
        return await write_runtime_operation(
            lambda active_session: cancel_runtime_flow(
                active_session,
                task_id,
                expected_active_flow_revision_id=query.expected_active_flow_revision_id,
                actor_ref=actor_ref,
            ),
            session=session,
        )
    except Exception as exc:  # pragma: no cover - thin HTTP wrapper
        raise_runtime_exception(exc)
