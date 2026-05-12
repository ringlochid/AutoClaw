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
from app.runtime.effects.validation import is_path_current
from app.runtime.projection import load_task_root_paths


async def parent_node_from_relation(
    session: AsyncSession,
    *,
    node: FlowNodeModel,
) -> FlowNodeModel | None:
    if node.parent_flow_node_id is None:
        if node.parent_node_key is not None:
            raise ValueError(
                "runtime node mirror parent_node_key exists without relational parent_flow_node_id"
            )
        return None
    parent = await session.get(FlowNodeModel, node.parent_flow_node_id)
    if parent is None:
        raise ValueError(
            "missing relational parent flow node "
            f"'{node.parent_flow_node_id}' for node '{node.node_key}'"
        )
    return parent


async def release_turn_descendant_refs(
    session: AsyncSession,
    *,
    task_id: str,
    current_node: FlowNodeModel,
    flow_revision_id: str,
) -> list[dict[str, object]]:
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

    if not descendant_nodes:
        return []

    paths = await load_task_root_paths(session, task_id)
    descendant_refs: list[EvidenceRef | NodeRuntimeFileRef] = []
    for descendant in descendant_nodes:
        if descendant.current_assignment_id is None:
            continue
        assignment = await session.get(AssignmentModel, descendant.current_assignment_id)
        if assignment is None or assignment.current_attempt_id is None:
            raise ValueError(
                f"descendant node '{descendant.node_key}' has no current assignment attempt"
            )
        attempt = await session.get(AttemptModel, assignment.current_attempt_id)
        if attempt is None:
            raise ValueError(f"missing attempt '{assignment.current_attempt_id}'")
        checkpoint_path = paths.attempts_path / attempt.attempt_id / "latest-checkpoint.md"
        if attempt.latest_checkpoint_id is not None and is_path_current(checkpoint_path):
            descendant_refs.append(
                NodeRuntimeFileRef(
                    kind=NodeRuntimeFileKind.CHECKPOINT,
                    path=checkpoint_path,
                    description=f"Latest checkpoint for descendant node '{descendant.node_key}'.",
                )
            )

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
        if not is_path_current(pointer.current_path):
            continue
        descendant_refs.append(
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot=pointer.slot,
                version=pointer.current_version,
                path=Path(pointer.current_path),
                description=pointer.description,
            )
        )

    return [ref.model_dump(mode="json") for ref in descendant_refs]


__all__ = ["parent_node_from_relation", "release_turn_descendant_refs"]
