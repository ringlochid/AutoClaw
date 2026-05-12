from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ArtifactCurrentPointerModel, FlowNodeModel
from app.runtime.contracts import EvidenceKind
from app.runtime.control.flow_queries import require_flow_for_task
from app.runtime.post_commit import has_pending_runtime_effect, queue_post_commit_action
from app.runtime.projection import load_task_root_paths
from app.runtime.resources import checkpoint_json_path, checkpoint_markdown_path


def coerce_source_path(path: Path) -> Path:
    return path.expanduser().resolve()


def is_path_current(path: str | Path) -> bool:
    return Path(path).expanduser().resolve().exists()


def file_copy_effect_key(destination: Path) -> tuple[str, ...]:
    return ("copy-file", str(destination))


def attempt_materialization_effect_key(task_id: str, attempt_id: str) -> tuple[str, ...]:
    return ("materialize-attempt", task_id, attempt_id)


def manifest_materialization_effect_key(task_id: str) -> tuple[str, ...]:
    return ("materialize-manifest", task_id)


def dispatch_materialization_effect_key(task_id: str, dispatch_id: str) -> tuple[str, ...]:
    return ("materialize-dispatch", task_id, dispatch_id)


def artifact_current_pointer_effect_key(
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> tuple[str, ...]:
    return ("materialize-artifact-current", task_id, owner_node_key, slot)


def queue_file_copy(
    session: AsyncSession,
    *,
    source_path: Path,
    destination: Path,
) -> None:
    queue_post_commit_action(
        session,
        key=file_copy_effect_key(destination),
        task_id=None,
        effect_kind="file_copy",
        payload={
            "source_path": str(coerce_source_path(source_path)),
            "destination_path": str(destination),
        },
    )


def queue_attempt_materialization(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> None:
    queue_post_commit_action(
        session,
        key=attempt_materialization_effect_key(task_id, attempt_id),
        task_id=task_id,
        effect_kind="attempt_materialization",
        payload={"task_id": task_id, "attempt_id": attempt_id},
    )


def queue_manifest_materialization(session: AsyncSession, *, task_id: str) -> None:
    queue_post_commit_action(
        session,
        key=manifest_materialization_effect_key(task_id),
        task_id=task_id,
        effect_kind="manifest_materialization",
        payload={"task_id": task_id},
    )


def queue_dispatch_materialization(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    queue_post_commit_action(
        session,
        key=dispatch_materialization_effect_key(task_id, dispatch_id),
        task_id=task_id,
        effect_kind="dispatch_materialization",
        payload={"task_id": task_id, "dispatch_id": dispatch_id},
    )


def queue_artifact_current_pointer_materialization(
    session: AsyncSession,
    *,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> None:
    queue_post_commit_action(
        session,
        key=artifact_current_pointer_effect_key(task_id, owner_node_key, slot),
        task_id=task_id,
        effect_kind="artifact_current_pointer_materialization",
        payload={
            "task_id": task_id,
            "owner_node_key": owner_node_key,
            "slot": slot,
        },
    )


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
