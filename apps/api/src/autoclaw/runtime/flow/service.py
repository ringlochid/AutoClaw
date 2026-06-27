from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

import autoclaw.runtime.flow.mutations as flow_mutations
import autoclaw.runtime.flow.reads as flow_reads
from autoclaw.persistence.models import DispatchTurnModel
from autoclaw.runtime.contracts import (
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


async def latest_fenced_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
) -> DispatchTurnModel | None:
    return await flow_reads.latest_fenced_dispatch(session, task_id=task_id)


async def continue_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    actor_ref: str | None = None,
) -> RuntimeFlowRead:
    return await flow_mutations.continue_runtime_flow(
        session,
        task_id,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
        actor_ref=actor_ref,
    )


async def pause_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    actor_ref: str | None = None,
) -> RuntimeFlowPauseResponse:
    return await flow_mutations.pause_runtime_flow(
        session,
        task_id,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
        actor_ref=actor_ref,
    )


async def cancel_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
    actor_ref: str | None = None,
) -> RuntimeFlowRead:
    return await flow_mutations.cancel_runtime_flow(
        session,
        task_id,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
        actor_ref=actor_ref,
    )


__all__ = [
    "cancel_runtime_flow",
    "continue_runtime_flow",
    "latest_fenced_dispatch",
    "latest_unreplaced_fenced_dispatch",
    "list_runtime_flows",
    "pause_runtime_flow",
    "runtime_flow_read",
]
