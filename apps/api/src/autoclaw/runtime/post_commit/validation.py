from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import ArtifactCurrentPointerModel, FlowNodeModel
from autoclaw.runtime.contracts import EvidenceKind
from autoclaw.runtime.flow.queries import require_flow_for_task
from autoclaw.runtime.task_root import (
    checkpoint_json_path,
    checkpoint_markdown_path,
)
from autoclaw.runtime.task_root.reads import read_task_root_paths


@dataclass(frozen=True)
class SurfacedRefFailure:
    summary: str
    reason: str
    slot: str | None = None
    path: str | None = None
    version: int | None = None
    current_owner_node_key: str | None = None
    current_assignment_key: str | None = None
    current_path: str | None = None
    current_version: int | None = None


async def current_surfaced_ref_failure(
    session: AsyncSession,
    *,
    task_id: str,
    ref: dict[str, Any],
) -> str | None:
    detail = await current_surfaced_ref_detail(session, task_id=task_id, ref=ref)
    if detail is None:
        return None
    return detail.summary


async def current_surfaced_ref_detail(
    session: AsyncSession,
    *,
    task_id: str,
    ref: dict[str, Any],
) -> SurfacedRefFailure | None:
    if ref.get("kind") == EvidenceKind.CRITERIA.value:
        return await _criteria_surfaced_ref_detail(session, task_id=task_id, ref=ref)
    if ref.get("kind") != EvidenceKind.ARTIFACT.value:
        return _non_artifact_surfaced_ref_detail(ref)
    return await _artifact_surfaced_ref_detail(session, task_id=task_id, ref=ref)


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


async def _criteria_surfaced_ref_detail(
    session: AsyncSession,
    *,
    task_id: str,
    ref: dict[str, Any],
) -> SurfacedRefFailure | None:
    flow = await require_flow_for_task(session, task_id)
    if flow.active_flow_revision_id is None:
        return SurfacedRefFailure(
            summary=f"criteria slot '{ref.get('slot')}' is stale for the current flow revision",
            reason="criteria_ref_stale",
            slot=_as_optional_str(ref.get("slot")),
            path=_as_optional_str(ref.get("path")),
        )
    nodes = await session.scalars(
        select(FlowNodeModel)
        .options(raiseload("*"))
        .where(FlowNodeModel.flow_revision_id == flow.active_flow_revision_id)
    )
    if await _criteria_ref_matches_current_node(nodes, ref):
        if _is_path_current(str(ref["path"])):
            return None
        return SurfacedRefFailure(
            summary=f"criteria slot '{ref.get('slot')}' file is missing at '{ref['path']}'",
            reason="criteria_file_missing",
            slot=_as_optional_str(ref.get("slot")),
            path=_as_optional_str(ref.get("path")),
        )
    return SurfacedRefFailure(
        summary=(
            f"criteria slot '{ref.get('slot')}' at '{ref.get('path')}' is stale for "
            "the current flow revision"
        ),
        reason="criteria_ref_stale",
        slot=_as_optional_str(ref.get("slot")),
        path=_as_optional_str(ref.get("path")),
    )


async def _criteria_ref_matches_current_node(
    nodes: Any,
    ref: dict[str, Any],
) -> bool:
    for node in nodes:
        for criteria in node.criteria_json:
            if str(criteria.get("slot")) == str(ref.get("slot")) and str(
                criteria.get("path")
            ) == str(ref["path"]):
                return True
    return False


def _non_artifact_surfaced_ref_detail(
    ref: dict[str, Any],
) -> SurfacedRefFailure | None:
    if _is_path_current(str(ref["path"])):
        return None
    if ref.get("kind") == "checkpoint":
        return SurfacedRefFailure(
            summary=f"checkpoint file is missing at '{ref['path']}'",
            reason="checkpoint_file_missing",
            path=_as_optional_str(ref.get("path")),
        )
    return SurfacedRefFailure(
        summary=f"surfaced file is missing at '{ref['path']}'",
        reason="surfaced_file_missing",
        path=_as_optional_str(ref.get("path")),
    )


async def _artifact_surfaced_ref_detail(
    session: AsyncSession,
    *,
    task_id: str,
    ref: dict[str, Any],
) -> SurfacedRefFailure | None:
    pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.slot == ref.get("slot"),
            ArtifactCurrentPointerModel.current_path == str(ref["path"]),
            ArtifactCurrentPointerModel.current_version == ref.get("version"),
        )
    )
    if pointer is None:
        return await _stale_artifact_ref_detail(session, task_id=task_id, ref=ref)
    if _is_path_current(pointer.current_path):
        return None
    return SurfacedRefFailure(
        summary=(
            f"current artifact file for slot '{pointer.slot}' is missing at "
            f"'{pointer.current_path}'"
        ),
        reason="artifact_file_missing",
        slot=pointer.slot,
        path=pointer.current_path,
        version=pointer.current_version,
        current_owner_node_key=pointer.owner_node_key,
        current_assignment_key=pointer.assignment_key,
        current_path=pointer.current_path,
        current_version=pointer.current_version,
    )


async def _stale_artifact_ref_detail(
    session: AsyncSession,
    *,
    task_id: str,
    ref: dict[str, Any],
) -> SurfacedRefFailure:
    current_pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.slot == ref.get("slot"),
        )
    )
    if current_pointer is None:
        return SurfacedRefFailure(
            summary=(
                f"artifact slot '{ref.get('slot')}' ref at '{ref.get('path')}' "
                f"(v{ref.get('version')}) is stale because no current pointer exists "
                "for that slot"
            ),
            reason="artifact_ref_stale",
            slot=_as_optional_str(ref.get("slot")),
            path=_as_optional_str(ref.get("path")),
            version=_as_optional_int(ref.get("version")),
        )
    return SurfacedRefFailure(
        summary=(
            f"artifact slot '{ref.get('slot')}' ref at '{ref.get('path')}' "
            f"(v{ref.get('version')}) is stale; current pointer is "
            f"'{current_pointer.current_path}' (v{current_pointer.current_version}) "
            f"from node '{current_pointer.owner_node_key}'"
        ),
        reason="artifact_ref_stale",
        slot=_as_optional_str(ref.get("slot")),
        path=_as_optional_str(ref.get("path")),
        version=_as_optional_int(ref.get("version")),
        current_owner_node_key=current_pointer.owner_node_key,
        current_assignment_key=current_pointer.assignment_key,
        current_path=current_pointer.current_path,
        current_version=current_pointer.current_version,
    )


def _is_path_current(path: str | Path) -> bool:
    return Path(path).expanduser().resolve().exists()


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "SurfacedRefFailure",
    "attempt_checkpoint_projection_failure",
    "current_surfaced_ref_detail",
    "current_surfaced_ref_failure",
]
