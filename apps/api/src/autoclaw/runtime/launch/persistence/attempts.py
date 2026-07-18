from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import AssignmentModel, AttemptModel
from autoclaw.runtime.contracts import (
    EvidenceRef,
    NodeRuntimeFileRef,
    RuntimeBootstrapInput,
    RuntimeBootstrapResult,
)
from autoclaw.runtime.ids import assignment_id, flow_node_id
from autoclaw.runtime.launch.bootstrap.criteria import stage_assignment_criteria_refs


async def stage_launch_attempt_rows(
    session: AsyncSession,
    *,
    bootstrap_input: RuntimeBootstrapInput,
    result: RuntimeBootstrapResult,
    flow_id: str,
) -> None:
    """Stage the initial target assignment and attempt for a fresh task."""

    assignment_row = _build_assignment_row(
        bootstrap_input=bootstrap_input,
        result=result,
        flow_id=flow_id,
    )
    session.add(assignment_row)
    await session.flush()
    stage_assignment_criteria_refs(session, assignment_row)

    session.add(
        AttemptModel(
            attempt_id=bootstrap_input.attempt_id,
            assignment_id=assignment_row.assignment_id,
            task_id=bootstrap_input.task_id,
            flow_id=flow_id,
            node_key=result.assignment.node_key,
            retry_of_attempt_id=None,
            status="running",
        )
    )
    await session.flush()


def _build_assignment_row(
    *,
    bootstrap_input: RuntimeBootstrapInput,
    result: RuntimeBootstrapResult,
    flow_id: str,
) -> AssignmentModel:
    return AssignmentModel(
        assignment_id=assignment_id(result.assignment.assignment_key),
        task_id=bootstrap_input.task_id,
        flow_id=flow_id,
        flow_revision_id=bootstrap_input.active_flow_revision_id,
        flow_node_id=flow_node_id(
            bootstrap_input.active_flow_revision_id,
            result.assignment.node_key,
        ),
        assignment_key=result.assignment.assignment_key,
        node_key=result.assignment.node_key,
        parent_assignment_id=None,
        summary=result.assignment.summary,
        instruction=result.assignment.instruction,
        criteria_json=[ref.model_dump(mode="json") for ref in result.assignment.criteria],
        consumes_json=[_ref_json(ref) for ref in result.assignment.consumes],
        produces_json=[
            requirement.model_dump(mode="json") for requirement in result.assignment.produces
        ],
        current_attempt_id=bootstrap_input.attempt_id,
        created_by_dispatch_id=None,
    )


def _ref_json(ref: EvidenceRef | NodeRuntimeFileRef) -> dict[str, Any]:
    return ref.model_dump(mode="json")


__all__ = ["stage_launch_attempt_rows"]
