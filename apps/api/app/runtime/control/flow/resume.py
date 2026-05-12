from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssignmentModel,
    AttemptModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
)
from app.runtime.contracts import CheckpointKind, EgressBoundary
from app.runtime.control.flow.queries import (
    flow_node_by_key,
    latest_checkpoint_for_attempt,
    latest_resumable_dispatch_for_attempt,
)


@dataclass(slots=True)
class FlowResumeTarget:
    node: FlowNodeModel | None = None
    assignment: AssignmentModel | None = None
    attempt: AttemptModel | None = None
    previous_dispatch: DispatchTurnModel | None = None

    def dispatch_open_inputs(
        self,
    ) -> tuple[FlowNodeModel, AssignmentModel, AttemptModel, str | None, str | None] | None:
        if self.node is None or self.assignment is None or self.attempt is None:
            return None
        previous_dispatch_id = (
            None if self.previous_dispatch is None else self.previous_dispatch.dispatch_id
        )
        staged_child_assignment_id = None
        if (
            self.previous_dispatch is not None
            and self.previous_dispatch.attempt_id == self.attempt.attempt_id
            and self.previous_dispatch.node_key == self.node.node_key
        ):
            staged_child_assignment_id = self.previous_dispatch.staged_child_assignment_id
        return (
            self.node,
            self.assignment,
            self.attempt,
            previous_dispatch_id,
            staged_child_assignment_id,
        )


async def ensure_flow_resumeable(
    session: AsyncSession,
    attempt: AttemptModel | None,
) -> None:
    if attempt is None:
        return
    latest_checkpoint = await latest_checkpoint_for_attempt(session, attempt)
    if (
        attempt.closed_at is not None
        or attempt.terminal_outcome is not None
        or (
            latest_checkpoint is not None
            and latest_checkpoint.checkpoint_kind == CheckpointKind.TERMINAL.value
        )
    ):
        raise ValueError("paused flow cannot continue after a terminal checkpoint")


async def resolve_flow_resume_target(
    session: AsyncSession,
    *,
    flow: FlowModel,
    previous_dispatch: DispatchTurnModel | None,
) -> FlowResumeTarget:
    if flow.current_open_dispatch_id is not None:
        return FlowResumeTarget(previous_dispatch=previous_dispatch)
    staged_child_target = await _resume_target_from_staged_child(
        session,
        previous_dispatch=previous_dispatch,
    )
    if staged_child_target is not None:
        return staged_child_target
    current_assignment_target = await _resume_target_from_current_assignment(
        session,
        flow=flow,
        previous_dispatch=previous_dispatch,
    )
    if current_assignment_target is not None:
        return current_assignment_target
    return FlowResumeTarget(previous_dispatch=previous_dispatch)


async def _resume_target_from_staged_child(
    session: AsyncSession,
    *,
    previous_dispatch: DispatchTurnModel | None,
) -> FlowResumeTarget | None:
    if (
        previous_dispatch is None
        or previous_dispatch.accepted_boundary != EgressBoundary.YIELD.value
        or previous_dispatch.staged_child_assignment_id is None
    ):
        return None
    assignment = await session.get(AssignmentModel, previous_dispatch.staged_child_assignment_id)
    if assignment is None or assignment.current_attempt_id is None:
        raise ValueError("staged child assignment is incomplete")
    node = await session.get(FlowNodeModel, assignment.flow_node_id)
    if node is None:
        raise ValueError(f"missing flow node '{assignment.flow_node_id}'")
    attempt = await session.get(AttemptModel, assignment.current_attempt_id)
    if attempt is None:
        raise ValueError(f"missing attempt '{assignment.current_attempt_id}'")
    return FlowResumeTarget(
        node=node,
        assignment=assignment,
        attempt=attempt,
        previous_dispatch=previous_dispatch,
    )


async def _resume_target_from_current_assignment(
    session: AsyncSession,
    *,
    flow: FlowModel,
    previous_dispatch: DispatchTurnModel | None,
) -> FlowResumeTarget | None:
    if flow.current_node_key is None:
        return None
    node = await flow_node_by_key(
        session,
        flow.active_flow_revision_id or "",
        flow.current_node_key,
    )
    if node.current_assignment_id is None:
        return FlowResumeTarget(node=node, previous_dispatch=previous_dispatch)
    assignment = await session.get(AssignmentModel, node.current_assignment_id)
    if assignment is None:
        return FlowResumeTarget(node=node, previous_dispatch=previous_dispatch)
    if assignment.current_attempt_id is None:
        return FlowResumeTarget(
            node=node, assignment=assignment, previous_dispatch=previous_dispatch
        )
    attempt = await session.get(AttemptModel, assignment.current_attempt_id)
    if attempt is None:
        return FlowResumeTarget(
            node=node, assignment=assignment, previous_dispatch=previous_dispatch
        )
    resumable_dispatch = await latest_resumable_dispatch_for_attempt(
        session,
        task_id=flow.task_id,
        attempt_id=attempt.attempt_id,
    )
    return FlowResumeTarget(
        node=node,
        assignment=assignment,
        attempt=attempt,
        previous_dispatch=previous_dispatch or resumable_dispatch,
    )
