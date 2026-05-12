from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from app.db.models import (
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptConsumedRefModel,
    FlowNodeModel,
)
from app.runtime.contracts import (
    AssignmentProjection,
    CheckpointHandoff,
    CheckpointKind,
    CheckpointOutcome,
    CheckpointProjection,
    EvidenceRef,
    NodeKind,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    ProduceRequirement,
    ResolvedNodeContext,
    RuntimeContextRef,
)

_NODE_RUNTIME_FILE_KIND_VALUES = frozenset(member.value for member in NodeRuntimeFileKind)


def json_mapping(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload or {})


def json_list(payload: object) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], payload or [])


def int_or_none(value: object) -> int | None:
    return int(value) if isinstance(value, int | str) else None


def sorted_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def runtime_context_ref_from_json(payload: dict[str, object]) -> RuntimeContextRef:
    kind = payload.get("kind")
    if isinstance(kind, str) and kind in _NODE_RUNTIME_FILE_KIND_VALUES:
        return NodeRuntimeFileRef.model_validate(
            {
                "kind": kind,
                "path": payload["path"],
                "description": payload["description"],
            }
        )
    return EvidenceRef.model_validate(payload)


def assignment_projection_from_model(model: AssignmentModel) -> AssignmentProjection:
    return AssignmentProjection(
        assignment_key=model.assignment_key,
        node_key=model.node_key,
        summary=model.summary,
        instruction=model.instruction,
        criteria=tuple(EvidenceRef.model_validate(item) for item in model.criteria_json),
        consumes=tuple(runtime_context_ref_from_json(item) for item in model.consumes_json),
        produces=tuple(ProduceRequirement.model_validate(item) for item in model.produces_json),
        transient_refs=tuple(
            EvidenceRef.model_validate(item) for item in model.transient_refs_json
        ),
        task_memory_search_hints=tuple(model.task_memory_search_hints_json),
    )


def runtime_context_ref_from_attempt_consumed_model(
    model: AttemptConsumedRefModel,
) -> RuntimeContextRef:
    return runtime_context_ref_from_json(
        {
            "kind": model.ref_kind,
            "slot": model.slot,
            "version": model.version,
            "path": Path(model.path),
            "description": model.description,
        }
    )


def checkpoint_projection_from_model(model: AttemptCheckpointModel) -> CheckpointProjection:
    return CheckpointProjection(
        checkpoint_kind=CheckpointKind(model.checkpoint_kind),
        outcome=None if model.outcome is None else CheckpointOutcome(model.outcome),
        handoff=CheckpointHandoff(
            summary=model.summary,
            next_step=model.next_step,
            blockers=tuple(model.blockers_json),
            risks=tuple(model.risks_json),
        ),
        produced_artifacts=tuple(
            EvidenceRef.model_validate(item) for item in model.produced_artifacts_json
        ),
        transient_refs=tuple(
            EvidenceRef.model_validate(item) for item in model.transient_refs_json
        ),
        task_memory_search_hints=tuple(model.task_memory_search_hints_json),
    )


def resolved_node_context(node: FlowNodeModel) -> ResolvedNodeContext:
    return ResolvedNodeContext(
        node_key=node.node_key,
        node_kind=NodeKind(node.structural_kind),
        node_description=node.description,
        role_key=node.role_key,
        role_revision_no=node.role_revision_no,
        role_description=node.role_description,
        role_instruction=node.role_instruction,
        policy_key=node.policy_key,
        policy_revision_no=node.policy_revision_no,
        policy_description=node.policy_description,
        policy_instruction=node.policy_instruction,
    )


def criteria_markdown(criteria: dict[str, Any]) -> str:
    lines = [f"# {criteria['slot']}", "", str(criteria["description"]), ""]
    lines.extend(f"- {item}" for item in cast(list[str], criteria.get("criteria", [])))
    return "\n".join(lines).rstrip() + "\n"
