from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ArtifactCurrentPointerModel, FlowNodeModel
from app.runtime.contracts import EvidenceKind
from app.runtime.control.flow.queries import require_flow_for_task
from app.runtime.effects.keys import (
    artifact_current_pointer_effect_key,
    attempt_materialization_effect_key,
    file_copy_effect_key,
    manifest_materialization_effect_key,
)
from app.runtime.effects.queue import has_pending_runtime_effect
from app.runtime.projection import load_task_root_paths
from app.runtime.task_root import checkpoint_json_path, checkpoint_markdown_path


def is_path_current(path: str | Path) -> bool:
    return Path(path).expanduser().resolve().exists()


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
            select(FlowNodeModel).where(
                FlowNodeModel.flow_revision_id == flow.active_flow_revision_id
            )
        )
        for node in nodes:
            for criteria in node.criteria_json:
                if str(criteria.get("slot")) == str(ref.get("slot")) and str(
                    criteria.get("path")
                ) == str(ref["path"]):
                    if is_path_current(str(ref["path"])):
                        return None
                    if await has_pending_runtime_effect(
                        session,
                        key=manifest_materialization_effect_key(task_id),
                    ):
                        return None
                    return "current criteria file is missing"
        return "current criteria ref is stale"
    if ref.get("kind") != EvidenceKind.ARTIFACT.value:
        if is_path_current(str(ref["path"])):
            return None
        if ref.get("kind") == "checkpoint":
            attempt_id = Path(str(ref["path"])).parent.name
            if await has_pending_runtime_effect(
                session,
                key=attempt_materialization_effect_key(task_id, attempt_id),
            ):
                return None
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
    if is_path_current(pointer.current_path):
        return None
    if await has_pending_runtime_effect(
        session,
        key=file_copy_effect_key(Path(pointer.current_path)),
    ) or await has_pending_runtime_effect(
        session,
        key=artifact_current_pointer_effect_key(task_id, pointer.owner_node_key, pointer.slot),
    ):
        return None
    return "current artifact file is missing"


async def attempt_checkpoint_projection_failure(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> str | None:
    paths = await load_task_root_paths(session, task_id)
    checkpoint_json = checkpoint_json_path(paths=paths, attempt_id=attempt_id)
    checkpoint_markdown = checkpoint_markdown_path(paths=paths, attempt_id=attempt_id)
    if is_path_current(checkpoint_json) and is_path_current(checkpoint_markdown):
        return None
    if await has_pending_runtime_effect(
        session,
        key=attempt_materialization_effect_key(task_id, attempt_id),
    ):
        return None
    return "current checkpoint projection files are missing"


__all__ = [
    "attempt_checkpoint_projection_failure",
    "current_surfaced_ref_failure",
    "is_path_current",
]
