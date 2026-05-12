from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ArtifactCurrentPointerModel, FlowNodeModel
from app.runtime.contracts import ManifestProjection
from app.runtime.projection.manifest.projection import build_manifest_projection
from app.runtime.projection.projection_mappers import criteria_markdown, int_or_none
from app.runtime.projection.runtime_state import current_runtime_state
from app.runtime.task_root import (
    artifact_current_json_path,
    criteria_file_path,
    load_task_root_paths,
    write_json_file,
    write_manifest_projection,
)


async def materialize_manifest(session: AsyncSession, task_id: str) -> ManifestProjection:
    paths = await load_task_root_paths(session, task_id)
    state = await current_runtime_state(session, task_id)
    nodes = await session.scalars(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == state.flow_revision.flow_revision_id
        )
    )
    for node in nodes:
        for criteria in node.criteria_json:
            version = int_or_none(criteria.get("version"))
            criteria_path = (
                Path(str(criteria["path"]))
                if criteria.get("path") is not None
                else criteria_file_path(paths=paths, slot=str(criteria["slot"]), version=version)
            )
            criteria_path.parent.mkdir(parents=True, exist_ok=True)
            markdown = criteria_markdown(criteria)
            criteria_path.write_text(markdown, encoding="utf-8")
            compatibility_path = criteria_file_path(paths=paths, slot=str(criteria["slot"]))
            compatibility_path.write_text(markdown, encoding="utf-8")
    manifest = await build_manifest_projection(session, task_id)
    write_manifest_projection(paths=paths, manifest=manifest)
    return manifest


async def materialize_artifact_current_pointer(
    session: AsyncSession,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> None:
    pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.owner_node_key == owner_node_key,
            ArtifactCurrentPointerModel.slot == slot,
        )
    )
    if pointer is None:
        return
    paths = await load_task_root_paths(session, task_id)
    write_json_file(
        artifact_current_json_path(paths=paths, owner_node_key=owner_node_key, slot=slot),
        {
            "owner_node_key": pointer.owner_node_key,
            "slot": pointer.slot,
            "current_version": pointer.current_version,
            "current_path": pointer.current_path,
            "description": pointer.description,
            "assignment_key": pointer.assignment_key,
            "attempt_id": pointer.attempt_id,
            "published_at": pointer.published_at.isoformat(),
            "supersedes_path": pointer.supersedes_path,
        },
    )
