from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import cast
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import insert, literal, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    AcceptedBoundaryModel,
    AssignmentDecisionModel,
    AttemptCheckpointModel,
    AttemptModel,
)
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import (
    BoundaryRead,
    CheckpointFileRef,
    CheckpointRead,
)
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime.dispatch.authority import (
    NodeOperationAuthority,
    exact_node_operation_authority_exists,
)
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.node_operations.contracts import (
    NodeOperationName,
    OpenHumanRequestRequest,
    RecordCheckpointRequest,
    ReturnBoundaryRequest,
    StartCommandRunRequest,
)
from autoclaw.runtime.node_operations.external_wait_handlers import (
    open_human_request,
    start_command_run,
)
from autoclaw.runtime.node_operations.result_reads import runtime_flow_read
from autoclaw.runtime.node_operations.source_transitions import close_source_dispatch


async def execute_controller_node_operation(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    operation_name: NodeOperationName,
    request: BaseModel,
) -> BaseModel:
    if operation_name == NodeOperationName.RECORD_CHECKPOINT:
        assert isinstance(request, RecordCheckpointRequest)
        return await _record_checkpoint(session, authority, request)
    if operation_name == NodeOperationName.RETURN_BOUNDARY:
        assert isinstance(request, ReturnBoundaryRequest)
        return await _return_boundary(session, authority, request)
    if operation_name == NodeOperationName.OPEN_HUMAN_REQUEST:
        assert isinstance(request, OpenHumanRequestRequest)
        return await open_human_request(session, authority, request)
    if operation_name == NodeOperationName.START_COMMAND_RUN:
        assert isinstance(request, StartCommandRunRequest)
        return await start_command_run(session, authority, request)

    from autoclaw.runtime.node_operations.structural_handlers import (
        execute_structural_node_operation,
    )

    return await execute_structural_node_operation(
        session,
        authority,
        operation_name,
        request,
    )


async def _record_checkpoint(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    request: RecordCheckpointRequest,
) -> CheckpointRead:
    body = request.checkpoint
    if body.produced_artifacts or body.transient_surfaces:
        raise RuntimeOperationError(
            code=OperationFailureCode.ILLEGAL_STATE,
            summary=(
                "artifact and transient checkpoint claims are unavailable until the "
                "publication protocol is active"
            ),
            is_retryable=False,
        )
    checkpoint_id = f"checkpoint.{authority.attempt_id}.{uuid4().hex}"
    evidence: dict[str, object] = {
        "next_step": body.handoff.next_step,
        "blockers": list(body.handoff.blockers),
        "risks": list(body.handoff.risks),
    }
    try:
        await _insert_checkpoint_if_current(
            session,
            authority,
            checkpoint_id=checkpoint_id,
            checkpoint_kind=body.checkpoint_kind.value,
            outcome=body.outcome.value if body.outcome is not None else None,
            summary=body.handoff.summary,
            evidence=evidence,
        )
        await session.commit()
    except IntegrityError as exc:
        if not _is_terminal_checkpoint_conflict(exc):
            raise
        await session.rollback()
        raise RuntimeOperationError(
            code=OperationFailureCode.CONFLICT,
            summary="another terminal checkpoint won the source dispatch",
            is_retryable=False,
        ) from exc
    checkpoint_ref = CheckpointFileRef(
        path=Path(f"_runtime/attempts/{authority.attempt_id}/latest-checkpoint.md"),
        description="Latest checkpoint projection for the current attempt.",
    )
    return CheckpointRead(
        attempt_id=authority.attempt_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ref=checkpoint_ref,
        latest_checkpoint_ref=checkpoint_ref,
    )


async def _insert_checkpoint_if_current(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    *,
    checkpoint_id: str,
    checkpoint_kind: str,
    outcome: str | None,
    summary: str,
    evidence: dict[str, object],
) -> None:
    table = AttemptCheckpointModel.__table__
    inserted_id = await session.scalar(
        insert(AttemptCheckpointModel)
        .from_select(
            (
                "checkpoint_id",
                "task_id",
                "flow_id",
                "assignment_id",
                "attempt_id",
                "authoring_dispatch_id",
                "checkpoint_kind",
                "outcome",
                "summary",
                "evidence_json",
                "criteria_results_json",
                "recorded_at",
            ),
            select(
                literal(checkpoint_id),
                literal(authority.task_id),
                literal(authority.flow_id),
                literal(authority.assignment_id),
                literal(authority.attempt_id),
                literal(authority.dispatch_id),
                literal(checkpoint_kind),
                literal(outcome, type_=table.c.outcome.type),
                literal(summary),
                literal(evidence, type_=table.c.evidence_json.type),
                literal([], type_=table.c.criteria_results_json.type),
                literal(utc_now(), type_=table.c.recorded_at.type),
            ).where(exact_node_operation_authority_exists(authority)),
        )
        .returning(table.c.checkpoint_id)
    )
    if inserted_id is None:
        raise RuntimeOperationError(
            code=OperationFailureCode.CONFLICT,
            summary="another transition changed current checkpoint authority",
            is_retryable=False,
        )


async def _return_boundary(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    request: ReturnBoundaryRequest,
) -> BoundaryRead:
    outcome = request.boundary.value
    checkpoint = await _latest_checkpoint(session, authority)
    if outcome != "yield" and (checkpoint is None or checkpoint.outcome != outcome):
        raise RuntimeOperationError(
            code=OperationFailureCode.BOUNDARY_PRECONDITION_FAILED,
            summary=f"{outcome} requires a matching terminal checkpoint",
            is_retryable=False,
        )
    decision = await session.scalar(
        select(AssignmentDecisionModel).where(
            AssignmentDecisionModel.source_dispatch_id == authority.dispatch_id
        )
    )
    _validate_boundary_decision(authority, outcome, decision)
    now = utc_now()
    await close_source_dispatch(
        session,
        authority,
        now=now,
        closed_reason="boundary",
        waiting_cause="none",
        waiting_source_id=None,
    )
    session.add(
        AcceptedBoundaryModel(
            accepted_boundary_id=f"accepted-boundary.{authority.dispatch_id}",
            source_dispatch_id=authority.dispatch_id,
            task_id=authority.task_id,
            flow_id=authority.flow_id,
            assignment_id=authority.assignment_id,
            attempt_id=authority.attempt_id,
            outcome=outcome,
            checkpoint_id=checkpoint.checkpoint_id if checkpoint is not None else None,
            assignment_decision_id=(
                decision.assignment_decision_id if decision is not None else None
            ),
        )
    )
    if outcome != "yield":
        await session.execute(
            update(AttemptModel)
            .where(
                AttemptModel.attempt_id == authority.attempt_id,
                AttemptModel.assignment_id == authority.assignment_id,
                AttemptModel.status.in_(("pending", "running")),
            )
            .values(status="completed", terminal_outcome=outcome, closed_at=now)
        )
    await session.commit()
    flow = await runtime_flow_read(session, authority)
    checkpoint_ref = (
        CheckpointFileRef(
            path=Path(f"_runtime/attempts/{authority.attempt_id}/latest-checkpoint.md"),
            description="Latest checkpoint projection for the source attempt.",
        )
        if checkpoint is not None
        else None
    )
    return BoundaryRead(
        accepted_boundary=request.boundary,
        flow=flow,
        latest_checkpoint_ref=checkpoint_ref,
    )


async def _latest_checkpoint(
    session: AsyncSession,
    authority: NodeOperationAuthority,
) -> AttemptCheckpointModel | None:
    return cast(
        AttemptCheckpointModel | None,
        await session.scalar(
            select(AttemptCheckpointModel)
            .where(
                AttemptCheckpointModel.task_id == authority.task_id,
                AttemptCheckpointModel.assignment_id == authority.assignment_id,
                AttemptCheckpointModel.attempt_id == authority.attempt_id,
                AttemptCheckpointModel.authoring_dispatch_id == authority.dispatch_id,
            )
            .order_by(AttemptCheckpointModel.recorded_at.desc())
            .limit(1)
        ),
    )


def _validate_boundary_decision(
    authority: NodeOperationAuthority,
    outcome: str,
    decision: AssignmentDecisionModel | None,
) -> None:
    expected: str | None = None
    if outcome == "yield":
        expected = "staged_child"
    elif outcome == "green" and authority.node_kind.value in {"parent", "root"}:
        expected = "release_green"
    elif outcome == "blocked" and authority.node_kind.value == "root":
        expected = "release_blocked"
    elif outcome == "retry" and authority.node_kind.value != "worker":
        raise RuntimeOperationError(
            code=OperationFailureCode.ILLEGAL_CALLER,
            summary="only workers may return retry",
            is_retryable=False,
        )
    if expected is None:
        return
    if decision is None or decision.decision_kind != expected:
        raise RuntimeOperationError(
            code=OperationFailureCode.BOUNDARY_PRECONDITION_FAILED,
            summary=f"{outcome} requires a current {expected} decision",
            is_retryable=False,
        )


def _is_terminal_checkpoint_conflict(exc: IntegrityError) -> bool:
    original = exc.orig
    diagnostics = getattr(original, "diag", None)
    driver_cause = getattr(original, "__cause__", None)
    constraint_name = (
        getattr(diagnostics, "constraint_name", None)
        or getattr(original, "constraint_name", None)
        or getattr(driver_cause, "constraint_name", None)
    )
    if constraint_name == "uq_attempt_checkpoints_one_terminal_per_dispatch":
        return True
    return isinstance(original, sqlite3.IntegrityError) and (
        getattr(original, "sqlite_errorcode", None) == sqlite3.SQLITE_CONSTRAINT_UNIQUE
        and str(original) == "UNIQUE constraint failed: attempt_checkpoints.authoring_dispatch_id"
    )


__all__ = ["execute_controller_node_operation"]
