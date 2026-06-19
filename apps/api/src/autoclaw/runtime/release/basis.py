from __future__ import annotations

from pathlib import Path
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    AttemptModel,
    FlowEdgeModel,
    FlowNodeModel,
)
from autoclaw.runtime.contracts import EvidenceKind, EvidenceRef
from autoclaw.runtime.errors import (
    boundary_precondition_error,
    missing_required_publication_error,
    stale_checkpoint_error,
)
from autoclaw.runtime.post_commit.validation import (
    SurfacedRefFailure,
    attempt_checkpoint_projection_failure,
    current_surfaced_ref_detail,
    current_surfaced_ref_failure,
)


async def ensure_assignment_required_publications(
    session: AsyncSession,
    *,
    task_id: str,
    assignment: AssignmentModel,
    is_boundary_mode: bool = False,
) -> None:
    slots = {str(requirement["slot"]) for requirement in assignment.produces_json}
    pointer_pairs = await current_pointer_pairs(
        session,
        task_id=task_id,
        assignment_keys={assignment.assignment_key},
        slots=slots,
    )
    for requirement in assignment.produces_json:
        slot = str(requirement["slot"])
        if (assignment.assignment_key, slot) in pointer_pairs:
            continue
        summary = f"missing required publication for assignment '{assignment.assignment_key}'"
        if is_boundary_mode:
            raise boundary_precondition_error(summary)
        raise missing_required_publication_error(summary)


async def flow_node_assignment_attempt_rows(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    parent_flow_node_id: str | None = None,
) -> list[tuple[FlowNodeModel, AssignmentModel | None, AttemptModel | None]]:
    query = (
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
        .where(FlowNodeModel.flow_revision_id == flow_revision_id)
        .order_by(FlowNodeModel.order_index.asc(), FlowNodeModel.node_key.asc())
    )
    if parent_flow_node_id is not None:
        query = query.where(FlowNodeModel.parent_flow_node_id == parent_flow_node_id)
    return cast(
        list[tuple[FlowNodeModel, AssignmentModel | None, AttemptModel | None]],
        (await session.execute(query)).all(),
    )


async def current_pointer_pairs(
    session: AsyncSession,
    *,
    task_id: str,
    assignment_keys: set[str],
    slots: set[str],
) -> set[tuple[str, str]]:
    if not assignment_keys or not slots:
        return set()
    pointers = list(
        await session.scalars(
            select(ArtifactCurrentPointerModel)
            .options(raiseload("*"))
            .where(
                ArtifactCurrentPointerModel.task_id == task_id,
                ArtifactCurrentPointerModel.assignment_key.in_(assignment_keys),
                ArtifactCurrentPointerModel.slot.in_(slots),
            )
        )
    )
    current_pairs: set[tuple[str, str]] = set()
    for pointer in pointers:
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
            current_pairs.add((pointer.assignment_key, pointer.slot))
    return current_pairs


async def ensure_current_assignment_basis_is_current(
    session: AsyncSession,
    *,
    task_id: str,
    assignment: AssignmentModel,
    action_name: str,
    is_boundary_mode: bool = False,
) -> None:
    for ref in [*assignment.criteria_json, *assignment.consumes_json]:
        failure = await current_surfaced_ref_failure(session, task_id=task_id, ref=ref)
        if failure is not None:
            summary = f"{action_name} requires current surfaced evidence: {failure}"
            if is_boundary_mode:
                raise boundary_precondition_error(summary)
            raise stale_checkpoint_error(summary)


async def ensure_release_green_child_assignment_basis_is_current(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    assignment: AssignmentModel,
    is_boundary_mode: bool = False,
) -> None:
    for ref in [*assignment.criteria_json, *assignment.consumes_json]:
        detail = await current_surfaced_ref_detail(session, task_id=task_id, ref=ref)
        if detail is None:
            continue
        if await _tolerate_release_green_child_stale_ref(
            session,
            flow_revision_id=flow_revision_id,
            assignment=assignment,
            detail=detail,
        ):
            continue
        summary = (
            "release_green requires current surfaced evidence for child assignment "
            f"'{assignment.assignment_key}': {detail.summary}"
        )
        suggested_next_step = _release_green_child_stale_next_step(
            assignment=assignment,
            detail=detail,
        )
        if is_boundary_mode:
            raise boundary_precondition_error(summary, suggested_next_step=suggested_next_step)
        raise stale_checkpoint_error(summary, suggested_next_step=suggested_next_step)


async def ensure_current_checkpoint_projection(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
    action_name: str,
    is_boundary_mode: bool = False,
) -> None:
    failure = await attempt_checkpoint_projection_failure(
        session,
        task_id=task_id,
        attempt_id=attempt_id,
    )
    if failure is not None:
        summary = f"{action_name} requires current checkpoint evidence: {failure}"
        if is_boundary_mode:
            raise boundary_precondition_error(summary)
        raise stale_checkpoint_error(summary)


__all__ = [
    "current_pointer_pairs",
    "ensure_assignment_required_publications",
    "ensure_current_assignment_basis_is_current",
    "ensure_current_checkpoint_projection",
    "ensure_release_green_child_assignment_basis_is_current",
    "flow_node_assignment_attempt_rows",
]


async def _tolerate_release_green_child_stale_ref(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    assignment: AssignmentModel,
    detail: SurfacedRefFailure,
) -> bool:
    if detail.reason != "artifact_ref_stale" or detail.current_owner_node_key is None:
        return False
    if detail.current_owner_node_key == assignment.node_key:
        return True
    return await _node_is_downstream_of(
        session,
        flow_revision_id=flow_revision_id,
        source_node_key=assignment.node_key,
        target_node_key=detail.current_owner_node_key,
    )


async def _node_is_downstream_of(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    source_node_key: str,
    target_node_key: str,
) -> bool:
    if source_node_key == target_node_key:
        return True
    edges = list(
        await session.scalars(
            select(FlowEdgeModel)
            .options(raiseload("*"))
            .where(FlowEdgeModel.flow_revision_id == flow_revision_id)
        )
    )
    consumers_by_provider: dict[str, set[str]] = {}
    for edge in edges:
        consumers_by_provider.setdefault(edge.provider_node_key, set()).add(edge.consumer_node_key)
    frontier = [source_node_key]
    seen = {source_node_key}
    while frontier:
        provider = frontier.pop()
        for consumer in consumers_by_provider.get(provider, ()):
            if consumer == target_node_key:
                return True
            if consumer in seen:
                continue
            seen.add(consumer)
            frontier.append(consumer)
    return False


def _release_green_child_stale_next_step(
    *,
    assignment: AssignmentModel,
    detail: SurfacedRefFailure,
) -> str:
    if detail.reason == "artifact_ref_stale" and detail.slot is not None:
        return (
            f"Reread the latest checkpoint and current pointer for slot '{detail.slot}'. "
            "If this child was intentionally reassigned for a patch or review loop, keep "
            "older feedback artifacts as transient carryover or rely on the latest "
            "checkpoint plus current publications instead of the superseded durable ref."
        )
    return (
        "Reread the latest relevant checkpoint and current surfaced refs for this child "
        "assignment, then either refresh the stale basis or stage the next legal child "
        "iteration against current publications."
    )
