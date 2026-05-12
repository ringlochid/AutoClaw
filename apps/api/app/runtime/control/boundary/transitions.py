from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssignmentModel,
    AttemptConsumedRefModel,
    AttemptModel,
    DispatchTurnModel,
)
from app.runtime.contracts import (
    EgressBoundary,
    FlowStatus,
    NodeKind,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
)
from app.runtime.control.boundary.relations import (
    parent_node_from_relation,
    release_turn_descendant_refs,
)
from app.runtime.control.budgets import consume_assignment_budget
from app.runtime.control.flow.queries import next_node_sequence_number
from app.runtime.control.release.preconditions import (
    ensure_assignment_required_publications,
    ensure_release_blocked_preconditions,
    ensure_release_green_preconditions,
)
from app.runtime.effects.queue import (
    queue_attempt_materialization,
    queue_manifest_materialization,
)
from app.runtime.ids import attempt_consumed_ref_id, attempt_id_for_task
from app.runtime.projection import CurrentRuntimeState
from app.schemas.runtime import CheckpointFileRef


async def advance_boundary_state(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    boundary: EgressBoundary,
    checkpoint_ref: CheckpointFileRef | None,
) -> None:
    if state.current_node.structural_kind == NodeKind.WORKER.value:
        await _handle_worker_boundary(
            session,
            task_id,
            state=state,
            boundary=boundary,
            checkpoint_ref=checkpoint_ref,
        )
        return
    await _handle_parent_boundary(
        session,
        task_id,
        state=state,
        dispatch=dispatch,
        boundary=boundary,
    )


def _retry_consumed_refs(
    *,
    consumes_json: list[dict[str, object]],
    checkpoint_ref: CheckpointFileRef | None,
) -> list[dict[str, object]]:
    retry_consumed_refs = [
        ref for ref in consumes_json if ref.get("kind") != NodeRuntimeFileKind.CHECKPOINT.value
    ]
    if checkpoint_ref is not None:
        retry_consumed_refs.insert(
            0,
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=checkpoint_ref.path,
                description="Prior terminal retry checkpoint for the same assignment.",
            ).model_dump(mode="json"),
        )
    return retry_consumed_refs


async def _start_retry_attempt(
    session: AsyncSession,
    task_id: str,
    *,
    node_key: str,
    current_attempt: AttemptModel,
    current_assignment: AssignmentModel,
    policy_key: str | None,
    policy_revision_no: int | None,
    flow_id: str,
) -> str:
    await consume_assignment_budget(
        session,
        budget_family="retry",
        limit_field="retry_limit",
        policy_key=policy_key,
        policy_revision_no=policy_revision_no,
        flow_id=flow_id,
        flow_node_id=current_assignment.flow_node_id,
        assignment_id=current_assignment.assignment_id,
        attempt_id=current_attempt.attempt_id,
    )
    retry_attempt_id = attempt_id_for_task(
        task_id,
        node_key,
        await next_node_sequence_number(session, AttemptModel, task_id, node_key),
    )
    current_assignment.current_attempt_id = retry_attempt_id
    retry_attempt = AttemptModel(
        attempt_id=retry_attempt_id,
        assignment_id=current_assignment.assignment_id,
        assignment_key=current_assignment.assignment_key,
        flow_node_id=current_assignment.flow_node_id,
        task_id=task_id,
        node_key=node_key,
        retry_of_attempt_id=current_attempt.attempt_id,
        status="running",
    )
    session.add(retry_attempt)
    await session.flush()
    return retry_attempt_id


async def _persist_retry_consumed_refs(
    session: AsyncSession,
    *,
    retry_attempt_id: str,
    criteria_json: list[dict[str, object]],
    retry_consumed_refs: list[dict[str, object]],
) -> None:
    for index, ref in enumerate([*criteria_json, *retry_consumed_refs], start=1):
        session.add(
            AttemptConsumedRefModel(
                attempt_consumed_ref_id=attempt_consumed_ref_id(retry_attempt_id, index),
                attempt_id=retry_attempt_id,
                ref_kind=str(ref["kind"]),
                slot=ref.get("slot"),
                version=ref.get("version"),
                path=str(ref["path"]),
                description=str(ref["description"]),
                order_index=index,
            )
        )
    await session.flush()


async def _handle_retry_boundary(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    checkpoint_ref: CheckpointFileRef | None,
) -> None:
    retry_attempt_id = await _start_retry_attempt(
        session,
        task_id,
        node_key=state.current_node.node_key,
        current_attempt=state.current_attempt,
        current_assignment=state.current_assignment,
        policy_key=state.current_node.policy_key,
        policy_revision_no=state.current_node.policy_revision_no,
        flow_id=state.flow.flow_id,
    )
    await _persist_retry_consumed_refs(
        session,
        retry_attempt_id=retry_attempt_id,
        criteria_json=state.current_assignment.criteria_json,
        retry_consumed_refs=_retry_consumed_refs(
            consumes_json=state.current_assignment.consumes_json,
            checkpoint_ref=checkpoint_ref,
        ),
    )
    queue_attempt_materialization(
        session,
        task_id=task_id,
        attempt_id=retry_attempt_id,
    )
    queue_manifest_materialization(session, task_id=task_id)
    state.flow.current_node_key = state.current_node.node_key


async def _handle_worker_boundary(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    boundary: EgressBoundary,
    checkpoint_ref: CheckpointFileRef | None,
) -> None:
    if boundary == EgressBoundary.RETRY:
        await _handle_retry_boundary(
            session,
            task_id,
            state=state,
            checkpoint_ref=checkpoint_ref,
        )
        return
    parent_node = await parent_node_from_relation(session, node=state.current_node)
    if boundary == EgressBoundary.GREEN:
        await ensure_assignment_required_publications(
            session,
            task_id=task_id,
            assignment=state.current_assignment,
            allow_pending_current_attempt_publications=True,
        )
    if parent_node is None:
        state.flow.status = (
            FlowStatus.SUCCEEDED.value
            if boundary == EgressBoundary.GREEN
            else FlowStatus.BLOCKED.value
        )
        return
    state.flow.current_node_key = parent_node.node_key


async def _handle_parent_green(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
) -> None:
    flow = state.flow
    if dispatch.release_precondition_kind != "release_green":
        raise ValueError("green requires release_green first")
    if (
        dispatch.release_precondition_flow_revision_id != flow.active_flow_revision_id
        or dispatch.release_precondition_assignment_id != state.current_assignment.assignment_id
    ):
        raise ValueError("green release precondition is stale")
    await ensure_release_green_preconditions(
        session,
        task_id=task_id,
        flow_revision_id=flow.active_flow_revision_id or "",
        current_node_key=state.current_node.node_key,
        current_assignment=state.current_assignment,
    )
    dispatch.release_precondition_descendant_refs_json = await release_turn_descendant_refs(
        session,
        task_id=task_id,
        current_node=state.current_node,
        flow_revision_id=flow.active_flow_revision_id or "",
    )
    parent_node = await parent_node_from_relation(session, node=state.current_node)
    if parent_node is None:
        flow.status = FlowStatus.SUCCEEDED.value
    else:
        flow.current_node_key = parent_node.node_key


async def _handle_parent_blocked(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
) -> None:
    flow = state.flow
    if (
        state.current_node.structural_kind != NodeKind.ROOT.value
        or dispatch.release_precondition_kind != "release_blocked"
    ):
        raise ValueError("blocked requires root release_blocked first")
    if (
        dispatch.release_precondition_flow_revision_id != flow.active_flow_revision_id
        or dispatch.release_precondition_assignment_id != state.current_assignment.assignment_id
    ):
        raise ValueError("blocked release precondition is stale")
    await ensure_release_blocked_preconditions(
        session,
        task_id=task_id,
        flow_revision_id=flow.active_flow_revision_id or "",
        current_node_key=state.current_node.node_key,
        current_assignment=state.current_assignment,
    )
    dispatch.release_precondition_descendant_refs_json = await release_turn_descendant_refs(
        session,
        task_id=task_id,
        current_node=state.current_node,
        flow_revision_id=flow.active_flow_revision_id or "",
    )
    flow.status = FlowStatus.BLOCKED.value


async def _handle_parent_boundary(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    boundary: EgressBoundary,
) -> None:
    if boundary == EgressBoundary.YIELD:
        assignment = await session.get(AssignmentModel, dispatch.staged_child_assignment_id)
        if assignment is None or assignment.current_attempt_id is None:
            raise ValueError("staged child assignment is incomplete")
        return
    if boundary == EgressBoundary.GREEN:
        await _handle_parent_green(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
        )
        return
    await _handle_parent_blocked(
        session,
        task_id,
        state=state,
        dispatch=dispatch,
    )


__all__ = [
    "advance_boundary_state",
]
