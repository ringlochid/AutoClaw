from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import insert, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    AssignmentDecisionModel,
    AssignmentModel,
    AttemptModel,
    FlowNodeModel,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import (
    AssignChildSuccess,
    ReleaseBlockedSuccess,
    ReleaseGreenSuccess,
)
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime.dispatch.authority import (
    NodeOperationAuthority,
    exact_node_operation_authority_exists,
)
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.launch.bootstrap.criteria import stage_assignment_criteria_refs
from autoclaw.runtime.node_operations.contracts import (
    AssignChildRequest,
    NodeOperationName,
    ReleaseRequest,
)
from autoclaw.runtime.node_operations.release import (
    add_release_basis_rows,
    require_release_blocked_basis,
    require_release_green_basis,
)
from autoclaw.runtime.node_operations.result_reads import runtime_flow_read


async def execute_structural_node_operation(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    operation_name: NodeOperationName,
    request: BaseModel,
) -> BaseModel:
    if operation_name == NodeOperationName.ASSIGN_CHILD:
        assert isinstance(request, AssignChildRequest)
        return await _assign_child(session, authority, request)
    if operation_name in {
        NodeOperationName.ADD_CHILD,
        NodeOperationName.UPDATE_CHILD,
        NodeOperationName.REMOVE_CHILD,
    }:
        from autoclaw.runtime.node_operations.structural_revisions import (
            adopt_structural_revision,
        )

        return await adopt_structural_revision(
            session,
            authority,
            operation_name,
            request,
        )
    if operation_name == NodeOperationName.RELEASE_GREEN:
        assert isinstance(request, ReleaseRequest)
        return await _record_release(session, authority, request, blocked=False)
    if operation_name == NodeOperationName.RELEASE_BLOCKED:
        assert isinstance(request, ReleaseRequest)
        return await _record_release(session, authority, request, blocked=True)
    raise RuntimeOperationError(
        code=OperationFailureCode.INVALID_REQUEST_SHAPE,
        summary=f"unsupported Node operation '{operation_name.value}'",
        is_retryable=False,
    )


async def _assign_child(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    request: AssignChildRequest,
) -> AssignChildSuccess:
    _require_expected_revision(authority, request.expected_structural_revision_id)
    await _require_no_staged_decision(session, authority)

    target = await _read_unassigned_direct_child(session, authority, request)
    assignment, attempt = _build_child_assignment(authority, request, target)
    await _claim_child_node(session, authority, target, assignment.assignment_id)

    session.add_all((assignment, attempt))
    stage_assignment_criteria_refs(session, assignment)
    _stage_child_assignment_decision(session, authority, assignment, attempt)
    await session.commit()

    flow = await runtime_flow_read(session, authority)
    return AssignChildSuccess(
        summary="Child assignment staged for a later yield boundary.",
        target_node_key=target.node_key,
        target_assignment_key=assignment.assignment_key,
        target_attempt_id=attempt.attempt_id,
        flow=flow,
        workflow_manifest_ref=flow.workflow_manifest_ref,
    )


async def _read_unassigned_direct_child(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    request: AssignChildRequest,
) -> FlowNodeModel:
    target = await session.scalar(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == authority.flow_revision_id,
            FlowNodeModel.node_key == request.payload.child_node_key,
            FlowNodeModel.parent_node_key == authority.node_key,
        )
    )
    if target is None:
        raise RuntimeOperationError(
            code=OperationFailureCode.ILLEGAL_TARGET_RELATION,
            summary="assign_child must target one direct child of the current node",
            is_retryable=False,
        )
    if target.current_assignment_id is not None:
        raise RuntimeOperationError(
            code=OperationFailureCode.CONFLICT,
            summary="the target child already has a current assignment",
            is_retryable=False,
        )
    return target


def _build_child_assignment(
    authority: NodeOperationAuthority,
    request: AssignChildRequest,
    target: FlowNodeModel,
) -> tuple[AssignmentModel, AttemptModel]:
    suffix = uuid4().hex
    assignment_id = f"assignment.{authority.task_id}.{target.node_key}.{suffix}"
    attempt_id = f"attempt.{authority.task_id}.{target.node_key}.{suffix}"
    assignment = AssignmentModel(
        assignment_id=assignment_id,
        task_id=authority.task_id,
        flow_id=authority.flow_id,
        flow_revision_id=authority.flow_revision_id,
        flow_node_id=target.flow_node_id,
        assignment_key=f"{authority.task_id}.{target.node_key}.{suffix}",
        node_key=target.node_key,
        parent_assignment_id=authority.assignment_id,
        summary=request.payload.assignment_intent.summary,
        instruction=request.payload.assignment_intent.instruction,
        criteria_json=list(target.criteria_json),
        consumes_json=_flatten_slots(target.consumes_json),
        produces_json=_flatten_slots(target.produces_json),
        current_attempt_id=attempt_id,
        work_plan_revision=0,
        created_by_dispatch_id=authority.dispatch_id,
    )
    attempt = AttemptModel(
        attempt_id=attempt_id,
        assignment_id=assignment_id,
        task_id=authority.task_id,
        flow_id=authority.flow_id,
        node_key=target.node_key,
        retry_of_attempt_id=None,
        status="pending",
    )
    return assignment, attempt


async def _claim_child_node(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    target: FlowNodeModel,
    assignment_id: str,
) -> None:
    updated_node = await session.scalar(
        update(FlowNodeModel)
        .where(
            FlowNodeModel.flow_node_id == target.flow_node_id,
            FlowNodeModel.current_assignment_id.is_(None),
            exact_node_operation_authority_exists(authority),
        )
        .values(current_assignment_id=assignment_id, state="waiting")
        .returning(FlowNodeModel.flow_node_id)
    )
    if updated_node is None:
        raise RuntimeOperationError(
            code=OperationFailureCode.CONFLICT,
            summary="another child assignment won the target node",
            is_retryable=False,
        )


def _stage_child_assignment_decision(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    assignment: AssignmentModel,
    attempt: AttemptModel,
) -> None:
    session.add(
        AssignmentDecisionModel(
            assignment_decision_id=f"assignment-decision.{authority.dispatch_id}",
            source_dispatch_id=authority.dispatch_id,
            task_id=authority.task_id,
            flow_id=authority.flow_id,
            assignment_id=authority.assignment_id,
            attempt_id=authority.attempt_id,
            source_flow_revision_id=authority.flow_revision_id,
            decision_kind="staged_child",
            staged_child_assignment_id=assignment.assignment_id,
            staged_child_attempt_id=attempt.attempt_id,
        )
    )


async def _record_release(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    request: ReleaseRequest,
    *,
    blocked: bool,
) -> ReleaseGreenSuccess | ReleaseBlockedSuccess:
    _require_expected_revision(authority, request.expected_structural_revision_id)
    await _require_no_staged_decision(session, authority)
    decision_kind = "release_blocked" if blocked else "release_green"
    basis = (
        await require_release_blocked_basis(session, authority)
        if blocked
        else await require_release_green_basis(session, authority)
    )
    decision_id = f"assignment-decision.{authority.dispatch_id}"
    await _insert_release_decision_if_current(
        session,
        authority,
        assignment_decision_id=decision_id,
        decision_kind=decision_kind,
    )
    add_release_basis_rows(
        session,
        authority=authority,
        assignment_decision_id=decision_id,
        basis=basis,
    )
    await session.commit()
    flow = await runtime_flow_read(session, authority)
    result_type = ReleaseBlockedSuccess if blocked else ReleaseGreenSuccess
    return result_type(
        summary=f"Recorded {decision_kind} readiness for the current assignment.",
        target_node_key=authority.node_key,
        flow=flow,
        workflow_manifest_ref=flow.workflow_manifest_ref,
    )


async def _insert_release_decision_if_current(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    *,
    assignment_decision_id: str,
    decision_kind: str,
) -> None:
    table = AssignmentDecisionModel.__table__
    inserted_id = await session.scalar(
        insert(AssignmentDecisionModel)
        .from_select(
            (
                "assignment_decision_id",
                "source_dispatch_id",
                "task_id",
                "flow_id",
                "assignment_id",
                "attempt_id",
                "source_flow_revision_id",
                "decision_kind",
                "staged_child_assignment_id",
                "staged_child_attempt_id",
                "recorded_at",
            ),
            select(
                literal(assignment_decision_id),
                literal(authority.dispatch_id),
                literal(authority.task_id),
                literal(authority.flow_id),
                literal(authority.assignment_id),
                literal(authority.attempt_id),
                literal(authority.flow_revision_id),
                literal(decision_kind),
                literal(None, type_=table.c.staged_child_assignment_id.type),
                literal(None, type_=table.c.staged_child_attempt_id.type),
                literal(utc_now(), type_=table.c.recorded_at.type),
            ).where(exact_node_operation_authority_exists(authority)),
        )
        .returning(table.c.assignment_decision_id)
    )
    if inserted_id is None:
        raise RuntimeOperationError(
            code=OperationFailureCode.CONFLICT,
            summary="another transition changed current release authority",
            is_retryable=False,
        )


async def _require_no_staged_decision(
    session: AsyncSession,
    authority: NodeOperationAuthority,
) -> None:
    existing = await session.scalar(
        select(AssignmentDecisionModel.assignment_decision_id).where(
            AssignmentDecisionModel.source_dispatch_id == authority.dispatch_id
        )
    )
    if existing is not None:
        raise RuntimeOperationError(
            code=OperationFailureCode.CONFLICTING_CONTINUATION,
            summary="the current dispatch already owns a staged continuation decision",
            is_retryable=False,
        )


def _require_expected_revision(
    authority: NodeOperationAuthority,
    expected_revision: str,
) -> None:
    if expected_revision != authority.flow_revision_id:
        raise RuntimeOperationError(
            code=OperationFailureCode.STALE_FLOW_REVISION,
            summary="the structural revision changed before this operation",
            is_retryable=True,
        )


def _flatten_slots(value: dict[str, object] | None) -> list[dict[str, object]]:
    if value is None:
        return []
    flattened: list[dict[str, object]] = []
    for kind, entries in value.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                flattened.append({"kind": kind.removesuffix("s"), **entry})
    return flattened


__all__ = ["execute_structural_node_operation"]
