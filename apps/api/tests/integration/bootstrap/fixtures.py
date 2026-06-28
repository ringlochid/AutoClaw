from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from autoclaw.definitions.compiler import (
    MappingRolePolicyLookup,
    NormalizedCompiledPlan,
    PolicyRevisionDefinition,
    RoleRevisionDefinition,
    WorkflowRevisionMetadata,
    compile_workflow,
)
from autoclaw.definitions.contracts import (
    PolicyDefinitionFile,
    RoleDefinitionFile,
    WorkflowDefinitionFile,
)
from autoclaw.definitions.contracts.workflow import WorkflowDefinitionInput
from autoclaw.definitions.registry import compile_current_workflow_launch_snapshot
from autoclaw.definitions.seeds import resolve_packaged_seed_definitions_root
from autoclaw.persistence import (
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowNodeModel,
)
from autoclaw.runtime import (
    CheckpointKind,
    CheckpointProjection,
    PromptFamily,
    PromptSendMode,
    RuntimeBootstrapProjectionInput,
    RuntimeBootstrapResult,
    TaskComposeInput,
)
from autoclaw.runtime.ids import checkpoint_id, dispatch_id_for_task
from autoclaw.runtime.launch import persist_bootstrap_runtime_from_precomputed
from autoclaw.runtime.projection import current_runtime_state
from autoclaw.runtime.projection.manifest import (
    build_current_structural_edit_palette,
)
from sqlalchemy.ext.asyncio import AsyncSession

ROLE_REVISIONS = {
    "architect": 48,
    "bug_fix_engineer": 57,
    "bug_triage": 56,
    "code_reviewer": 58,
    "engineer": 44,
    "failure_analyst": 60,
    "planner": 47,
    "planning_lead": 42,
    "release_operator": 46,
    "replan_planner": 62,
    "researcher": 43,
    "reviewer": 45,
    "root_planning_lead": 41,
    "test_verifier": 59,
    "delivery_planner": 61,
}

POLICY_REVISIONS = {
    "standard-failure-analysis": 64,
    "standard-parent-planning": 52,
    "standard-release": 55,
    "standard-review": 54,
    "standard-root-planning": 51,
    "standard-verification": 63,
    "standard-worker": 53,
    "standard-delivery-planning": 65,
}


def load_seeded_lookup() -> MappingRolePolicyLookup:
    with resolve_packaged_seed_definitions_root() as definitions_root:
        roles = {
            role.id: RoleRevisionDefinition(
                definition=role,
                revision_no=ROLE_REVISIONS[role.id],
            )
            for role in (
                RoleDefinitionFile.model_validate(load_yaml(path))
                for path in sorted((definitions_root / "roles").glob("*.yaml"))
            )
        }
        policies = {
            policy.id: PolicyRevisionDefinition(
                definition=policy,
                revision_no=POLICY_REVISIONS[policy.id],
            )
            for policy in (
                PolicyDefinitionFile.model_validate(load_yaml(path))
                for path in sorted((definitions_root / "policies").glob("*.yaml"))
            )
        }
    return MappingRolePolicyLookup(roles=roles, policies=policies)


def load_workflow_definition(name: str) -> WorkflowDefinitionFile:
    with resolve_packaged_seed_definitions_root() as definitions_root:
        return WorkflowDefinitionFile.model_validate(
            load_yaml(definitions_root / "workflows" / f"{name}.yaml")
        )


def compile_workflow_fixture(
    workflow_definition: WorkflowDefinitionInput,
    revision_no: int,
) -> NormalizedCompiledPlan:
    return compile_workflow(
        workflow=workflow_definition,
        workflow_revision=WorkflowRevisionMetadata(
            workflow_key=workflow_definition.id,
            definition_revision_no=revision_no,
        ),
        compiler_version="bootstrap-fixture",
        lookup=load_seeded_lookup(),
    )


def task_compose_payload(workflow_key: str, **roots: Any) -> TaskComposeInput:
    payload: dict[str, Any] = {
        "task": {
            "key": "auth-refresh-hardening",
            "title": "Harden auth refresh flow",
            "summary": "Investigate and fix the auth refresh regression.",
            "instruction": "Stay scoped to the auth refresh failure path only.",
        },
        "workflow": {"key": workflow_key},
    }
    if roots:
        payload["roots"] = roots
    return TaskComposeInput.model_validate(payload)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


async def persist_bootstrap_runtime(
    session: AsyncSession,
    *,
    task_id: str,
    task_root: Path,
    compiler_version: str,
    latest_checkpoint: CheckpointProjection | None = None,
    task_compose: TaskComposeInput | None = None,
) -> RuntimeBootstrapResult:
    workflow_key = (
        task_compose.workflow.key if task_compose is not None else None
    ) or "minimal-implement-change"
    snapshot = await compile_current_workflow_launch_snapshot(
        session,
        workflow_key=workflow_key,
        compiler_version=compiler_version,
    )
    bootstrap_input = RuntimeBootstrapProjectionInput(
        task_id=task_id,
        active_flow_revision_id=f"flowrev.{task_id}.01",
        attempt_id=f"attempt.{task_id}.root.01",
        assignment_key=f"{task_id}.root.assign-01",
        dispatch_id=dispatch_id_for_task(task_id, "root", 0),
        task_root=task_root,
        task_compose=task_compose or task_compose_payload(workflow_key),
        workflow_definition=snapshot.workflow.definition,
        compiled_plan=snapshot.compiled_plan,
        role_policy_lookup=snapshot.role_policy_lookup,
        structural_edit_palette=await build_current_structural_edit_palette(session),
        latest_checkpoint=latest_checkpoint,
    )
    return await persist_bootstrap_runtime_from_precomputed(
        session,
        bootstrap_input,
        should_commit=False,
    )


async def seed_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    send_mode: PromptSendMode,
    rendered_at: datetime | None = None,
) -> DispatchTurnModel:
    state = await current_runtime_state(session, task_id)
    dispatch = DispatchTurnModel(
        dispatch_id=dispatch_id,
        flow_id=state.flow.flow_id,
        flow_revision_id=state.flow_revision.flow_revision_id,
        flow_node_id=state.current_node.flow_node_id,
        task_id=task_id,
        node_key=state.current_node.node_key,
        assignment_id=state.current_assignment.assignment_id,
        assignment_key=state.current_assignment.assignment_key,
        attempt_id=state.current_attempt.attempt_id,
        prompt_name=PromptFamily.PARENT_ROOT_DISPATCH.value,
        delivery_status="accepted",
        control_state="live",
        control_state_reason="launch_confirmed",
        prompt_path="",
        content_hash="",
        rendered_at=rendered_at or datetime.now(tz=UTC),
        opened_at=rendered_at or datetime.now(tz=UTC),
    )
    session.add(dispatch)
    session.add(
        DispatchDeliveryStateModel(
            dispatch_id=dispatch.dispatch_id,
            task_id=task_id,
            attempt_id=state.current_attempt.attempt_id,
            assignment_key=state.current_assignment.assignment_key,
            node_key=state.current_node.node_key,
            transport_family="local_runtime",
            transport_state="accepted",
        )
    )
    session.add(
        DispatchContinuityStateModel(
            dispatch_id=dispatch.dispatch_id,
            task_id=task_id,
            attempt_id=state.current_attempt.attempt_id,
            assignment_key=state.current_assignment.assignment_key,
            node_key=state.current_node.node_key,
            session_key_present=False,
        )
    )
    session.add(
        DispatchWatchdogStateModel(
            dispatch_id=dispatch.dispatch_id,
            task_id=task_id,
            attempt_id=state.current_attempt.attempt_id,
            assignment_key=state.current_assignment.assignment_key,
            node_key=state.current_node.node_key,
            watchdog_state="clear",
        )
    )
    await session.flush()
    return dispatch


async def seed_child_terminal_retry_checkpoint(
    session: AsyncSession,
    *,
    task_id: str,
    task_root: Path,
    dispatch: DispatchTurnModel,
    child_node: FlowNodeModel,
    attempt_id: str,
    assignment_suffix: str,
    assignment_summary: str,
    checkpoint_summary: str,
    checkpoint_next_step: str,
    checkpoint_risk: str,
    recorded_at: datetime,
    make_current: bool,
) -> Path:
    assignment = AssignmentModel(
        assignment_id=f"{task_id}.{child_node.node_key}.assignment.{assignment_suffix}",
        task_id=task_id,
        flow_id=dispatch.flow_id,
        flow_revision_id=dispatch.flow_revision_id or "",
        flow_node_id=child_node.flow_node_id,
        assignment_key=f"{task_id}.{child_node.node_key}.assign-{assignment_suffix}",
        node_key=child_node.node_key,
        summary=assignment_summary,
        instruction=None,
        criteria_json=[],
        consumes_json=[],
        produces_json=[],
        transient_refs_json=[],
        task_memory_search_hints_json=[],
        current_attempt_id=attempt_id,
    )
    attempt = AttemptModel(
        attempt_id=attempt_id,
        assignment_id=assignment.assignment_id,
        assignment_key=assignment.assignment_key,
        flow_node_id=child_node.flow_node_id,
        task_id=task_id,
        node_key=child_node.node_key,
        status="failed",
    )
    checkpoint_id_value = checkpoint_id(attempt_id, 1)
    session.add(assignment)
    await session.flush()
    session.add(attempt)
    session.add(
        AttemptCheckpointModel(
            checkpoint_id=checkpoint_id_value,
            assignment_id=assignment.assignment_id,
            assignment_key=assignment.assignment_key,
            attempt_id=attempt_id,
            flow_node_id=child_node.flow_node_id,
            node_key=child_node.node_key,
            checkpoint_kind=CheckpointKind.TERMINAL.value,
            outcome="retry",
            summary=checkpoint_summary,
            next_step=checkpoint_next_step,
            blockers_json=[],
            risks_json=[checkpoint_risk],
            produced_artifact_claims_json=[],
            produced_artifacts_json=[],
            artifact_refs_json=[],
            transient_refs_json=[],
            task_memory_search_hints_json=[],
            recorded_at=recorded_at,
        )
    )
    await session.flush()
    attempt.latest_checkpoint_id = checkpoint_id_value
    if make_current:
        child_node.current_assignment_id = assignment.assignment_id
    await session.flush()
    return task_root / "_runtime" / "attempts" / attempt_id / "latest-checkpoint.md"
