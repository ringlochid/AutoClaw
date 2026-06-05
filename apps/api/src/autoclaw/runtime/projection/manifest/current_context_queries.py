from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import (
    ArtifactCurrentPointerModel,
    ArtifactPublicationModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptConsumedRefModel,
    AttemptModel,
    DispatchTurnModel,
    FlowNodeModel,
)
from autoclaw.runtime.contracts import (
    EvidenceKind,
    EvidenceRef,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    RuntimeContextRef,
    TaskRootPaths,
)
from autoclaw.runtime.projection.projection_mappers import (
    runtime_context_ref_from_attempt_consumed_model,
)
from autoclaw.runtime.task_root import checkpoint_json_path


async def attempt_consumed_refs(
    session: AsyncSession,
    *,
    attempt_id: str,
) -> tuple[RuntimeContextRef, ...]:
    attempt_rows = list(
        await session.scalars(
            select(AttemptConsumedRefModel)
            .options(raiseload("*"))
            .where(AttemptConsumedRefModel.attempt_id == attempt_id)
            .order_by(AttemptConsumedRefModel.order_index.asc())
        )
    )
    return tuple(runtime_context_ref_from_attempt_consumed_model(model) for model in attempt_rows)


async def latest_dispatch_selected_checkpoint_attempt_id(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> str | None:
    dispatch = await session.scalar(
        select(DispatchTurnModel)
        .options(raiseload("*"))
        .where(
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.attempt_id == attempt_id,
        )
        .order_by(DispatchTurnModel.rendered_at.desc())
    )
    if dispatch is None:
        return None
    return dispatch.relevant_checkpoint_attempt_id


async def ordinary_descendant_context_refs(
    session: AsyncSession,
    *,
    task_id: str,
    paths: TaskRootPaths,
    current_node: FlowNodeModel,
    flow_revision_id: str,
    recorded_at_cutoff: datetime | None,
) -> tuple[RuntimeContextRef, ...]:
    return (
        *(
            await _current_child_artifact_refs(
                session,
                task_id=task_id,
                current_node=current_node,
                flow_revision_id=flow_revision_id,
                recorded_at_cutoff=recorded_at_cutoff,
            )
        ),
        *(
            await _child_checkpoint_refs(
                session,
                task_id,
                paths,
                current_node,
                flow_revision_id,
                recorded_at_cutoff,
            )
        ),
    )


async def _direct_child_nodes(
    session: AsyncSession,
    *,
    current_node: FlowNodeModel,
    flow_revision_id: str,
) -> list[FlowNodeModel]:
    return list(
        await session.scalars(
            select(FlowNodeModel)
            .options(raiseload("*"))
            .where(
                FlowNodeModel.flow_revision_id == flow_revision_id,
                FlowNodeModel.parent_flow_node_id == current_node.flow_node_id,
            )
            .order_by(FlowNodeModel.order_index.asc())
        )
    )


async def _current_child_checkpoint_attempt_ids(
    session: AsyncSession,
    *,
    current_node: FlowNodeModel,
    flow_revision_id: str,
) -> dict[str, str]:
    rows = cast(
        list[tuple[FlowNodeModel, AssignmentModel | None, AttemptModel | None]],
        (
            await session.execute(
                select(FlowNodeModel, AssignmentModel, AttemptModel)
                .options(raiseload("*"))
                .outerjoin(
                    AssignmentModel,
                    AssignmentModel.assignment_id == FlowNodeModel.current_assignment_id,
                )
                .outerjoin(
                    AttemptModel,
                    AttemptModel.attempt_id == AssignmentModel.current_attempt_id,
                )
                .where(
                    FlowNodeModel.flow_revision_id == flow_revision_id,
                    FlowNodeModel.parent_flow_node_id == current_node.flow_node_id,
                )
                .order_by(FlowNodeModel.order_index.asc())
            )
        ).all(),
    )
    return {
        child.node_key: attempt.attempt_id
        for child, _, attempt in rows
        if attempt is not None and attempt.latest_checkpoint_id is not None
    }


async def _historical_child_checkpoint_attempt_ids(
    session: AsyncSession,
    *,
    task_id: str,
    child_node_keys: list[str],
    recorded_at_cutoff: datetime,
) -> dict[str, str]:
    child_attempt_ids: dict[str, str] = {}
    for node_key, checkpoint_attempt_id in cast(
        list[tuple[str, str]],
        (
            await session.execute(
                select(AttemptModel.node_key, AttemptCheckpointModel.attempt_id)
                .join(
                    AttemptModel,
                    AttemptModel.attempt_id == AttemptCheckpointModel.attempt_id,
                )
                .where(
                    AttemptModel.task_id == task_id,
                    AttemptModel.node_key.in_(child_node_keys),
                    AttemptCheckpointModel.recorded_at <= recorded_at_cutoff,
                )
                .order_by(
                    AttemptModel.node_key.asc(),
                    AttemptCheckpointModel.recorded_at.desc(),
                    AttemptCheckpointModel.checkpoint_id.desc(),
                )
            )
        ).all(),
    ):
        child_attempt_ids.setdefault(node_key, checkpoint_attempt_id)
    return child_attempt_ids


async def _child_checkpoint_attempt_ids(
    session: AsyncSession,
    *,
    task_id: str,
    current_node: FlowNodeModel,
    flow_revision_id: str,
    recorded_at_cutoff: datetime | None,
) -> tuple[list[FlowNodeModel], dict[str, str]]:
    children = await _direct_child_nodes(
        session,
        current_node=current_node,
        flow_revision_id=flow_revision_id,
    )
    if not children:
        return [], {}
    if recorded_at_cutoff is None:
        return children, await _current_child_checkpoint_attempt_ids(
            session,
            current_node=current_node,
            flow_revision_id=flow_revision_id,
        )
    return children, await _historical_child_checkpoint_attempt_ids(
        session,
        task_id=task_id,
        child_node_keys=[child.node_key for child in children],
        recorded_at_cutoff=recorded_at_cutoff,
    )


def _checkpoint_ref_for_attempt_id(
    *,
    paths: TaskRootPaths,
    child_node_key: str,
    attempt_id: str,
) -> NodeRuntimeFileRef:
    return NodeRuntimeFileRef(
        kind=NodeRuntimeFileKind.CHECKPOINT,
        path=checkpoint_json_path(
            paths=paths,
            attempt_id=attempt_id,
        ).with_suffix(".md"),
        description=f"Latest checkpoint for direct child node '{child_node_key}'.",
    )


async def _child_checkpoint_refs(
    session: AsyncSession,
    task_id: str,
    paths: TaskRootPaths,
    current_node: FlowNodeModel,
    flow_revision_id: str,
    recorded_at_cutoff: datetime | None = None,
) -> tuple[NodeRuntimeFileRef, ...]:
    children, child_attempt_ids = await _child_checkpoint_attempt_ids(
        session,
        task_id=task_id,
        current_node=current_node,
        flow_revision_id=flow_revision_id,
        recorded_at_cutoff=recorded_at_cutoff,
    )
    refs: list[NodeRuntimeFileRef] = []
    for child in children:
        attempt_id = child_attempt_ids.get(child.node_key)
        if attempt_id is None:
            continue
        refs.append(
            _checkpoint_ref_for_attempt_id(
                paths=paths,
                child_node_key=child.node_key,
                attempt_id=attempt_id,
            )
        )
    return tuple(refs)


async def _current_child_artifact_refs(
    session: AsyncSession,
    *,
    task_id: str,
    current_node: FlowNodeModel,
    flow_revision_id: str,
    recorded_at_cutoff: datetime | None = None,
) -> tuple[EvidenceRef, ...]:
    children = await _direct_child_nodes(
        session,
        current_node=current_node,
        flow_revision_id=flow_revision_id,
    )
    if not children:
        return ()
    child_node_keys = [child.node_key for child in children]
    if recorded_at_cutoff is None:
        current_pointers = list(
            await session.scalars(
                select(ArtifactCurrentPointerModel)
                .options(raiseload("*"))
                .where(
                    ArtifactCurrentPointerModel.task_id == task_id,
                    ArtifactCurrentPointerModel.owner_node_key.in_(child_node_keys),
                )
                .order_by(
                    ArtifactCurrentPointerModel.owner_node_key.asc(),
                    ArtifactCurrentPointerModel.slot.asc(),
                )
            )
        )
        return tuple(
            EvidenceRef(
                kind=EvidenceKind.ARTIFACT,
                slot=pointer.slot,
                version=pointer.current_version,
                path=Path(pointer.current_path),
                description=pointer.description,
            )
            for pointer in current_pointers
        )

    publications = list(
        await session.scalars(
            select(ArtifactPublicationModel)
            .options(raiseload("*"))
            .where(
                ArtifactPublicationModel.task_id == task_id,
                ArtifactPublicationModel.owner_node_key.in_(child_node_keys),
                ArtifactPublicationModel.published_at <= recorded_at_cutoff,
            )
            .order_by(
                ArtifactPublicationModel.owner_node_key.asc(),
                ArtifactPublicationModel.slot.asc(),
                ArtifactPublicationModel.published_at.desc(),
                ArtifactPublicationModel.version.desc(),
            )
        )
    )
    current_refs_by_identity: dict[tuple[str, str], EvidenceRef] = {}
    for publication in publications:
        identity = (publication.owner_node_key, publication.slot)
        if identity in current_refs_by_identity:
            continue
        current_refs_by_identity[identity] = EvidenceRef(
            kind=EvidenceKind.ARTIFACT,
            slot=publication.slot,
            version=publication.version,
            path=Path(publication.path),
            description=publication.description,
        )
    return tuple(current_refs_by_identity.values())
