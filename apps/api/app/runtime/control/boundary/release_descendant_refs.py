from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    AttemptModel,
    FlowNodeModel,
)
from app.runtime.contracts import EvidenceKind, EvidenceRef, NodeRuntimeFileKind, NodeRuntimeFileRef
from app.runtime.control.failures import illegal_state_error, missing_resource_error
from app.runtime.effects.validation import current_surfaced_ref_failure
from app.runtime.task_root import load_task_root_paths


async def release_turn_descendant_refs(
    session: AsyncSession,
    *,
    task_id: str,
    current_node: FlowNodeModel,
    flow_revision_id: str,
) -> list[dict[str, object]]:
    descendant_nodes = await _descendant_nodes(
        session,
        current_node=current_node,
        flow_revision_id=flow_revision_id,
    )
    if not descendant_nodes:
        return []

    descendant_refs: list[EvidenceRef | NodeRuntimeFileRef] = []
    descendant_refs.extend(
        await _descendant_checkpoint_refs(
            session,
            task_id=task_id,
            descendant_nodes=descendant_nodes,
        )
    )
    descendant_refs.extend(
        await _descendant_artifact_refs(
            session,
            task_id=task_id,
            descendant_nodes=descendant_nodes,
        )
    )
    return [ref.model_dump(mode="json") for ref in descendant_refs]


async def _descendant_nodes(
    session: AsyncSession,
    *,
    current_node: FlowNodeModel,
    flow_revision_id: str,
) -> list[FlowNodeModel]:
    descendants = list(
        await session.scalars(
            select(FlowNodeModel)
            .where(FlowNodeModel.flow_revision_id == flow_revision_id)
            .order_by(FlowNodeModel.order_index.asc(), FlowNodeModel.node_key.asc())
        )
    )
    children_by_parent_id: defaultdict[str, list[FlowNodeModel]] = defaultdict(list)
    for descendant in descendants:
        if descendant.parent_flow_node_id is not None:
            children_by_parent_id[descendant.parent_flow_node_id].append(descendant)

    descendant_nodes: list[FlowNodeModel] = []
    pending_parent_ids = [current_node.flow_node_id]
    while pending_parent_ids:
        parent_flow_node_id = pending_parent_ids.pop(0)
        for child in children_by_parent_id.get(parent_flow_node_id, ()):
            descendant_nodes.append(child)
            pending_parent_ids.append(child.flow_node_id)
    return descendant_nodes


async def _descendant_checkpoint_refs(
    session: AsyncSession,
    *,
    task_id: str,
    descendant_nodes: list[FlowNodeModel],
) -> list[NodeRuntimeFileRef]:
    paths = await load_task_root_paths(session, task_id)
    checkpoint_refs: list[NodeRuntimeFileRef] = []
    for descendant in descendant_nodes:
        checkpoint_ref = await _current_descendant_checkpoint_ref(
            session,
            task_id=task_id,
            descendant=descendant,
            attempts_path=paths.attempts_path,
        )
        if checkpoint_ref is not None:
            checkpoint_refs.append(checkpoint_ref)
    return checkpoint_refs


async def _current_descendant_checkpoint_ref(
    session: AsyncSession,
    *,
    task_id: str,
    descendant: FlowNodeModel,
    attempts_path: Path,
) -> NodeRuntimeFileRef | None:
    if descendant.current_assignment_id is None:
        return None
    assignment = await session.get(AssignmentModel, descendant.current_assignment_id)
    if assignment is None or assignment.current_attempt_id is None:
        raise illegal_state_error(
            f"descendant node '{descendant.node_key}' has no current assignment attempt"
        )
    attempt = await session.get(AttemptModel, assignment.current_attempt_id)
    if attempt is None:
        raise missing_resource_error(f"missing attempt '{assignment.current_attempt_id}'")
    if attempt.latest_checkpoint_id is None:
        return None

    checkpoint_ref = NodeRuntimeFileRef(
        kind=NodeRuntimeFileKind.CHECKPOINT,
        path=attempts_path / attempt.attempt_id / "latest-checkpoint.md",
        description=f"Latest checkpoint for descendant node '{descendant.node_key}'.",
    )
    failure = await current_surfaced_ref_failure(
        session,
        task_id=task_id,
        ref=checkpoint_ref.model_dump(mode="json"),
    )
    return None if failure is not None else checkpoint_ref


async def _descendant_artifact_refs(
    session: AsyncSession,
    *,
    task_id: str,
    descendant_nodes: list[FlowNodeModel],
) -> list[EvidenceRef]:
    descendant_refs: list[EvidenceRef] = []
    for pointer in await session.scalars(
        select(ArtifactCurrentPointerModel)
        .where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.owner_node_key.in_(
                tuple(descendant.node_key for descendant in descendant_nodes)
            ),
        )
        .order_by(
            ArtifactCurrentPointerModel.owner_node_key.asc(),
            ArtifactCurrentPointerModel.slot.asc(),
        )
    ):
        artifact_ref = EvidenceRef(
            kind=EvidenceKind.ARTIFACT,
            slot=pointer.slot,
            version=pointer.current_version,
            path=Path(pointer.current_path),
            description=pointer.description,
        )
        failure = await current_surfaced_ref_failure(
            session,
            task_id=task_id,
            ref=artifact_ref.model_dump(mode="json"),
        )
        if failure is None:
            descendant_refs.append(artifact_ref)
    return descendant_refs


__all__ = ["release_turn_descendant_refs"]
