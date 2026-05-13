from __future__ import annotations

from typing import Any, NamedTuple, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AssignmentModel, AttemptModel, DispatchTurnModel, FlowNodeModel
from app.runtime.contracts import EvidenceRef, NodeRuntimeFileRef, TaskRootPaths
from app.runtime.control.assignment.persistence import (
    latest_checkpoint_ref,
    persist_assignment_criteria_refs,
    persist_attempt_consumed_refs,
    planned_transient_refs,
    queue_transient_surface_copies,
)
from app.runtime.control.assignment.staging import (
    load_superseded_child_assignment,
    resolve_assign_child_dependency_refs,
)
from app.runtime.control.budgets import consume_assignment_budget
from app.runtime.control.clock import utc_now
from app.runtime.control.failures import illegal_state_error, illegal_target_relation_error
from app.runtime.control.flow.queries import flow_node_by_key, next_node_sequence_number
from app.runtime.control.flow.service import runtime_flow_read
from app.runtime.control.release.guards import ensure_no_staged_child_assignment
from app.runtime.effects.queue import (
    queue_attempt_materialization,
    queue_manifest_materialization,
)
from app.runtime.ids import assignment_id, assignment_key_for_task, attempt_id_for_task
from app.runtime.projection import CurrentRuntimeState, load_task_root_paths
from app.schemas.runtime import AssignChildSuccess, AssignmentFileRef, WorkflowManifestRef
from app.schemas.runtime.parent_tools import AssignChildToolCall


def _artifact_requirements(node: FlowNodeModel) -> list[dict[str, object]]:
    produces = cast(dict[str, Any], node.produces_json or {})
    return list(cast(list[dict[str, object]], produces.get("artifacts", [])))


class PreparedChildAssignment(NamedTuple):
    child_node: FlowNodeModel
    superseded_assignment: AssignmentModel | None
    assignment_key: str
    attempt_id: str
    criteria_refs: list[EvidenceRef]
    consumes: list[EvidenceRef | NodeRuntimeFileRef]
    paths: TaskRootPaths
    transient_refs: tuple[EvidenceRef, ...]


async def _child_node_for_assignment(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    child_node_key: str,
    parent_flow_node_id: str,
) -> FlowNodeModel:
    child_node = await flow_node_by_key(
        session,
        flow_revision_id,
        child_node_key,
    )
    if child_node.parent_flow_node_id != parent_flow_node_id:
        raise illegal_target_relation_error("assign_child target must be a direct child")
    return child_node


async def _persist_child_attempt(
    session: AsyncSession,
    task_id: str,
    *,
    assignment: AssignmentModel,
    attempt_id: str,
    child_node_key: str,
    criteria_refs: list[EvidenceRef],
    consumes: list[EvidenceRef | NodeRuntimeFileRef],
) -> None:
    session.add(
        AttemptModel(
            attempt_id=attempt_id,
            assignment_id=assignment.assignment_id,
            assignment_key=assignment.assignment_key,
            flow_node_id=assignment.flow_node_id,
            task_id=task_id,
            node_key=child_node_key,
            status="pending",
        )
    )
    await session.flush()
    await persist_attempt_consumed_refs(
        session,
        attempt_id_value=attempt_id,
        consumed_refs=[*criteria_refs, *consumes],
    )


def _assignment_model(
    *,
    task_id: str,
    flow_id: str,
    flow_revision_id: str,
    flow_node_id: str,
    node_key: str,
    assignment_key: str,
    attempt_id: str,
    dispatch_id: str,
    typed_call: AssignChildToolCall,
    criteria_refs: list[EvidenceRef],
    consumes: list[EvidenceRef | NodeRuntimeFileRef],
    transient_refs: tuple[EvidenceRef, ...],
    produces_json: list[dict[str, object]],
) -> AssignmentModel:
    assign_payload = typed_call.payload
    assignment = AssignmentModel(
        assignment_id=assignment_id(assignment_key),
        task_id=task_id,
        flow_id=flow_id,
        flow_revision_id=flow_revision_id,
        flow_node_id=flow_node_id,
        assignment_key=assignment_key,
        node_key=node_key,
        summary=assign_payload.assignment_intent.summary,
        instruction=assign_payload.assignment_intent.instruction,
        criteria_json=[ref.model_dump(mode="json") for ref in criteria_refs],
        consumes_json=[ref.model_dump(mode="json") for ref in consumes],
        produces_json=produces_json,
        transient_refs_json=[ref.model_dump(mode="json") for ref in transient_refs],
        task_memory_search_hints_json=list(assign_payload.task_memory_search_hints),
        current_attempt_id=attempt_id,
        created_by_dispatch_id=dispatch_id,
    )
    return assignment


async def _prepare_child_assignment(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    typed_call: AssignChildToolCall,
    active_flow_revision_id: str,
) -> PreparedChildAssignment:
    child_node = await _child_node_for_assignment(
        session,
        flow_revision_id=active_flow_revision_id,
        child_node_key=typed_call.payload.child_node_key,
        parent_flow_node_id=state.current_node.flow_node_id,
    )
    await consume_assignment_budget(
        session,
        budget_family="child_assignment",
        limit_field="child_assignment_limit",
        policy_key=state.current_node.policy_key,
        policy_revision_no=state.current_node.policy_revision_no,
        flow_id=state.flow.flow_id,
        flow_node_id=state.current_node.flow_node_id,
        assignment_id=state.current_assignment.assignment_id,
        attempt_id=state.current_assignment.current_attempt_id,
    )
    superseded_assignment = await load_superseded_child_assignment(session, child_node=child_node)
    attempt_seq = await next_node_sequence_number(
        session,
        AttemptModel,
        task_id,
        child_node.node_key,
    )
    criteria_refs, consumes = await resolve_assign_child_dependency_refs(
        session,
        task_id=task_id,
        child_node=child_node,
        flow_revision_id=active_flow_revision_id,
        typed_call=typed_call,
    )
    paths = await load_task_root_paths(session, task_id)
    transient_refs = planned_transient_refs(
        child_node=child_node,
        typed_call=typed_call,
        task_root_paths=paths,
    )
    queue_transient_surface_copies(
        session,
        typed_call=typed_call,
        transient_refs=transient_refs,
    )
    return PreparedChildAssignment(
        child_node=child_node,
        superseded_assignment=superseded_assignment,
        assignment_key=assignment_key_for_task(task_id, child_node.node_key, attempt_seq),
        attempt_id=attempt_id_for_task(task_id, child_node.node_key, attempt_seq),
        criteria_refs=criteria_refs,
        consumes=consumes,
        paths=paths,
        transient_refs=transient_refs,
    )


async def _stage_prepared_child_assignment(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: AssignChildToolCall,
    active_flow_revision_id: str,
    prepared: PreparedChildAssignment,
) -> AssignmentModel:
    assignment = _assignment_model(
        task_id=task_id,
        flow_id=state.flow.flow_id,
        flow_revision_id=active_flow_revision_id,
        flow_node_id=prepared.child_node.flow_node_id,
        node_key=prepared.child_node.node_key,
        assignment_key=prepared.assignment_key,
        attempt_id=prepared.attempt_id,
        dispatch_id=dispatch.dispatch_id,
        typed_call=typed_call,
        criteria_refs=prepared.criteria_refs,
        consumes=prepared.consumes,
        transient_refs=prepared.transient_refs,
        produces_json=_artifact_requirements(prepared.child_node),
    )
    if (
        prepared.superseded_assignment is not None
        and prepared.superseded_assignment.superseded_at is None
    ):
        prepared.superseded_assignment.superseded_at = utc_now()
    prepared.child_node.current_assignment_id = assignment.assignment_id
    session.add(assignment)
    await session.flush()
    await persist_assignment_criteria_refs(
        session,
        assignment_id_value=assignment.assignment_id,
        criteria_refs=prepared.criteria_refs,
    )
    await _persist_child_attempt(
        session,
        task_id,
        assignment=assignment,
        attempt_id=prepared.attempt_id,
        child_node_key=prepared.child_node.node_key,
        criteria_refs=prepared.criteria_refs,
        consumes=prepared.consumes,
    )
    dispatch.staged_child_assignment_id = assignment.assignment_id
    dispatch.staged_continuation_kind = "child_assignment"
    await session.flush()
    queue_attempt_materialization(session, task_id=task_id, attempt_id=prepared.attempt_id)
    queue_manifest_materialization(session, task_id=task_id)
    return assignment


async def _assign_child_success(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    assignment: AssignmentModel,
    prepared: PreparedChildAssignment,
) -> AssignChildSuccess:
    return AssignChildSuccess(
        summary=f"Staged child assignment for '{prepared.child_node.node_key}'.",
        target_node_key=prepared.child_node.node_key,
        target_assignment_key=assignment.assignment_key,
        target_attempt_id=prepared.attempt_id,
        child_assignment_ref=AssignmentFileRef(
            path=prepared.paths.attempts_path / prepared.attempt_id / "assignment.md",
            description=f"Current assignment for child node '{prepared.child_node.node_key}'.",
        ),
        flow=await runtime_flow_read(session, task_id),
        workflow_manifest_ref=WorkflowManifestRef(
            path=prepared.paths.runtime_path / "workflow-manifest.md",
            description="Whole-workflow visible contract for the current task.",
        ),
        latest_checkpoint_ref=latest_checkpoint_ref(
            attempt_id=state.current_attempt.attempt_id,
            latest_checkpoint_id=state.current_attempt.latest_checkpoint_id,
            task_root_paths=prepared.paths,
        ),
    )


async def call_assign_child(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: AssignChildToolCall,
) -> AssignChildSuccess:
    ensure_no_staged_child_assignment(dispatch, action_name="assign_child")
    active_flow_revision_id = state.flow.active_flow_revision_id
    if active_flow_revision_id is None:
        raise illegal_state_error("missing active flow revision")
    prepared = await _prepare_child_assignment(
        session,
        task_id,
        state=state,
        typed_call=typed_call,
        active_flow_revision_id=active_flow_revision_id,
    )
    assignment = await _stage_prepared_child_assignment(
        session,
        task_id,
        state=state,
        dispatch=dispatch,
        typed_call=typed_call,
        active_flow_revision_id=active_flow_revision_id,
        prepared=prepared,
    )
    return await _assign_child_success(
        session,
        task_id,
        state=state,
        assignment=assignment,
        prepared=prepared,
    )


__all__ = ["call_assign_child"]
