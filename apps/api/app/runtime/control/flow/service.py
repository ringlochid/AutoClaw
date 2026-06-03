from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchTurnModel
from app.runtime.control.flow.mutations import (
    cancel_runtime_flow as _cancel_runtime_flow,
)
from app.runtime.control.flow.mutations import (
    continue_runtime_flow as _continue_runtime_flow,
)
from app.runtime.control.flow.mutations import (
    pause_runtime_flow as _pause_runtime_flow,
)
from app.runtime.control.flow.reads import (
    latest_unreplaced_fenced_dispatch as _latest_unreplaced_fenced_dispatch,
)
from app.runtime.control.flow.reads import (
    list_runtime_flows as _list_runtime_flows,
)
from app.runtime.control.flow.reads import (
    runtime_flow_read as _runtime_flow_read,
)
from app.schemas.runtime import (
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
)


async def runtime_flow_read(session: AsyncSession, task_id: str) -> RuntimeFlowRead:
    return await _runtime_flow_read(session, task_id)


async def list_runtime_flows(
    session: AsyncSession,
    *,
    q: str | None = None,
    cursor: str | None = None,
    status: str = "any",
    limit: int = 50,
    sort: str = "updated_at_desc",
) -> RuntimeFlowSummaryListResponse:
    return await _list_runtime_flows(
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
    return await _latest_unreplaced_fenced_dispatch(session, task_id=task_id)


async def continue_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowRead:
    return await _continue_runtime_flow(
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
    return await _pause_runtime_flow(
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
    return await _cancel_runtime_flow(
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
