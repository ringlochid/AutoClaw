from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchTurnModel
from app.runtime.contracts import (
    ManifestCurrentContextProjection,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    RuntimeContextRef,
    TaskRootPaths,
)
from app.runtime.projection.manifest.checkpoint_handoff import (
    checkpoint_attempt_id_from_path,
    dispatch_selected_checkpoint_path_at_cutoff,
    latest_checkpoint_for_attempt_before_cutoff,
    release_precondition_descendant_refs,
    stable_selected_checkpoint_path_for_attempt,
)
from app.runtime.projection.manifest.current_context_queries import (
    attempt_consumed_refs,
    ordinary_descendant_context_refs,
)
from app.runtime.projection.projection_mappers import assignment_projection_from_model
from app.runtime.projection.runtime_state import CurrentRuntimeState
from app.runtime.task_root import assignment_json_path, checkpoint_json_path

__all__ = [
    "build_manifest_current_context",
    "checkpoint_attempt_id_from_path",
    "latest_checkpoint_for_attempt_before_cutoff",
]

SELECTED_CHECKPOINT_DESCRIPTION = (
    "Controller-selected checkpoint surfaced for the current redispatch handoff."
)


async def build_manifest_current_context(
    session: AsyncSession,
    *,
    task_id: str,
    paths: TaskRootPaths,
    state: CurrentRuntimeState,
    current_relevant_cutoff: datetime | None,
    dispatch: DispatchTurnModel | None,
) -> ManifestCurrentContextProjection:
    assignment = assignment_projection_from_model(state.current_assignment)
    controller_refs = await attempt_consumed_refs(
        session,
        attempt_id=state.current_attempt.attempt_id,
    )
    descendant_refs = release_precondition_descendant_refs(dispatch)
    if descendant_refs is None:
        descendant_refs = await ordinary_descendant_context_refs(
            session,
            task_id=task_id,
            paths=paths,
            current_node=state.current_node,
            flow_revision_id=state.flow_revision.flow_revision_id,
            recorded_at_cutoff=current_relevant_cutoff,
        )
    current_relevant_paths: list[RuntimeContextRef] = [
        *controller_refs,
        *descendant_refs,
        *assignment.transient_refs,
    ]
    latest_checkpoint_path, latest_relevant_checkpoint_path = await _latest_checkpoint_paths(
        session,
        task_id=task_id,
        paths=paths,
        attempt_id=state.current_attempt.attempt_id,
        recorded_at_cutoff=current_relevant_cutoff,
        dispatch=dispatch,
    )
    _append_visible_checkpoint_refs(
        current_relevant_paths,
        latest_checkpoint_path=latest_checkpoint_path,
        latest_relevant_checkpoint_path=latest_relevant_checkpoint_path,
    )
    return ManifestCurrentContextProjection(
        current_node_key=state.current_node.node_key,
        owner_node_key=state.current_node.node_key,
        active_attempt_id=state.current_attempt.attempt_id,
        active_assignment_path=assignment_json_path(
            paths=paths,
            attempt_id=state.current_attempt.attempt_id,
        ).with_suffix(".md"),
        latest_checkpoint_path=latest_checkpoint_path,
        latest_relevant_checkpoint_path=latest_relevant_checkpoint_path,
        current_relevant_paths=tuple(current_relevant_paths),
    )


async def _latest_checkpoint_paths(
    session: AsyncSession,
    *,
    task_id: str,
    paths: TaskRootPaths,
    attempt_id: str,
    recorded_at_cutoff: datetime | None,
    dispatch: DispatchTurnModel | None,
) -> tuple[Path | None, Path | None]:
    latest_checkpoint = await latest_checkpoint_for_attempt_before_cutoff(
        session,
        attempt_id=attempt_id,
        recorded_at_cutoff=recorded_at_cutoff,
    )
    latest_checkpoint_path = (
        checkpoint_json_path(paths=paths, attempt_id=latest_checkpoint.attempt_id).with_suffix(
            ".md"
        )
        if latest_checkpoint is not None
        else None
    )
    latest_relevant_checkpoint_path = (
        await dispatch_selected_checkpoint_path_at_cutoff(
            session,
            dispatch=dispatch,
            paths=paths,
            recorded_at_cutoff=recorded_at_cutoff,
            latest_checkpoint_path=latest_checkpoint_path,
        )
        if dispatch is not None
        else await stable_selected_checkpoint_path_for_attempt(
            session,
            task_id=task_id,
            attempt_id=attempt_id,
            paths=paths,
            latest_checkpoint_path=latest_checkpoint_path,
        )
    )
    return latest_checkpoint_path, latest_relevant_checkpoint_path


def _append_visible_checkpoint_refs(
    current_relevant_paths: list[RuntimeContextRef],
    *,
    latest_checkpoint_path: Path | None,
    latest_relevant_checkpoint_path: Path | None,
) -> None:
    if latest_relevant_checkpoint_path is not None:
        _append_checkpoint_ref_if_missing(
            current_relevant_paths,
            path=latest_relevant_checkpoint_path,
            description=SELECTED_CHECKPOINT_DESCRIPTION,
        )
    if latest_checkpoint_path is not None:
        _append_checkpoint_ref_if_missing(
            current_relevant_paths,
            path=latest_checkpoint_path,
            description="Latest durable checkpoint for the current attempt.",
        )


def _append_checkpoint_ref_if_missing(
    current_relevant_paths: list[RuntimeContextRef],
    *,
    path: Path,
    description: str,
) -> None:
    for ref in current_relevant_paths:
        if (
            isinstance(ref, NodeRuntimeFileRef)
            and ref.kind == NodeRuntimeFileKind.CHECKPOINT
            and ref.path == path
        ):
            return
    current_relevant_paths.append(
        NodeRuntimeFileRef(
            kind=NodeRuntimeFileKind.CHECKPOINT,
            path=path,
            description=description,
        )
    )
