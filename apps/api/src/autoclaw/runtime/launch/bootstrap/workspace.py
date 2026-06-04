from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.db.models import WorkspaceRootLeaseModel


async def acquire_workspace_root_lease(
    session: AsyncSession,
    *,
    task_id: str,
    flow_id: str,
    workspace_root_path: str,
    binding_mode: str,
) -> None:
    if not _workspace_binding_requires_lease(binding_mode):
        return

    normalized_path = await asyncio.to_thread(
        lambda: str(Path(workspace_root_path).expanduser().resolve())
    )
    existing_lease = await session.scalar(
        select(WorkspaceRootLeaseModel).where(
            WorkspaceRootLeaseModel.normalized_workspace_root_path == normalized_path
        )
    )
    if existing_lease is not None and existing_lease.lease_status == "live":
        raise ValueError(f"workspace host path already held by live task: {normalized_path}")
    if existing_lease is not None:
        existing_lease.task_id = task_id
        existing_lease.flow_id = flow_id
        existing_lease.lease_status = "live"
        existing_lease.leased_at = _now()
        existing_lease.released_at = None
        return

    session.add(
        WorkspaceRootLeaseModel(
            workspace_root_lease_id=_workspace_root_lease_id(task_id),
            normalized_workspace_root_path=normalized_path,
            task_id=task_id,
            flow_id=flow_id,
            lease_status="live",
        )
    )


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _workspace_binding_requires_lease(binding_mode: str) -> bool:
    return binding_mode != "ensure_task_default"


def _workspace_root_lease_id(task_id: str) -> str:
    return f"workspace-root-lease.{task_id}"
