from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import (
    AssignmentModel,
    AttemptModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
    TaskModel,
)
from autoclaw.runtime.errors import illegal_state_error, missing_resource_error


@dataclass(frozen=True)
class CurrentRuntimeState:
    task: TaskModel
    flow: FlowModel
    flow_revision: FlowRevisionModel
    current_node: FlowNodeModel
    current_assignment: AssignmentModel
    current_attempt: AttemptModel


async def current_runtime_state(session: AsyncSession, task_id: str) -> CurrentRuntimeState:
    state = await _joined_current_runtime_state(session, task_id)
    if state is not None and state.flow.current_open_dispatch_id is None:
        return state
    if state is not None and state.flow.current_open_dispatch_id is not None:
        dispatch = await session.get(
            DispatchTurnModel,
            state.flow.current_open_dispatch_id,
            options=(raiseload("*"),),
        )
        if dispatch is None:
            raise missing_resource_error(
                f"missing dispatch '{state.flow.current_open_dispatch_id}'"
            )
        if (
            dispatch.node_key == state.current_node.node_key
            and dispatch.assignment_id == state.current_assignment.assignment_id
            and dispatch.attempt_id == state.current_attempt.attempt_id
        ):
            return state
        return await dispatch_runtime_state(
            session,
            task_id=task_id,
            dispatch=dispatch,
        )
    return await _load_current_runtime_state_without_join(session, task_id)


async def dispatch_runtime_state(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> CurrentRuntimeState:
    state = await _joined_dispatch_runtime_state(
        session,
        task_id=task_id,
        dispatch=dispatch,
    )
    if state is not None:
        return state

    task = await session.get(TaskModel, task_id, options=(raiseload("*"),))
    if task is None:
        raise missing_resource_error(f"unknown task_id '{task_id}'")
    flow = await session.scalar(
        select(FlowModel).options(raiseload("*")).where(FlowModel.task_id == task_id)
    )
    if flow is None:
        raise illegal_state_error(f"task '{task_id}' has no runtime flow")
    if dispatch.flow_revision_id is None:
        raise illegal_state_error(f"dispatch '{dispatch.dispatch_id}' has no flow revision")
    flow_revision = await session.get(
        FlowRevisionModel,
        dispatch.flow_revision_id,
        options=(raiseload("*"),),
    )
    if flow_revision is None:
        raise missing_resource_error(f"missing flow revision '{dispatch.flow_revision_id}'")
    if dispatch.flow_node_id is not None:
        current_node = await session.get(
            FlowNodeModel,
            dispatch.flow_node_id,
            options=(raiseload("*"),),
        )
    else:
        current_node = await session.scalar(
            select(FlowNodeModel)
            .options(raiseload("*"))
            .where(
                FlowNodeModel.flow_revision_id == dispatch.flow_revision_id,
                FlowNodeModel.node_key == dispatch.node_key,
            )
        )
    if current_node is None:
        raise missing_resource_error(f"missing flow node for dispatch '{dispatch.dispatch_id}'")
    if dispatch.assignment_id is None:
        raise illegal_state_error(f"dispatch '{dispatch.dispatch_id}' has no assignment")
    assignment = await session.get(
        AssignmentModel,
        dispatch.assignment_id,
        options=(raiseload("*"),),
    )
    if assignment is None:
        raise missing_resource_error(f"missing assignment '{dispatch.assignment_id}'")
    if dispatch.attempt_id is None:
        raise illegal_state_error(f"dispatch '{dispatch.dispatch_id}' has no attempt")
    attempt = await session.get(
        AttemptModel,
        dispatch.attempt_id,
        options=(raiseload("*"),),
    )
    if attempt is None:
        raise missing_resource_error(f"missing attempt '{dispatch.attempt_id}'")
    return CurrentRuntimeState(
        task=task,
        flow=flow,
        flow_revision=flow_revision,
        current_node=current_node,
        current_assignment=assignment,
        current_attempt=attempt,
    )


async def _joined_current_runtime_state(
    session: AsyncSession,
    task_id: str,
) -> CurrentRuntimeState | None:
    row = cast(
        tuple[
            TaskModel,
            FlowModel,
            FlowRevisionModel,
            FlowNodeModel,
            AssignmentModel,
            AttemptModel,
        ]
        | None,
        (
            await session.execute(
                select(
                    TaskModel,
                    FlowModel,
                    FlowRevisionModel,
                    FlowNodeModel,
                    AssignmentModel,
                    AttemptModel,
                )
                .options(raiseload("*"))
                .join(FlowModel, FlowModel.task_id == TaskModel.task_id)
                .join(
                    FlowRevisionModel,
                    FlowRevisionModel.flow_revision_id == FlowModel.active_flow_revision_id,
                )
                .join(
                    FlowNodeModel,
                    and_(
                        FlowNodeModel.flow_revision_id == FlowRevisionModel.flow_revision_id,
                        FlowNodeModel.node_key == FlowModel.current_node_key,
                    ),
                )
                .join(
                    AssignmentModel,
                    AssignmentModel.assignment_id == FlowNodeModel.current_assignment_id,
                )
                .join(
                    AttemptModel,
                    AttemptModel.attempt_id == AssignmentModel.current_attempt_id,
                )
                .where(TaskModel.task_id == task_id)
            )
        ).one_or_none(),
    )
    if row is None:
        return None
    task, flow, flow_revision, current_node, assignment, attempt = row
    return CurrentRuntimeState(
        task=task,
        flow=flow,
        flow_revision=flow_revision,
        current_node=current_node,
        current_assignment=assignment,
        current_attempt=attempt,
    )


async def _load_current_runtime_state_without_join(
    session: AsyncSession,
    task_id: str,
) -> CurrentRuntimeState:
    task = await session.get(TaskModel, task_id)
    if task is None:
        raise missing_resource_error(f"unknown task_id '{task_id}'")
    flow = await session.scalar(
        select(FlowModel).options(raiseload("*")).where(FlowModel.task_id == task_id)
    )
    if flow is None:
        raise illegal_state_error(f"task '{task_id}' has no active runtime flow")
    if flow.current_open_dispatch_id is not None:
        dispatch = await session.get(
            DispatchTurnModel,
            flow.current_open_dispatch_id,
            options=(raiseload("*"),),
        )
        if dispatch is None:
            raise missing_resource_error(f"missing dispatch '{flow.current_open_dispatch_id}'")
        return await dispatch_runtime_state(
            session,
            task_id=task_id,
            dispatch=dispatch,
        )
    if flow.active_flow_revision_id is None or flow.current_node_key is None:
        raise illegal_state_error(f"task '{task_id}' has no active runtime flow")
    flow_revision = await session.get(
        FlowRevisionModel,
        flow.active_flow_revision_id,
        options=(raiseload("*"),),
    )
    if flow_revision is None:
        raise missing_resource_error(
            f"missing active flow revision '{flow.active_flow_revision_id}'"
        )
    current_node = await session.scalar(
        select(FlowNodeModel)
        .options(raiseload("*"))
        .where(
            FlowNodeModel.flow_revision_id == flow_revision.flow_revision_id,
            FlowNodeModel.node_key == flow.current_node_key,
        )
    )
    if current_node is None or current_node.current_assignment_id is None:
        raise illegal_state_error(f"missing current assignment for node '{flow.current_node_key}'")
    assignment = await session.get(
        AssignmentModel,
        current_node.current_assignment_id,
        options=(raiseload("*"),),
    )
    if assignment is None or assignment.current_attempt_id is None:
        raise illegal_state_error(
            f"missing current attempt for assignment '{current_node.current_assignment_id}'"
        )
    attempt = await session.get(
        AttemptModel,
        assignment.current_attempt_id,
        options=(raiseload("*"),),
    )
    if attempt is None:
        raise missing_resource_error(f"missing attempt '{assignment.current_attempt_id}'")
    return CurrentRuntimeState(
        task=task,
        flow=flow,
        flow_revision=flow_revision,
        current_node=current_node,
        current_assignment=assignment,
        current_attempt=attempt,
    )


async def _joined_dispatch_runtime_state(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> CurrentRuntimeState | None:
    if (
        dispatch.flow_revision_id is None
        or dispatch.assignment_id is None
        or dispatch.attempt_id is None
    ):
        return None
    node_join = (
        FlowNodeModel.flow_node_id == dispatch.flow_node_id
        if dispatch.flow_node_id is not None
        else and_(
            FlowNodeModel.flow_revision_id == dispatch.flow_revision_id,
            FlowNodeModel.node_key == dispatch.node_key,
        )
    )
    row = cast(
        tuple[
            TaskModel,
            FlowModel,
            FlowRevisionModel,
            FlowNodeModel,
            AssignmentModel,
            AttemptModel,
        ]
        | None,
        (
            await session.execute(
                select(
                    TaskModel,
                    FlowModel,
                    FlowRevisionModel,
                    FlowNodeModel,
                    AssignmentModel,
                    AttemptModel,
                )
                .options(raiseload("*"))
                .join(FlowModel, FlowModel.task_id == TaskModel.task_id)
                .join(
                    FlowRevisionModel,
                    FlowRevisionModel.flow_revision_id == dispatch.flow_revision_id,
                )
                .join(FlowNodeModel, node_join)
                .join(
                    AssignmentModel,
                    AssignmentModel.assignment_id == dispatch.assignment_id,
                )
                .join(
                    AttemptModel,
                    AttemptModel.attempt_id == dispatch.attempt_id,
                )
                .where(
                    TaskModel.task_id == task_id,
                    FlowModel.flow_id == dispatch.flow_id,
                    FlowNodeModel.flow_revision_id == dispatch.flow_revision_id,
                )
            )
        ).one_or_none(),
    )
    if row is None:
        return None
    task, flow, flow_revision, current_node, assignment, attempt = row
    return CurrentRuntimeState(
        task=task,
        flow=flow,
        flow_revision=flow_revision,
        current_node=current_node,
        current_assignment=assignment,
        current_attempt=attempt,
    )
