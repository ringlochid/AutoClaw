from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.runtime.control.observability_support import (
    OBSERVABILITY_FILE_SPECS,
)
from autoclaw.runtime.control.observability_support import (
    observability_ref as _observability_ref,
)
from autoclaw.runtime.control.observability_support import (
    operator_snapshot as _operator_snapshot,
)
from autoclaw.runtime.control.observability_trace import operator_trace as _operator_trace
from autoclaw.schemas.runtime import (
    ObservabilityFileRef,
    OperatorFlowSnapshotResponse,
    OperatorFlowTraceResponse,
)


async def operator_snapshot(
    session: AsyncSession,
    task_id: str,
) -> OperatorFlowSnapshotResponse:
    return await _operator_snapshot(session, task_id)


async def operator_trace(
    session: AsyncSession,
    task_id: str,
    *,
    scope: str = "current",
    q: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    sort: str = "occurred_at_desc",
) -> OperatorFlowTraceResponse:
    return await _operator_trace(
        session,
        task_id,
        scope=scope,
        q=q,
        cursor=cursor,
        limit=limit,
        sort=sort,
    )


async def observability_ref(
    session: AsyncSession,
    task_id: str,
    filename: str,
    description: str,
) -> ObservabilityFileRef:
    return await _observability_ref(
        session,
        task_id,
        filename,
        description,
    )


__all__ = [
    "OBSERVABILITY_FILE_SPECS",
    "observability_ref",
    "operator_snapshot",
    "operator_trace",
]
