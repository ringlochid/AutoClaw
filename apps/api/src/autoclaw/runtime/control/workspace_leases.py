from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.db.models import WorkspaceRootLeaseModel
from autoclaw.runtime.control.clock import utc_now


async def release_workspace_root_lease(
    session: AsyncSession,
    *,
    task_id: str,
) -> None:
    lease = await session.scalar(
        select(WorkspaceRootLeaseModel).where(
            WorkspaceRootLeaseModel.task_id == task_id,
            WorkspaceRootLeaseModel.lease_status == "live",
        )
    )
    if lease is None:
        return
    lease.lease_status = "released"
    lease.released_at = utc_now()
    await session.flush()
