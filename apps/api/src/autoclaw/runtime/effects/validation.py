from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.db.models import ArtifactCurrentPointerModel, FlowNodeModel
from autoclaw.runtime.control.flow.queries import require_flow_for_task
from autoclaw.runtime.task_root import (
    checkpoint_json_path,
    checkpoint_markdown_path,
)
from autoclaw.runtime.task_root.reads import read_task_root_paths
from autoclaw.schemas.runtime.contracts import EvidenceKind


async def current_surfaced_ref_failure(
    session: AsyncSession,
    *,
    task_id: str,
    ref: dict[str, Any],
) -> str | None:
    if ref.get("kind") == EvidenceKind.CRITERIA.value:
        flow = await require_flow_for_task(session, task_id)
        if flow.active_flow_revision_id is None:
            return "current criteria ref is stale"
        nodes = await session.scalars(
            select(FlowNodeModel)
            .options(raiseload("*"))
            .where(FlowNodeModel.flow_revision_id == flow.active_flow_revision_id)
        )
        for node in nodes:
            for criteria in node.criteria_json:
                if str(criteria.get("slot")) == str(ref.get("slot")) and str(
                    criteria.get("path")
                ) == str(ref["path"]):
                    if _is_path_current(str(ref["path"])):
                        return None
                    return "current criteria file is missing"
        return "current criteria ref is stale"
    if ref.get("kind") != EvidenceKind.ARTIFACT.value:
        if _is_path_current(str(ref["path"])):
            return None
        if ref.get("kind") == "checkpoint":
            return "current checkpoint file is missing"
        return "current surfaced file is missing"
    pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.slot == ref.get("slot"),
            ArtifactCurrentPointerModel.current_path == str(ref["path"]),
            ArtifactCurrentPointerModel.current_version == ref.get("version"),
        )
    )
    if pointer is None:
        return "current artifact ref is stale"
    if _is_path_current(pointer.current_path):
        return None
    return "current artifact file is missing"


async def attempt_checkpoint_projection_failure(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> str | None:
    paths = await read_task_root_paths(session, task_id)
    checkpoint_json = checkpoint_json_path(paths=paths, attempt_id=attempt_id)
    checkpoint_markdown = checkpoint_markdown_path(paths=paths, attempt_id=attempt_id)
    if _is_path_current(checkpoint_json) and _is_path_current(checkpoint_markdown):
        return None
    return "current checkpoint projection files are missing"


def _is_path_current(path: str | Path) -> bool:
    return Path(path).expanduser().resolve().exists()


__all__ = [
    "attempt_checkpoint_projection_failure",
    "current_surfaced_ref_failure",
]
