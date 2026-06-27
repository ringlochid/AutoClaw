from __future__ import annotations

from datetime import datetime
from typing import Literal, NamedTuple, overload

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import (
    AssignmentModel,
    AttemptCheckpointModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
)
from autoclaw.runtime.boundary.transitions import advance_boundary_state
from autoclaw.runtime.clock import dispatch_control_deadline, utc_now
from autoclaw.runtime.contracts import (
    BoundaryRead,
    BoundaryWrite,
    CheckpointFileRef,
    CheckpointKind,
    EgressBoundary,
    FlowStatus,
    NodeKind,
    RuntimeFlowRead,
    TaskEventSource,
    TaskEventType,
    TaskRootPaths,
    WorkflowManifestRef,
)
from autoclaw.runtime.errors import (
    boundary_precondition_error,
    illegal_caller_error,
    illegal_state_error,
    missing_resource_error,
)
from autoclaw.runtime.flow.queries import (
    current_semantic_flow_target,
    latest_checkpoint_for_attempt,
)
from autoclaw.runtime.flow.service import runtime_flow_read
from autoclaw.runtime.post_commit.cases import stage_boundary_outputs
from autoclaw.runtime.post_commit.writes import DeferredRuntimeWrite
from autoclaw.runtime.projection.runtime_state import CurrentRuntimeState, current_runtime_state
from autoclaw.runtime.release.guards import terminal_release_basis_committed
from autoclaw.runtime.task_events import append_task_event
from autoclaw.runtime.task_root.reads import load_task_root_paths

TERMINAL_BOUNDARIES = frozenset(
    {EgressBoundary.GREEN, EgressBoundary.RETRY, EgressBoundary.BLOCKED}
)


class BoundaryContext(NamedTuple):
    state: CurrentRuntimeState
    dispatch: DispatchTurnModel
    latest_checkpoint: AttemptCheckpointModel | None
    checkpoint_ref: CheckpointFileRef | None


@overload
async def accept_boundary(
    session: AsyncSession,
    task_id: str,
    payload: BoundaryWrite,
    *,
    should_read_after_commit: Literal[False] = False,
    state: CurrentRuntimeState | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> BoundaryRead: ...


@overload
async def accept_boundary(
    session: AsyncSession,
    task_id: str,
    payload: BoundaryWrite,
    *,
    should_read_after_commit: Literal[True],
    state: CurrentRuntimeState | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> DeferredRuntimeWrite[BoundaryRead]: ...


async def accept_boundary(
    session: AsyncSession,
    task_id: str,
    payload: BoundaryWrite,
    *,
    should_read_after_commit: bool = False,
    state: CurrentRuntimeState | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> BoundaryRead | DeferredRuntimeWrite[BoundaryRead]:
    context = await _load_boundary_context(
        session,
        task_id,
        state=state,
        dispatch=dispatch,
    )
    _validate_boundary_acceptance(
        state=context.state,
        dispatch=context.dispatch,
        latest_checkpoint=context.latest_checkpoint,
        boundary=payload.boundary,
    )
    await _close_current_dispatch(
        session,
        task_id,
        state=context.state,
        dispatch=context.dispatch,
        boundary=payload.boundary,
    )
    await advance_boundary_state(
        session,
        task_id,
        state=context.state,
        dispatch=context.dispatch,
        boundary=payload.boundary,
        checkpoint_ref=context.checkpoint_ref,
    )
    boundary_accepted_at = utc_now()
    context.state.flow.updated_at = boundary_accepted_at
    await _append_boundary_progression_events(
        session,
        task_id=task_id,
        state=context.state,
        dispatch=context.dispatch,
        boundary=payload.boundary,
        checkpoint_ref=context.checkpoint_ref,
        occurred_at=boundary_accepted_at,
    )
    await session.flush()
    _stage_boundary_outputs(
        session,
        task_id,
        dispatch_id=context.dispatch.dispatch_id,
        attempt_ids=_retry_attempt_ids(
            boundary=payload.boundary,
            current_attempt_id=context.state.current_assignment.current_attempt_id,
        ),
    )
    if should_read_after_commit:

        async def _should_read_after_commit() -> BoundaryRead:
            return await _boundary_read(
                session,
                task_id=task_id,
                state=context.state,
                accepted_boundary=payload.boundary,
                checkpoint_ref=context.checkpoint_ref,
            )

        return DeferredRuntimeWrite(read_after_commit=_should_read_after_commit)
    return await _boundary_read(
        session,
        task_id=task_id,
        state=context.state,
        accepted_boundary=payload.boundary,
        checkpoint_ref=context.checkpoint_ref,
    )


def _build_boundary_checkpoint_ref(
    *,
    attempt_id: str,
    latest_checkpoint_id: str | None,
    paths: TaskRootPaths,
) -> CheckpointFileRef | None:
    if latest_checkpoint_id is None:
        return None
    return CheckpointFileRef(
        path=paths.attempts_path / attempt_id / "latest-checkpoint.md",
        description="Latest checkpoint for the current attempt.",
    )


def _validate_boundary_acceptance(
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    latest_checkpoint: AttemptCheckpointModel | None,
    boundary: EgressBoundary,
) -> None:
    if boundary == EgressBoundary.YIELD:
        if terminal_release_basis_committed(dispatch):
            raise boundary_precondition_error(
                "yield is illegal after terminal release basis was committed",
                suggested_next_step=(
                    "If this dispatch should stay non-terminal, stage exactly one child "
                    "assignment first, publish a progress checkpoint if later readers need "
                    "the reasoning, then emit `yield`. If the committed basis is "
                    "`release_green` or root `release_blocked`, close with the matching "
                    "terminal boundary instead."
                ),
            )
        if dispatch.staged_child_assignment_id is None:
            raise boundary_precondition_error(
                "yield requires exactly one staged child assignment",
                suggested_next_step=(
                    "If this dispatch should stay non-terminal, stage exactly one child "
                    "assignment first, publish a progress checkpoint if later readers need "
                    "the reasoning, then emit `yield`. Structural CRUD alone does not "
                    "justify `yield`."
                ),
            )
        return
    if (
        state.current_node.structural_kind != NodeKind.WORKER.value
        and boundary == EgressBoundary.RETRY
    ):
        raise illegal_caller_error("parent/root retry is illegal")
    if (
        latest_checkpoint is None
        or latest_checkpoint.checkpoint_kind != CheckpointKind.TERMINAL.value
    ):
        raise boundary_precondition_error(
            "terminal boundaries require a terminal checkpoint",
            suggested_next_step=(
                "Publish a terminal checkpoint with the matching outcome first, then emit "
                "the requested boundary."
            ),
        )
    if latest_checkpoint.outcome != boundary.value:
        raise boundary_precondition_error(
            "boundary does not match latest terminal checkpoint outcome",
            suggested_next_step=(
                "Reread the latest terminal checkpoint and emit the boundary that matches "
                "its recorded outcome."
            ),
        )


def _close_dispatch_for_boundary(
    dispatch: DispatchTurnModel,
    *,
    boundary: EgressBoundary,
    closed_at: datetime,
) -> None:
    dispatch.accepted_boundary = boundary.value
    dispatch.closed_by_boundary = boundary.value
    dispatch.closed_at = closed_at
    if dispatch.control_state == "live":
        dispatch.control_deadline_at = dispatch_control_deadline(base=closed_at)
        dispatch.control_state_reason = f"boundary:{boundary.value}:awaiting_inactivity"
    elif dispatch.control_state == "launching":
        dispatch.control_deadline_at = dispatch.control_deadline_at or dispatch_control_deadline(
            base=closed_at
        )
        dispatch.control_state_reason = f"boundary:{boundary.value}:launch_unconfirmed"
    elif dispatch.control_state == "fenced":
        dispatch.control_deadline_at = None
        dispatch.fenced_at = dispatch.fenced_at or closed_at


def _sync_delivery_state(
    delivery_state: DispatchDeliveryStateModel | None,
    *,
    closed_at: datetime,
) -> None:
    if delivery_state is None:
        return
    delivery_state.updated_at = closed_at


def _close_attempt_for_boundary(
    state: CurrentRuntimeState,
    *,
    boundary: EgressBoundary,
    closed_at: datetime,
) -> None:
    state.current_attempt.terminal_outcome = boundary.value
    state.current_attempt.closed_at = closed_at
    state.current_attempt.status = (
        "succeeded"
        if boundary == EgressBoundary.GREEN
        else "blocked"
        if boundary == EgressBoundary.BLOCKED
        else "failed"
    )


async def _load_boundary_context(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> BoundaryContext:
    state = state or await current_runtime_state(session, task_id)
    if dispatch is None:
        flow = state.flow
        if flow.current_open_dispatch_id is None:
            raise illegal_state_error("no current open dispatch")
        dispatch = await session.get(
            DispatchTurnModel,
            flow.current_open_dispatch_id,
            options=(raiseload("*"),),
        )
        if dispatch is None:
            raise missing_resource_error(f"missing dispatch '{flow.current_open_dispatch_id}'")
    latest_checkpoint = await latest_checkpoint_for_attempt(session, state.current_attempt)
    paths = await load_task_root_paths(session, task_id)
    checkpoint_ref = _build_boundary_checkpoint_ref(
        attempt_id=state.current_attempt.attempt_id,
        latest_checkpoint_id=state.current_attempt.latest_checkpoint_id,
        paths=paths,
    )
    return BoundaryContext(
        state=state,
        dispatch=dispatch,
        latest_checkpoint=latest_checkpoint,
        checkpoint_ref=checkpoint_ref,
    )


async def _close_current_dispatch(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    boundary: EgressBoundary,
) -> DispatchDeliveryStateModel | None:
    closed_at = utc_now()
    _close_dispatch_for_boundary(
        dispatch,
        boundary=boundary,
        closed_at=closed_at,
    )
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    _sync_delivery_state(
        delivery_state,
        closed_at=closed_at,
    )
    if boundary in TERMINAL_BOUNDARIES:
        _close_attempt_for_boundary(
            state,
            boundary=boundary,
            closed_at=closed_at,
        )
    return delivery_state


def _stage_boundary_outputs(
    session: AsyncSession,
    task_id: str,
    *,
    dispatch_id: str,
    attempt_ids: tuple[str, ...] = (),
) -> None:
    stage_boundary_outputs(
        session,
        task_id=task_id,
        dispatch_id=dispatch_id,
        attempt_ids=attempt_ids,
    )


async def _semantic_boundary_flow_read(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
) -> RuntimeFlowRead:
    semantic_target = await current_semantic_flow_target(
        session,
        flow=state.flow,
        incomplete_summary="accepted boundary left current semantic target incomplete",
        suggested_next_step=(
            "Inspect the committed node, assignment, and attempt currentness, then repair "
            "the incomplete semantic target before progressing this task."
        ),
    )
    if semantic_target is None:
        return await runtime_flow_read(session, task_id)
    paths = await load_task_root_paths(session, task_id)
    return RuntimeFlowRead(
        task_id=state.task.task_id,
        task_title=state.task.title,
        task_summary=state.task.summary,
        workflow_key=state.task.workflow_key,
        status=FlowStatus(state.flow.status),
        active_flow_revision_id=state.flow.active_flow_revision_id or "",
        workflow_manifest_ref=WorkflowManifestRef(
            path=paths.runtime_path / "workflow-manifest.md",
            description="Current generated workflow manifest for this runtime task.",
        ),
        current_node_key=semantic_target.node.node_key,
        active_attempt_id=semantic_target.attempt.attempt_id,
        updated_at=state.flow.updated_at,
    )


def _retry_attempt_ids(
    *,
    boundary: EgressBoundary,
    current_attempt_id: str | None,
) -> tuple[str, ...]:
    if boundary == EgressBoundary.RETRY and current_attempt_id is not None:
        return (current_attempt_id,)
    return ()


async def _boundary_read(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
    accepted_boundary: EgressBoundary,
    checkpoint_ref: CheckpointFileRef | None,
) -> BoundaryRead:
    return BoundaryRead(
        accepted_boundary=accepted_boundary,
        flow=await _semantic_boundary_flow_read(
            session,
            task_id=task_id,
            state=state,
        ),
        latest_checkpoint_ref=checkpoint_ref,
    )


async def _append_boundary_progression_events(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    boundary: EgressBoundary,
    checkpoint_ref: CheckpointFileRef | None,
    occurred_at: datetime,
) -> None:
    next_node_key, next_attempt_id = await _next_semantic_target(session, flow=state.flow)
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.BOUNDARY_ACCEPTED,
        event_source=TaskEventSource.NODE,
        occurred_at=occurred_at,
        flow_revision_id=state.flow.active_flow_revision_id,
        dispatch_id=dispatch.dispatch_id,
        attempt_id=state.current_attempt.attempt_id,
        node_key=state.current_node.node_key,
        payload={
            "boundary": boundary.value,
            "latest_checkpoint_ref": (
                None if checkpoint_ref is None else checkpoint_ref.model_dump(mode="json")
            ),
            "previous_node_key": state.current_node.node_key,
            "next_node_key": next_node_key,
            "next_attempt_id": next_attempt_id,
            "resulting_flow_status": state.flow.status,
            "requires_reopen_after_inactivity": state.flow.status == FlowStatus.RUNNING.value,
        },
    )
    if boundary != EgressBoundary.YIELD or dispatch.staged_child_assignment_id is None:
        return
    child_assignment = await session.get(AssignmentModel, dispatch.staged_child_assignment_id)
    if child_assignment is None or child_assignment.current_attempt_id is None:
        raise missing_resource_error("yield continuation basis is incomplete")
    await append_task_event(
        session,
        task_id=task_id,
        event_type=TaskEventType.CHILD_ASSIGNMENT_COMMITTED,
        event_source=TaskEventSource.CONTROLLER,
        occurred_at=occurred_at,
        flow_revision_id=child_assignment.flow_revision_id,
        dispatch_id=dispatch.dispatch_id,
        attempt_id=child_assignment.current_attempt_id,
        node_key=child_assignment.node_key,
        payload={
            "target_node_key": child_assignment.node_key,
            "target_assignment_key": child_assignment.assignment_key,
            "target_attempt_id": child_assignment.current_attempt_id,
            "parent_node_key": state.current_node.node_key,
            "source_dispatch_id": dispatch.dispatch_id,
            "boundary": EgressBoundary.YIELD.value,
        },
    )


async def _next_semantic_target(
    session: AsyncSession,
    *,
    flow: FlowModel,
) -> tuple[str | None, str | None]:
    if flow.status != FlowStatus.RUNNING.value:
        return None, None
    semantic_target = await current_semantic_flow_target(
        session,
        flow=flow,
        incomplete_summary="accepted boundary left current semantic target incomplete",
        suggested_next_step=(
            "Inspect the committed node, assignment, and attempt currentness, then repair "
            "the incomplete semantic target before progressing this task."
        ),
    )
    if semantic_target is None:
        return None, None
    return semantic_target.node.node_key, semantic_target.attempt.attempt_id


__all__ = ["accept_boundary"]
