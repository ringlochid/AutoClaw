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
from app.runtime.projection.checkpoint_handoff import (
    checkpoint_attempt_id_from_path,
    controller_selected_checkpoint_path,
    dispatch_selected_checkpoint_path_at_cutoff,
    latest_checkpoint_for_attempt_before_cutoff,
    release_precondition_descendant_refs,
)
from app.runtime.projection.current_context_queries import (
    attempt_consumed_refs,
    ordinary_descendant_context_refs,
)
from app.runtime.projection.projection_mappers import assignment_projection_from_model
from app.runtime.projection.runtime_state import CurrentRuntimeState
from app.runtime.resources import assignment_json_path, checkpoint_json_path

__all__ = [
    "build_manifest_current_context",
    "checkpoint_attempt_id_from_path",
    "latest_checkpoint_for_attempt_before_cutoff",
]


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
    latest_checkpoint_path: Path | None = None
    latest_checkpoint = await latest_checkpoint_for_attempt_before_cutoff(
        session,
        attempt_id=state.current_attempt.attempt_id,
        recorded_at_cutoff=current_relevant_cutoff,
    )
    if latest_checkpoint is not None:
        latest_checkpoint_path = checkpoint_json_path(
            paths=paths,
            attempt_id=latest_checkpoint.attempt_id,
        ).with_suffix(".md")
        current_relevant_paths.append(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=latest_checkpoint_path,
                description="Latest durable checkpoint for the current attempt.",
            )
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
        latest_relevant_checkpoint_path=(
            await dispatch_selected_checkpoint_path_at_cutoff(
                session,
                dispatch=dispatch,
                paths=paths,
                recorded_at_cutoff=current_relevant_cutoff,
                latest_checkpoint_path=latest_checkpoint_path,
            )
            if dispatch is not None
            else controller_selected_checkpoint_path(
                controller_refs=controller_refs,
                latest_checkpoint_path=latest_checkpoint_path,
            )
        ),
        current_relevant_paths=tuple(current_relevant_paths),
    )
