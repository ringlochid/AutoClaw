from __future__ import annotations

from pathlib import Path

from autoclaw.runtime import RuntimeBootstrapProjectionInput
from autoclaw.runtime.launch import bootstrap_task_runtime_projection
from autoclaw.runtime.launch.persistence.runtime import write_bootstrap_runtime_outputs
from tests.integration.bootstrap.fixtures import (
    compile_workflow_fixture,
    load_seeded_lookup,
    load_workflow_definition,
    task_compose_payload,
)


def test_write_bootstrap_runtime_outputs_restores_stable_manifest_and_assignment_files(
    tmp_path: Path,
) -> None:
    workflow_definition = load_workflow_definition("bounded_change")
    compiled_plan = compile_workflow_fixture(workflow_definition, revision_no=4)

    result = bootstrap_task_runtime_projection(
        RuntimeBootstrapProjectionInput(
            task_id="task_2026_0045",
            active_flow_revision_id="flowrev_bootstrap_outputs",
            attempt_id="attempt.root.01",
            assignment_key="root.assign-01",
            dispatch_id="dispatch.root.01",
            task_root=tmp_path / "task-root",
            task_compose=task_compose_payload("bounded-change"),
            workflow_definition=workflow_definition,
            compiled_plan=compiled_plan,
            role_policy_lookup=load_seeded_lookup(),
        )
    )

    manifest_json = result.paths.runtime_path / "workflow-manifest.json"
    manifest_markdown = result.paths.runtime_path / "workflow-manifest.md"
    assignment_json = (
        result.paths.runtime_path
        / "attempts"
        / result.prompt_record.attempt_id
        / ("assignment.json")
    )
    assignment_markdown = (
        result.paths.runtime_path / "attempts" / result.prompt_record.attempt_id / ("assignment.md")
    )
    artifact_index = (
        result.paths.runtime_path
        / "attempts"
        / result.prompt_record.attempt_id
        / ("artifact-index.json")
    )
    transient_index = (
        result.paths.runtime_path
        / "attempts"
        / result.prompt_record.attempt_id
        / ("transient-index.json")
    )

    for path in (
        manifest_json,
        manifest_markdown,
        assignment_json,
        assignment_markdown,
        artifact_index,
        transient_index,
    ):
        path.unlink(missing_ok=True)

    write_bootstrap_runtime_outputs(result)

    assert manifest_json.is_file()
    assert manifest_markdown.is_file()
    assert assignment_json.is_file()
    assert assignment_markdown.is_file()
    assert artifact_index.is_file()
    assert transient_index.is_file()
