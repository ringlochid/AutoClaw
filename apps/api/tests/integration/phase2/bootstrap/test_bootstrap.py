from __future__ import annotations

import json
from pathlib import Path

import pytest
from autoclaw.runtime import (
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    PromptFamily,
    RuntimeBootstrapProjectionInput,
    localize_external_resource,
)
from autoclaw.runtime.launch import bootstrap_task_runtime_projection
from tests.integration.phase2.bootstrap.fixtures import (
    compile_workflow_fixture,
    load_seeded_lookup,
    load_workflow_definition,
    task_compose_payload,
)


def test_bootstrap_root_runtime_materializes_manifest_assignment_and_prompt(
    tmp_path: Path,
) -> None:
    workflow_definition = load_workflow_definition("minimal_implement_change")
    compiled_plan = compile_workflow_fixture(workflow_definition, revision_no=4)

    result = bootstrap_task_runtime_projection(
        RuntimeBootstrapProjectionInput(
            task_id="task_2026_0042",
            active_flow_revision_id="flowrev_0001",
            attempt_id="attempt.root.01",
            assignment_key="root.assign-01",
            dispatch_id="dispatch.root.01",
            task_root=tmp_path / "task-root",
            task_compose=task_compose_payload("minimal-implement-change"),
            workflow_definition=workflow_definition,
            compiled_plan=compiled_plan,
            role_policy_lookup=load_seeded_lookup(),
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
    assert result.assignment.consumes == ()
    assert all(criteria.version is None for criteria in result.assignment.criteria)
    assert result.prompt_record.prompt_name == PromptFamily.PARENT_ROOT_DISPATCH
    assert result.prompt_record.rendered_markdown_path.is_file()
    assert result.prompt_record.transport_request_path.is_file()
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
    assert "## Latest Checkpoint Context" in result.prompt_bundle.full_markdown
    assert "## Consumed Durable Refs" in result.prompt_bundle.full_markdown
    assert "- no current relevant checkpoint is surfaced" in result.prompt_bundle.full_markdown
    assert str(result.paths.criteria_path / "implementation_rules.v01.md") in (
        result.prompt_bundle.full_markdown
    )
    assert "## Allowed Actions Now" in result.prompt_bundle.full_markdown
    assert "architect (allowed node kinds: worker)" in result.prompt_bundle.full_markdown
    assert "standard-parent-planning (applies_to: parent)" in result.prompt_bundle.full_markdown
    manifest_markdown = (result.paths.runtime_path / "workflow-manifest.md").read_text(
        encoding="utf-8"
    )
    assert "## Structural Edit Palette" in manifest_markdown
    prompt_request = json.loads(
        result.prompt_record.transport_request_path.read_text(encoding="utf-8")
    )
    assert prompt_request["dispatch_id"] == "dispatch.root.01"
    assert prompt_request["send_mode"] == "full_prompt"
    assert prompt_request["instructions_text"] == result.prompt_bundle.instructions_text
    assert prompt_request["input_text"] == result.prompt_bundle.input_text
    assert prompt_request["content_hash"] == result.prompt_record.content_hash
    assert prompt_request["transport_request_hash"] == result.prompt_record.transport_request_hash
    assert "- latest_checkpoint_path: null" in manifest_markdown
    assert result.manifest.structural_edit_palette is not None
    assert any(role.role == "architect" for role in result.manifest.structural_edit_palette.roles)
    assert any(
        policy.policy == "standard-parent-planning"
        for policy in result.manifest.structural_edit_palette.policies
    )


def test_bootstrap_rejects_non_root_automatic_assignment_without_explicit_projection(
    tmp_path: Path,
) -> None:
    workflow_definition = load_workflow_definition("normal_parent_first_release")
    compiled_plan = compile_workflow_fixture(workflow_definition, revision_no=7)

    with pytest.raises(ValueError, match="launch/root path"):
        bootstrap_task_runtime_projection(
            RuntimeBootstrapProjectionInput(
                task_id="task_2026_0042",
                active_flow_revision_id="flowrev_0002",
                attempt_id="attempt.implement_change.01",
                assignment_key="implement_change.assign-01",
                dispatch_id="dispatch.implement_change.01",
                task_root=tmp_path / "task-root",
                task_compose=task_compose_payload("normal-parent-first-release"),
                workflow_definition=workflow_definition,
                compiled_plan=compiled_plan,
                role_policy_lookup=load_seeded_lookup(),
                current_node_key="implement_change",
            )
        )


def test_bootstrap_manifest_preserves_declaring_owner_for_inherited_criteria(
    tmp_path: Path,
) -> None:
    workflow_definition = load_workflow_definition("normal_parent_first_release")
    compiled_plan = compile_workflow_fixture(workflow_definition, revision_no=7)

    result = bootstrap_task_runtime_projection(
        RuntimeBootstrapProjectionInput(
            task_id="task_2026_criteria_owner_bootstrap",
            active_flow_revision_id="flowrev_criteria_owner_bootstrap",
            attempt_id="attempt.root.01",
            assignment_key="root.assign-01",
            dispatch_id="dispatch.root.01",
            task_root=tmp_path / "task-root",
            task_compose=task_compose_payload("normal-parent-first-release"),
            workflow_definition=workflow_definition,
            compiled_plan=compiled_plan,
            role_policy_lookup=load_seeded_lookup(),
        )
    )

    node_by_key = {node.node_key: node for node in result.manifest.node_tree}
    review_change_criteria = node_by_key["review_change"].criteria

    assert len(review_change_criteria) == 1
    assert review_change_criteria[0].slot == "implementation_subtree_requirements"
    assert review_change_criteria[0].owner_node_key == "implementation_subtree"


def test_bootstrap_honors_custom_root_bindings_and_localizes_external_resource(
    tmp_path: Path,
) -> None:
    workflow_definition = load_workflow_definition("minimal_implement_change")
    compiled_plan = compile_workflow_fixture(workflow_definition, revision_no=4)
    shared_context = (tmp_path / "shared-context").resolve()
    shared_context.mkdir(parents=True)

    result = bootstrap_task_runtime_projection(
        RuntimeBootstrapProjectionInput(
            task_id="task_2026_0043",
            active_flow_revision_id="flowrev_0003",
            attempt_id="attempt.root.01",
            assignment_key="root.assign-01",
            dispatch_id="dispatch.root.01",
            task_root=tmp_path / "task-root",
            task_compose=task_compose_payload(
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
            role_policy_lookup=load_seeded_lookup(),
        )
    )

    assert result.paths.workspace_path == (tmp_path / "custom-workspace").resolve()
    assert result.paths.context_path == shared_context
    localized_criteria_path = (
        result.paths.transfers_path / "localized" / "implementation_rules.v01.md"
    )
    assert result.assignment.criteria[0].path == localized_criteria_path
    assert result.manifest.node_tree[0].criteria[0].path == localized_criteria_path
    assert result.manifest.current_context.current_relevant_paths[0].path == localized_criteria_path
    assert localized_criteria_path.is_file()
    assert str(localized_criteria_path) in result.prompt_bundle.full_markdown
    assert str(shared_context / "criteria" / "implementation_rules.v01.md") not in (
        result.prompt_bundle.full_markdown
    )

    external_resource = tmp_path / "outside" / "user-note.txt"
    external_resource.parent.mkdir(parents=True)
    external_resource.write_text("keep this repro note", encoding="utf-8")

    localized_path = localize_external_resource(
        paths=result.paths,
        source_path=external_resource,
    )

    assert localized_path.parent == result.paths.transfers_path / "localized"
    assert localized_path.is_relative_to(result.paths.task_root)
    assert localized_path.read_text(encoding="utf-8") == "keep this repro note"


def test_bootstrap_materializes_supplied_checkpoint_projection(tmp_path: Path) -> None:
    workflow_definition = load_workflow_definition("minimal_implement_change")
    compiled_plan = compile_workflow_fixture(workflow_definition, revision_no=4)

    result = bootstrap_task_runtime_projection(
        RuntimeBootstrapProjectionInput(
            task_id="task_2026_0044",
            active_flow_revision_id="flowrev_0004",
            attempt_id="attempt.root.01",
            assignment_key="root.assign-01",
            dispatch_id="dispatch.root.01",
            task_root=tmp_path / "task-root",
            task_compose=task_compose_payload("minimal-implement-change"),
            workflow_definition=workflow_definition,
            compiled_plan=compiled_plan,
            role_policy_lookup=load_seeded_lookup(),
            latest_checkpoint=CheckpointProjection(
                checkpoint_kind=CheckpointKind.PROGRESS,
                handoff=CheckpointHandoff(
                    summary="Root reviewed the initial task shape and is ready to continue.",
                    next_step=(
                        "Stage the next bounded worker assignment when current evidence is "
                        "sufficient."
                    ),
                ),
            ),
        )
    )

    latest_checkpoint_path = (
        result.paths.runtime_path / "attempts" / "attempt.root.01" / "latest-checkpoint.md"
    )
    assert latest_checkpoint_path.is_file()
    assert result.manifest.current_context.latest_checkpoint_path == latest_checkpoint_path
    assert result.manifest.current_context.latest_relevant_checkpoint_path is None
    assert "## Latest Checkpoint Context" in result.prompt_bundle.full_markdown
    assert result.latest_checkpoint is not None
    assert result.latest_checkpoint.checkpoint_kind == CheckpointKind.PROGRESS
    assert result.latest_checkpoint.outcome is None
