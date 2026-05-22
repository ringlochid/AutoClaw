from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import (
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
)
from app.runtime.control.failures import illegal_state_error, missing_resource_error


@dataclass(frozen=True, slots=True)
class SemanticFlowTarget:
    node: FlowNodeModel
    assignment: AssignmentModel
    attempt: AttemptModel


async def next_node_sequence_number(
    session: AsyncSession,
    model: type[AttemptModel] | type[DispatchTurnModel],
    task_id: str,
    node_key: str,
) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(model)
        .where(
            model.task_id == task_id,
            model.node_key == node_key,
        )
    )
    return int(count or 0) + 1


async def require_flow_for_task(session: AsyncSession, task_id: str) -> FlowModel:
    flow = await session.scalar(
        select(FlowModel).options(raiseload("*")).where(FlowModel.task_id == task_id)
    )
    if flow is None:
        raise missing_resource_error(f"unknown task_id '{task_id}'")
    return flow


async def flow_node_by_key(
    session: AsyncSession,
    flow_revision_id: str,
    node_key: str,
) -> FlowNodeModel:
    node = await session.scalar(
        select(FlowNodeModel)
        .options(raiseload("*"))
        .where(
            FlowNodeModel.flow_revision_id == flow_revision_id,
            FlowNodeModel.node_key == node_key,
        )
    )
    if node is None:
        raise missing_resource_error(f"unknown node_key '{node_key}'")
    return node


async def latest_checkpoint_for_attempt(
    session: AsyncSession,
    attempt: AttemptModel,
) -> AttemptCheckpointModel | None:
    if attempt.latest_checkpoint_id is None:
        return None
    return await session.get(AttemptCheckpointModel, attempt.latest_checkpoint_id)


async def latest_resumable_dispatch_for_attempt(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> DispatchTurnModel | None:
    dispatch = await session.scalar(
        select(DispatchTurnModel)
        .where(
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.attempt_id == attempt_id,
            DispatchTurnModel.accepted_boundary.is_(None),
            DispatchTurnModel.closed_at.is_not(None),
        )
        .order_by(DispatchTurnModel.rendered_at.desc())
    )
    return dispatch


async def current_semantic_flow_target(
    session: AsyncSession,
    *,
    flow: FlowModel,
    incomplete_summary: str,
    suggested_next_step: str | None = None,
) -> SemanticFlowTarget | None:
    if flow.active_flow_revision_id is None or flow.current_node_key is None:
        return None
    node = await flow_node_by_key(
        session,
        flow.active_flow_revision_id,
        flow.current_node_key,
    )
    if node.current_assignment_id is None:
        if suggested_next_step is None:
            raise illegal_state_error(incomplete_summary)
        raise illegal_state_error(
            incomplete_summary,
            suggested_next_step=suggested_next_step,
        )
    assignment = await session.get(AssignmentModel, node.current_assignment_id)
    if assignment is None:
        raise missing_resource_error(f"missing current assignment '{node.current_assignment_id}'")
    if assignment.current_attempt_id is None:
        if suggested_next_step is None:
            raise illegal_state_error(incomplete_summary)
        raise illegal_state_error(
            incomplete_summary,
            suggested_next_step=suggested_next_step,
        )
    attempt = await session.get(AttemptModel, assignment.current_attempt_id)
    if attempt is None:
        if suggested_next_step is None:
            raise illegal_state_error(incomplete_summary)
        raise illegal_state_error(
            incomplete_summary,
            suggested_next_step=suggested_next_step,
        )
    return SemanticFlowTarget(
        node=node,
        assignment=assignment,
        attempt=attempt,
    )
