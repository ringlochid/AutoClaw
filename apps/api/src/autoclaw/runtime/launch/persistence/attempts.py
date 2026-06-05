from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptConsumedRefModel,
    AttemptModel,
    AttemptProducedRefModel,
)
from autoclaw.runtime.contracts import (
    CheckpointProjection,
    EvidenceRef,
    NodeRuntimeFileRef,
    RuntimeBootstrapProjectionInput,
    RuntimeBootstrapResult,
)
from autoclaw.runtime.ids import (
    artifact_publication_id,
    assignment_id,
    attempt_consumed_ref_id,
    flow_node_id,
)
from autoclaw.runtime.launch.bootstrap.criteria import stage_assignment_criteria_refs


async def stage_launch_attempt_rows(
    session: AsyncSession,
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    result: RuntimeBootstrapResult,
    flow_id: str,
) -> None:
    latest_checkpoint = result.latest_checkpoint
    checkpoint_id = (
        _bootstrap_checkpoint_id(bootstrap_input.attempt_id)
        if latest_checkpoint is not None
        else None
    )
    assignment_row = _build_assignment_row(
        bootstrap_input=bootstrap_input,
        result=result,
        flow_id=flow_id,
    )
    session.add(assignment_row)
    await session.flush()
    stage_assignment_criteria_refs(session, assignment_row)

    session.add(
        _build_attempt_row(
            bootstrap_input=bootstrap_input,
            assignment_row=assignment_row,
            node_key=result.assignment.node_key,
            checkpoint_id=checkpoint_id,
        )
    )
    await session.flush()

    _stage_consumed_refs(
        session,
        attempt_id=bootstrap_input.attempt_id,
        refs=(
            *result.assignment.criteria,
            *result.assignment.consumes,
        ),
    )

    if latest_checkpoint is not None:
        assert checkpoint_id is not None
        session.add(
            _build_checkpoint_row(
                checkpoint_id=checkpoint_id,
                attempt_id=bootstrap_input.attempt_id,
                assignment_row=assignment_row,
                node_key=result.assignment.node_key,
                latest_checkpoint=latest_checkpoint,
            )
        )
        _stage_produced_artifact_refs(
            session,
            attempt_id=bootstrap_input.attempt_id,
            assignment_row=assignment_row,
            owner_node_key=result.assignment.node_key,
            produced_artifacts=latest_checkpoint.produced_artifacts,
        )

    await session.flush()


def _bootstrap_checkpoint_id(attempt_id: str) -> str:
    return f"checkpoint.{attempt_id}.01"


def _consume_json(ref: EvidenceRef | NodeRuntimeFileRef) -> dict[str, Any]:
    return ref.model_dump(mode="json")


def _build_assignment_row(
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
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
        summary=result.assignment.summary,
        instruction=result.assignment.instruction,
        criteria_json=[ref.model_dump(mode="json") for ref in result.assignment.criteria],
        consumes_json=[_consume_json(ref) for ref in result.assignment.consumes],
        produces_json=[req.model_dump(mode="json") for req in result.assignment.produces],
        transient_refs_json=[
            ref.model_dump(mode="json") for ref in result.assignment.transient_refs
        ],
        task_memory_search_hints_json=list(result.assignment.task_memory_search_hints),
        current_attempt_id=bootstrap_input.attempt_id,
        created_by_dispatch_id=None,
    )


def _build_attempt_row(
    *,
    bootstrap_input: RuntimeBootstrapProjectionInput,
    assignment_row: AssignmentModel,
    node_key: str,
    checkpoint_id: str | None,
) -> AttemptModel:
    return AttemptModel(
        attempt_id=bootstrap_input.attempt_id,
        assignment_id=assignment_row.assignment_id,
        assignment_key=assignment_row.assignment_key,
        flow_node_id=assignment_row.flow_node_id,
        task_id=bootstrap_input.task_id,
        node_key=node_key,
        status="running",
        latest_checkpoint_id=checkpoint_id,
    )


def _stage_consumed_refs(
    session: AsyncSession,
    *,
    attempt_id: str,
    refs: tuple[EvidenceRef | NodeRuntimeFileRef, ...],
) -> None:
    for index, ref in enumerate(refs, start=1):
        session.add(
            AttemptConsumedRefModel(
                attempt_consumed_ref_id=attempt_consumed_ref_id(attempt_id, index),
                attempt_id=attempt_id,
                ref_kind=ref.kind.value,
                slot=getattr(ref, "slot", None),
                version=getattr(ref, "version", None),
                path=str(ref.path),
                description=ref.description,
                order_index=index,
            )
        )


def _build_checkpoint_row(
    *,
    checkpoint_id: str,
    attempt_id: str,
    assignment_row: AssignmentModel,
    node_key: str,
    latest_checkpoint: CheckpointProjection,
) -> AttemptCheckpointModel:
    produced_artifacts = latest_checkpoint.produced_artifacts
    return AttemptCheckpointModel(
        checkpoint_id=checkpoint_id,
        assignment_id=assignment_row.assignment_id,
        assignment_key=assignment_row.assignment_key,
        attempt_id=attempt_id,
        flow_node_id=assignment_row.flow_node_id,
        node_key=node_key,
        checkpoint_kind=latest_checkpoint.checkpoint_kind.value,
        outcome=latest_checkpoint.outcome.value if latest_checkpoint.outcome else None,
        summary=latest_checkpoint.handoff.summary,
        next_step=latest_checkpoint.handoff.next_step,
        blockers_json=list(latest_checkpoint.handoff.blockers),
        risks_json=list(latest_checkpoint.handoff.risks),
        produced_artifact_claims_json=[
            {
                "kind": "artifact",
                "slot": ref.slot,
                "path": str(ref.path),
            }
            for ref in produced_artifacts
        ],
        produced_artifacts_json=[ref.model_dump(mode="json") for ref in produced_artifacts],
        artifact_refs_json=[ref.model_dump(mode="json") for ref in produced_artifacts],
        transient_refs_json=[
            ref.model_dump(mode="json") for ref in latest_checkpoint.transient_refs
        ],
        task_memory_search_hints_json=list(latest_checkpoint.task_memory_search_hints),
    )


def _stage_produced_artifact_refs(
    session: AsyncSession,
    *,
    attempt_id: str,
    assignment_row: AssignmentModel,
    owner_node_key: str,
    produced_artifacts: tuple[EvidenceRef, ...],
) -> None:
    for index, artifact_ref in enumerate(produced_artifacts, start=1):
        slot = artifact_ref.slot or f"artifact-{index}"
        version = artifact_ref.version or index
        session.add(
            AttemptProducedRefModel(
                attempt_produced_ref_id=artifact_publication_id(
                    attempt_id,
                    slot,
                    version,
                ),
                attempt_id=attempt_id,
                owner_node_key=owner_node_key,
                assignment_key=assignment_row.assignment_key,
                slot=slot,
                version=version,
                path=str(artifact_ref.path),
                description=artifact_ref.description,
                became_current=True,
                order_index=index,
            )
        )
