from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

import app.runtime.control.flow.mutations as flow_mutations
import app.runtime.control.flow.reads as flow_reads
from app.db.models import DispatchTurnModel
from app.schemas.runtime import (
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
)


async def runtime_flow_read(session: AsyncSession, task_id: str) -> RuntimeFlowRead:
    return await flow_reads.runtime_flow_read(session, task_id)


async def list_runtime_flows(
    session: AsyncSession,
    *,
    q: str | None = None,
    cursor: str | None = None,
    status: str = "any",
    limit: int = 50,
    sort: str = "updated_at_desc",
) -> RuntimeFlowSummaryListResponse:
    return await flow_reads.list_runtime_flows(
        session,
        q=q,
        cursor=cursor,
        status=status,
        limit=limit,
        sort=sort,
    )


async def latest_unreplaced_fenced_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
) -> DispatchTurnModel | None:
    return await flow_reads.latest_unreplaced_fenced_dispatch(session, task_id=task_id)


async def continue_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowRead:
    return await flow_mutations.continue_runtime_flow(
        session,
        task_id,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
    )


async def pause_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowPauseResponse:
    return await flow_mutations.pause_runtime_flow(
        session,
        task_id,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
    )


async def cancel_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowRead:
    return await flow_mutations.cancel_runtime_flow(
        session,
        task_id,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
    )


__all__ = [
    "cancel_runtime_flow",
    "continue_runtime_flow",
    "latest_unreplaced_fenced_dispatch",
    "list_runtime_flows",
    "pause_runtime_flow",
    "runtime_flow_read",
]
