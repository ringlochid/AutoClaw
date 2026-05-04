from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from app.compiler import (
    MappingRolePolicyLookup,
    NormalizedCompiledPlan,
    PolicyRevisionDefinition,
    RoleRevisionDefinition,
    WorkflowRevisionMetadata,
    compile_workflow,
)
from app.runtime import (
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    PromptFamily,
    RuntimeBootstrapInput,
    TaskComposeInput,
    bootstrap_task_runtime,
    localize_external_resource,
)
from app.schemas.definitions import (
    PolicyDefinitionFile,
    RoleDefinitionFile,
    WorkflowDefinitionFile,
)
from app.schemas.workflow_definitions import WorkflowDefinitionInput

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFINITIONS_ROOT = REPO_ROOT / "definitions"

ROLE_REVISIONS = {
    "architect": 48,
    "engineer": 44,
    "planner": 47,
    "planning_lead": 42,
    "release_operator": 46,
    "researcher": 43,
    "reviewer": 45,
    "root_planning_lead": 41,
}

POLICY_REVISIONS = {
    "standard-parent-planning": 52,
    "standard-release": 55,
    "standard-review": 54,
    "standard-root-planning": 51,
    "standard-worker": 53,
}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _load_seeded_lookup() -> MappingRolePolicyLookup:
    roles = {
        role.id: RoleRevisionDefinition(
            definition=role,
            revision_no=ROLE_REVISIONS[role.id],
        )
        for role in (
            RoleDefinitionFile.model_validate(_load_yaml(path))
            for path in sorted((DEFINITIONS_ROOT / "roles").glob("*.yaml"))
        )
    }
    policies = {
        policy.id: PolicyRevisionDefinition(
            definition=policy,
            revision_no=POLICY_REVISIONS[policy.id],
        )
        for policy in (
            PolicyDefinitionFile.model_validate(_load_yaml(path))
            for path in sorted((DEFINITIONS_ROOT / "policies").glob("*.yaml"))
        )
    }
    return MappingRolePolicyLookup(roles=roles, policies=policies)


def _load_workflow_definition(name: str) -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        _load_yaml(DEFINITIONS_ROOT / "workflows" / f"{name}.yaml")
    )


def _compile_workflow(
    workflow_definition: WorkflowDefinitionInput,
    revision_no: int,
) -> NormalizedCompiledPlan:
    return compile_workflow(
        workflow=workflow_definition,
        workflow_revision=WorkflowRevisionMetadata(
            workflow_key=workflow_definition.id,
            definition_revision_no=revision_no,
        ),
        compiler_version="phase-2-bootstrap",
        lookup=_load_seeded_lookup(),
    )


def _task_compose_payload(workflow_key: str, **roots: Any) -> TaskComposeInput:
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


def test_bootstrap_root_runtime_materializes_manifest_assignment_and_prompt(
    tmp_path: Path,
) -> None:
    workflow_definition = _load_workflow_definition("minimal_implement_change")
    compiled_plan = _compile_workflow(workflow_definition, revision_no=4)

    result = bootstrap_task_runtime(
        RuntimeBootstrapInput(
            task_id="task_2026_0042",
            active_flow_revision_id="flowrev_0001",
            attempt_id="attempt.root.01",
            assignment_key="root.assign-01",
            dispatch_id="dispatch.root.01",
            task_root=tmp_path / "task-root",
            task_compose=_task_compose_payload("minimal-implement-change"),
            workflow_definition=workflow_definition,
            compiled_plan=compiled_plan,
            role_policy_lookup=_load_seeded_lookup(),
        )
    )

    assert result.paths.workspace_path.is_dir()
    assert result.paths.context_path.is_dir()
    assert result.paths.criteria_path.is_dir()
    assert result.paths.outputs_path.is_dir()
    assert result.paths.transfers_path.is_dir()
    assert result.paths.runtime_path.is_dir()
    assert result.manifest.workflow.workflow_key == "minimal-implement-change"
    assert result.assignment.node_key == "root"
    assert result.prompt_record.prompt_name == PromptFamily.PARENT_ROOT_DISPATCH
    assert result.prompt_record.rendered_markdown_path.is_file()
    assert (result.paths.runtime_path / "workflow-manifest.json").is_file()
    assert (result.paths.runtime_path / "workflow-manifest.md").is_file()
    assert (
        result.paths.runtime_path / "attempts" / "attempt.root.01" / "assignment.json"
    ).is_file()
    assert (result.paths.runtime_path / "attempts" / "attempt.root.01" / "assignment.md").is_file()
    assert not (
        result.paths.runtime_path / "attempts" / "attempt.root.01" / "latest-checkpoint.md"
    ).exists()
    assert (result.paths.criteria_path / "implementation_rules.md").is_file()
    assert "## Current Assignment" in result.prompt_bundle.full_markdown
    assert "## Allowed Actions Now" in result.prompt_bundle.full_markdown


def test_bootstrap_rejects_non_root_automatic_assignment_without_explicit_projection(
    tmp_path: Path,
) -> None:
    workflow_definition = _load_workflow_definition("normal_parent_first_release")
    compiled_plan = _compile_workflow(workflow_definition, revision_no=7)

    with pytest.raises(ValueError, match="launch/root path"):
        bootstrap_task_runtime(
            RuntimeBootstrapInput(
                task_id="task_2026_0042",
                active_flow_revision_id="flowrev_0002",
                attempt_id="attempt.implement_change.01",
                assignment_key="implement_change.assign-01",
                dispatch_id="dispatch.implement_change.01",
                task_root=tmp_path / "task-root",
                task_compose=_task_compose_payload("normal-parent-first-release"),
                workflow_definition=workflow_definition,
                compiled_plan=compiled_plan,
                role_policy_lookup=_load_seeded_lookup(),
                current_node_key="implement_change",
            )
        )


def test_bootstrap_honors_custom_root_bindings_and_localizes_external_resource(
    tmp_path: Path,
) -> None:
    workflow_definition = _load_workflow_definition("minimal_implement_change")
    compiled_plan = _compile_workflow(workflow_definition, revision_no=4)
    shared_context = (tmp_path / "shared-context").resolve()
    shared_context.mkdir(parents=True)

    result = bootstrap_task_runtime(
        RuntimeBootstrapInput(
            task_id="task_2026_0043",
            active_flow_revision_id="flowrev_0003",
            attempt_id="attempt.root.01",
            assignment_key="root.assign-01",
            dispatch_id="dispatch.root.01",
            task_root=tmp_path / "task-root",
            task_compose=_task_compose_payload(
                "minimal-implement-change",
                workspace={
                    "mode": "ensure_host_path",
                    "host_path": str(tmp_path / "custom-workspace"),
                },
                context={
                    "mode": "use_existing_host",
                    "host_path": str(shared_context),
                },
            ),
            workflow_definition=workflow_definition,
            compiled_plan=compiled_plan,
            role_policy_lookup=_load_seeded_lookup(),
        )
    )

    assert result.paths.workspace_path == (tmp_path / "custom-workspace").resolve()
    assert result.paths.context_path == shared_context

    external_resource = tmp_path / "outside" / "user-note.txt"
    external_resource.parent.mkdir(parents=True)
    external_resource.write_text("keep this repro note", encoding="utf-8")

    localized_path = localize_external_resource(
        paths=result.paths,
        source_path=external_resource,
    )

    assert localized_path.parent == result.paths.context_path
    assert localized_path.read_text(encoding="utf-8") == "keep this repro note"


def test_bootstrap_materializes_supplied_checkpoint_projection(tmp_path: Path) -> None:
    workflow_definition = _load_workflow_definition("minimal_implement_change")
    compiled_plan = _compile_workflow(workflow_definition, revision_no=4)

    result = bootstrap_task_runtime(
        RuntimeBootstrapInput(
            task_id="task_2026_0044",
            active_flow_revision_id="flowrev_0004",
            attempt_id="attempt.root.01",
            assignment_key="root.assign-01",
            dispatch_id="dispatch.root.01",
            task_root=tmp_path / "task-root",
            task_compose=_task_compose_payload("minimal-implement-change"),
            workflow_definition=workflow_definition,
            compiled_plan=compiled_plan,
            role_policy_lookup=_load_seeded_lookup(),
            latest_checkpoint=CheckpointProjection(
                checkpoint_kind=CheckpointKind.PROGRESS,
                handoff=CheckpointHandoff(
                    summary="Root reviewed the initial task shape and is ready to continue.",
                    next_step="Stage the next bounded worker assignment when current "
                    "evidence is sufficient.",
                ),
            ),
        )
    )

    latest_checkpoint_path = (
        result.paths.runtime_path / "attempts" / "attempt.root.01" / "latest-checkpoint.md"
    )
    assert latest_checkpoint_path.is_file()
    assert result.manifest.current_context.latest_checkpoint_path == latest_checkpoint_path
    assert "## Latest Checkpoint Context" in result.prompt_bundle.full_markdown
    assert result.latest_checkpoint is not None
    assert result.latest_checkpoint.checkpoint_kind == CheckpointKind.PROGRESS
    assert result.latest_checkpoint.outcome is None
