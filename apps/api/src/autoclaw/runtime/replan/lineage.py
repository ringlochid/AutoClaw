from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from autoclaw.persistence.models import (
    ArtifactCurrentPointerModel,
    ArtifactPublicationModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    BudgetCounterModel,
    DispatchTurnModel,
    NodeSessionModel,
)
from autoclaw.runtime.errors import illegal_state_error

NodeSnapshot = dict[str, Any]


async def node_has_open_current_work(
    session: AsyncSession,
    node: NodeSnapshot,
) -> bool:
    current_assignment_id = node.get("current_assignment_id")
    if current_assignment_id is None:
        return False
    assignment = await session.get(AssignmentModel, str(current_assignment_id))
    if assignment is None or assignment.current_attempt_id is None:
        return False
    attempt = await session.get(AttemptModel, assignment.current_attempt_id)
    if attempt is None:
        return False
    return attempt.closed_at is None or attempt.terminal_outcome is None


async def rebind_current_runtime_lineage(
    session: AsyncSession,
    *,
    flow_id: str,
    next_revision_id: str,
    nodes: list[NodeSnapshot],
    next_flow_node_ids: dict[str, str],
    current_open_dispatch_id: str | None,
) -> None:
    assignment_node_ids, current_attempt_node_ids = await _rebind_assignments_and_attempts(
        session,
        flow_id=flow_id,
        next_revision_id=next_revision_id,
        nodes=nodes,
        next_flow_node_ids=next_flow_node_ids,
    )
    await _rebind_attempt_derivatives(session, current_attempt_node_ids)
    await _rebind_assignment_derivatives(session, flow_id, assignment_node_ids)
    await _rebind_open_dispatch(
        session,
        current_open_dispatch_id=current_open_dispatch_id,
        next_revision_id=next_revision_id,
        assignment_node_ids=assignment_node_ids,
    )


async def _rebind_assignments_and_attempts(
    session: AsyncSession,
    *,
    flow_id: str,
    next_revision_id: str,
    nodes: list[NodeSnapshot],
    next_flow_node_ids: dict[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    assignment_node_ids: dict[str, str] = {}
    current_attempt_node_ids: dict[str, str] = {}
    for node in nodes:
        current_assignment_id = node["current_assignment_id"]
        if current_assignment_id is None:
            continue
        assignment = await session.get(AssignmentModel, str(current_assignment_id))
        if assignment is None:
            raise illegal_state_error(f"missing current assignment '{current_assignment_id}'")
        next_flow_node_id = next_flow_node_ids[str(node["node_key"])]
        assignment.flow_id = flow_id
        assignment.flow_revision_id = next_revision_id
        assignment.flow_node_id = next_flow_node_id
        assignment_node_ids[assignment.assignment_id] = next_flow_node_id
        if assignment.current_attempt_id is not None:
            current_attempt = await session.get(AttemptModel, assignment.current_attempt_id)
            if current_attempt is None:
                raise illegal_state_error(
                    f"missing current attempt '{assignment.current_attempt_id}'"
                )
            current_attempt.flow_node_id = next_flow_node_id
            current_attempt_node_ids[current_attempt.attempt_id] = next_flow_node_id
    return assignment_node_ids, current_attempt_node_ids


async def _rebind_attempt_derivatives(
    session: AsyncSession,
    current_attempt_node_ids: dict[str, str],
) -> None:
    for checkpoint in await session.scalars(
        select(AttemptCheckpointModel).where(
            AttemptCheckpointModel.attempt_id.in_(tuple(current_attempt_node_ids))
        )
    ):
        checkpoint.flow_node_id = current_attempt_node_ids[checkpoint.attempt_id]

    for publication in await session.scalars(
        select(ArtifactPublicationModel).where(
            ArtifactPublicationModel.attempt_id.in_(tuple(current_attempt_node_ids))
        )
    ):
        publication.flow_node_id = current_attempt_node_ids[publication.attempt_id]

    for pointer in await session.scalars(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.attempt_id.in_(tuple(current_attempt_node_ids))
        )
    ):
        pointer.flow_node_id = current_attempt_node_ids[pointer.attempt_id]


async def _rebind_assignment_derivatives(
    session: AsyncSession,
    flow_id: str,
    assignment_node_ids: dict[str, str],
) -> None:
    for budget_counter in await session.scalars(
        select(BudgetCounterModel)
        .options(selectinload(BudgetCounterModel.assignment))
        .where(BudgetCounterModel.assignment_id.in_(tuple(assignment_node_ids)))
    ):
        assignment = budget_counter.assignment
        if assignment is None:
            continue
        budget_counter.flow_id = flow_id
        budget_counter.flow_node_id = assignment_node_ids[assignment.assignment_id]

    for node_session in await session.scalars(
        select(NodeSessionModel)
        .options(selectinload(NodeSessionModel.assignment))
        .where(
            NodeSessionModel.assignment_id.in_(tuple(assignment_node_ids)),
            NodeSessionModel.closed_at.is_(None),
        )
    ):
        assignment = node_session.assignment
        if assignment is None:
            continue
        node_session.flow_node_id = assignment_node_ids[assignment.assignment_id]


async def _rebind_open_dispatch(
    session: AsyncSession,
    *,
    current_open_dispatch_id: str | None,
    next_revision_id: str,
    assignment_node_ids: dict[str, str],
) -> None:
    if current_open_dispatch_id is None:
        return
    dispatch = await session.get(DispatchTurnModel, current_open_dispatch_id)
    if dispatch is None:
        raise illegal_state_error(f"missing open dispatch '{current_open_dispatch_id}'")
    if dispatch.assignment_id is None:
        return
    dispatch_assignment_id = dispatch.assignment_id
    if dispatch_assignment_id not in assignment_node_ids:
        raise illegal_state_error(
            "current open dispatch assignment is no longer attached to the adopted flow revision"
        )
    next_flow_node_id = assignment_node_ids[dispatch_assignment_id]
    dispatch.flow_revision_id = next_revision_id
    dispatch.flow_node_id = next_flow_node_id
