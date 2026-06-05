from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
)
from autoclaw.runtime.contracts import CheckpointKind
from autoclaw.runtime.errors import illegal_state_error
from autoclaw.runtime.flow.queries import (
    current_semantic_flow_target,
    latest_checkpoint_for_attempt,
    latest_resumable_dispatch_for_attempt,
)

SEMANTIC_TARGET_INCOMPLETE_SUMMARY = "current semantic target is incomplete"
SEMANTIC_TARGET_REPAIR_NEXT_STEP = (
    "Inspect the current node assignment and attempt currentness, then repair the "
    "incomplete semantic target before continuing this task."
)
TERMINAL_CONTROL_NEXT_STEP = (
    "Reread the latest checkpoint and emit the matching terminal boundary instead of "
    "pausing, cancelling, or continuing this flow."
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
    if _attempt_has_terminal_state(attempt, latest_checkpoint):
        raise illegal_state_error(
            "paused flow cannot continue after a terminal checkpoint",
            suggested_next_step=TERMINAL_CONTROL_NEXT_STEP,
        )


async def ensure_flow_interruptible(
    session: AsyncSession,
    attempt: AttemptModel | None,
    *,
    action: str,
) -> None:
    if attempt is None:
        return
    latest_checkpoint = await latest_checkpoint_for_attempt(session, attempt)
    if _attempt_has_terminal_state(attempt, latest_checkpoint):
        raise illegal_state_error(
            f"{action} is illegal after a terminal checkpoint",
            suggested_next_step=TERMINAL_CONTROL_NEXT_STEP,
        )


async def resolve_flow_resume_target(
    session: AsyncSession,
    *,
    flow: FlowModel,
    previous_dispatch: DispatchTurnModel | None,
) -> FlowResumeTarget:
    if flow.current_open_dispatch_id is not None:
        return FlowResumeTarget(previous_dispatch=previous_dispatch)
    current_assignment_target = await _resume_target_from_current_assignment(
        session,
        flow=flow,
        previous_dispatch=previous_dispatch,
    )
    if current_assignment_target is not None:
        return current_assignment_target
    if previous_dispatch is not None and previous_dispatch.accepted_boundary is not None:
        raise illegal_state_error(
            SEMANTIC_TARGET_INCOMPLETE_SUMMARY,
            suggested_next_step=SEMANTIC_TARGET_REPAIR_NEXT_STEP,
        )
    return FlowResumeTarget(previous_dispatch=previous_dispatch)


def _attempt_has_terminal_state(
    attempt: AttemptModel,
    latest_checkpoint: AttemptCheckpointModel | None,
) -> bool:
    return (
        attempt.closed_at is not None
        or attempt.terminal_outcome is not None
        or (
            latest_checkpoint is not None
            and latest_checkpoint.checkpoint_kind == CheckpointKind.TERMINAL.value
        )
    )


async def _resume_target_from_current_assignment(
    session: AsyncSession,
    *,
    flow: FlowModel,
    previous_dispatch: DispatchTurnModel | None,
) -> FlowResumeTarget | None:
    semantic_target = await current_semantic_flow_target(
        session,
        flow=flow,
        incomplete_summary=SEMANTIC_TARGET_INCOMPLETE_SUMMARY,
        suggested_next_step=SEMANTIC_TARGET_REPAIR_NEXT_STEP,
    )
    if semantic_target is None:
        return None
    resumable_dispatch = await latest_resumable_dispatch_for_attempt(
        session,
        task_id=flow.task_id,
        attempt_id=semantic_target.attempt.attempt_id,
    )
    return FlowResumeTarget(
        node=semantic_target.node,
        assignment=semantic_target.assignment,
        attempt=semantic_target.attempt,
        previous_dispatch=previous_dispatch or resumable_dispatch,
    )
