from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from app import cli
from app.compiler import (
    MappingRolePolicyLookup,
    NormalizedCompiledPlan,
    PolicyRevisionDefinition,
    RoleRevisionDefinition,
    WorkflowRevisionMetadata,
    compile_workflow,
)
from app.config import get_settings
from app.db import (
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptConsumedRefModel,
    AttemptModel,
    DispatchContinuityStateModel,
    DispatchTurnModel,
)
from app.db.session import dispose_db_engine, get_session_factory
from app.runtime import (
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    PromptFamily,
    PromptSendMode,
    RuntimeLaunchInput,
    TaskComposeInput,
    launch_task_runtime,
    localize_external_resource,
)
from app.runtime.contracts import _RuntimeBootstrapProjectionInput
from app.runtime.ids import attempt_consumed_ref_id, checkpoint_id, dispatch_id_for_task
from app.runtime.launch.projection import _bootstrap_task_runtime_projection
from app.runtime.projection.materialize import materialize_attempt_files, render_dispatch_prompt
from app.schemas.definitions import (
    PolicyDefinitionFile,
    RoleDefinitionFile,
    WorkflowDefinitionFile,
)
from app.schemas.definitions.workflow import WorkflowDefinitionInput

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

    result = _bootstrap_task_runtime_projection(
        _RuntimeBootstrapProjectionInput(
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
    assert "- no current relevant checkpoint is surfaced" in result.prompt_bundle.full_markdown
    assert "## Allowed Actions Now" in result.prompt_bundle.full_markdown
    manifest_markdown = (result.paths.runtime_path / "workflow-manifest.md").read_text(
        encoding="utf-8"
    )
    prompt_request = json.loads(
        result.prompt_record.transport_request_path.read_text(encoding="utf-8")
    )
    assert prompt_request["dispatch_id"] == "dispatch.root.01"
    assert prompt_request["send_mode"] == "full_prompt"
    assert prompt_request["previous_response_id"] is None
    assert prompt_request["instructions_text"] == result.prompt_bundle.instructions_text
    assert prompt_request["input_text"] == result.prompt_bundle.input_text
    assert prompt_request["content_hash"] == result.prompt_record.content_hash
    assert prompt_request["transport_request_hash"] == result.prompt_record.transport_request_hash
    assert "- latest_checkpoint_path: null" in manifest_markdown


def test_bootstrap_rejects_non_root_automatic_assignment_without_explicit_projection(
    tmp_path: Path,
) -> None:
    workflow_definition = _load_workflow_definition("normal_parent_first_release")
    compiled_plan = _compile_workflow(workflow_definition, revision_no=7)

    with pytest.raises(ValueError, match="launch/root path"):
        _bootstrap_task_runtime_projection(
            _RuntimeBootstrapProjectionInput(
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

    result = _bootstrap_task_runtime_projection(
        _RuntimeBootstrapProjectionInput(
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

    result = _bootstrap_task_runtime_projection(
        _RuntimeBootstrapProjectionInput(
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


async def test_launch_materializes_dispatch_files_for_full_prompt_dispatch(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_dispatch_materialization"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    try:
        await cli._cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=8123,
                log_level="INFO",
                api_key="api-test-key",
                internal_api_key="internal-test-key",
                force=True,
                skip_db_upgrade=False,
                json=False,
            )
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_task_runtime(
                    session,
                    RuntimeLaunchInput(
                        task_id=task_id,
                        task_root=task_root,
                        task_compose=_task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-2-dispatch-proof",
                    ),
                )

            dispatch_dir = task_root / "_runtime" / "dispatch" / dispatch_id
            prompt_path = dispatch_dir / "prompt.md"
            prompt_request_path = dispatch_dir / "prompt-request.json"
            delivery_state_path = dispatch_dir / "delivery-state.json"
            continuity_state_path = dispatch_dir / "continuity-state.json"
            watchdog_state_path = dispatch_dir / "watchdog-state.json"
            provider_events_path = dispatch_dir / "provider-events.ndjson"

            assert prompt_path.is_file()
            assert prompt_request_path.is_file()
            assert delivery_state_path.is_file()
            assert continuity_state_path.is_file()
            assert watchdog_state_path.is_file()
            assert provider_events_path.is_file()

            full_prompt_request = json.loads(prompt_request_path.read_text(encoding="utf-8"))
            assert full_prompt_request["send_mode"] == "full_prompt"
            assert full_prompt_request["previous_response_id"] is None
            assert full_prompt_request["instructions_text"] is not None
            assert "## Operating Model" in prompt_path.read_text(encoding="utf-8")
            assert provider_events_path.read_text(encoding="utf-8") == ""
    finally:
        await dispose_db_engine()


async def test_render_dispatch_prompt_persists_same_session_wrapper_for_prebound_dispatch(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_same_session_render"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    try:
        await cli._cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=8123,
                log_level="INFO",
                api_key="api-test-key",
                internal_api_key="internal-test-key",
                force=True,
                skip_db_upgrade=False,
                json=False,
            )
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_task_runtime(
                    session,
                    RuntimeLaunchInput(
                        task_id=task_id,
                        task_root=task_root,
                        task_compose=_task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-2-same-session-render",
                    ),
                )

            async with session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                continuity_state = await session.get(DispatchContinuityStateModel, dispatch_id)
                assert dispatch is not None
                assert continuity_state is not None

                dispatch.send_mode = PromptSendMode.SAME_SESSION_CONTINUE.value
                continuity_state.previous_response_id = "resp_root_01"

                bundle, record = await render_dispatch_prompt(session, task_id, dispatch)

            same_session_request = json.loads(
                record.transport_request_path.read_text(encoding="utf-8")
            )
            assert bundle.instructions_text is None
            assert record.transport_request.instructions_text is None
            assert same_session_request["send_mode"] == "same_session_continue"
            assert same_session_request["previous_response_id"] == "resp_root_01"
            assert same_session_request["instructions_text"] is None
            assert same_session_request["input_text"] == bundle.input_text
            assert same_session_request["transport_request_hash"] == record.transport_request_hash
            assert "## Operating Model" not in bundle.input_text
            assert (
                (task_root / "_runtime" / "dispatch" / dispatch_id / "prompt.md")
                .read_text(encoding="utf-8")
                .startswith("## Operating Model")
            )
    finally:
        await dispose_db_engine()


async def test_render_dispatch_prompt_uses_surfaced_relevant_prior_checkpoint(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_prior_checkpoint_handoff"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    prior_attempt_id = f"attempt.{task_id}.root.00"
    prior_checkpoint_path = (
        task_root / "_runtime" / "attempts" / prior_attempt_id / "latest-checkpoint.md"
    )

    try:
        await cli._cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=8123,
                log_level="INFO",
                api_key="api-test-key",
                internal_api_key="internal-test-key",
                force=True,
                skip_db_upgrade=False,
                json=False,
            )
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_task_runtime(
                    session,
                    RuntimeLaunchInput(
                        task_id=task_id,
                        task_root=task_root,
                        task_compose=_task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-2-prior-checkpoint-proof",
                    ),
                )

            async with session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                assert dispatch.assignment_id is not None
                assert dispatch.attempt_id is not None
                assert dispatch.flow_node_id is not None

                assignment = await session.get(AssignmentModel, dispatch.assignment_id)
                assert assignment is not None

                prior_checkpoint_id = checkpoint_id(prior_attempt_id, 1)
                prior_attempt = AttemptModel(
                    attempt_id=prior_attempt_id,
                    assignment_id=assignment.assignment_id,
                    assignment_key=assignment.assignment_key,
                    flow_node_id=dispatch.flow_node_id,
                    task_id=task_id,
                    node_key=assignment.node_key,
                    status="failed",
                )
                session.add(prior_attempt)
                await session.flush()
                session.add(
                    AttemptCheckpointModel(
                        checkpoint_id=prior_checkpoint_id,
                        assignment_id=assignment.assignment_id,
                        assignment_key=assignment.assignment_key,
                        attempt_id=prior_attempt_id,
                        flow_node_id=dispatch.flow_node_id,
                        node_key=assignment.node_key,
                        checkpoint_kind=CheckpointKind.TERMINAL.value,
                        outcome="retry",
                        summary="Prior retry handoff for the current root decision.",
                        next_step="Reuse this surfaced checkpoint before staging the next child.",
                        blockers_json=[],
                        risks_json=["Prior child evidence remains the deciding input."],
                        produced_artifact_claims_json=[],
                        produced_artifacts_json=[],
                        artifact_refs_json=[],
                        transient_refs_json=[],
                        task_memory_search_hints_json=[],
                        recorded_at=dispatch.rendered_at - timedelta(seconds=1),
                    )
                )
                await session.flush()
                prior_attempt.latest_checkpoint_id = prior_checkpoint_id
                session.add(
                    AttemptConsumedRefModel(
                        attempt_consumed_ref_id=attempt_consumed_ref_id(dispatch.attempt_id, 99),
                        attempt_id=dispatch.attempt_id,
                        ref_kind="checkpoint",
                        slot=None,
                        version=None,
                        path=str(prior_checkpoint_path),
                        description="Latest surfaced prior-attempt checkpoint for this root turn.",
                        order_index=99,
                    )
                )
                await session.flush()
                await materialize_attempt_files(session, task_id, prior_attempt_id)

                bundle, _ = await render_dispatch_prompt(session, task_id, dispatch)

            assert prior_checkpoint_path.is_file()
            assert f"- path: {prior_checkpoint_path}" in bundle.full_markdown
            assert "Prior retry handoff for the current root decision." in bundle.full_markdown
            assert (
                "Reuse this surfaced checkpoint before staging the next child."
                in bundle.full_markdown
            )
            assert "Prior child evidence remains the deciding input." in bundle.full_markdown
            assert "- no current relevant checkpoint is surfaced" not in bundle.full_markdown
    finally:
        await dispose_db_engine()


async def test_materialize_attempt_files_keeps_assignment_transient_refs_before_checkpoint(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_transient_index"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    try:
        await cli._cmd_init(
            argparse.Namespace(
                config=str(config_path),
                data_dir=str(data_dir),
                database_url=None,
                host="127.0.0.1",
                port=8123,
                log_level="INFO",
                api_key="api-test-key",
                internal_api_key="internal-test-key",
                force=True,
                skip_db_upgrade=False,
                json=False,
            )
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await launch_task_runtime(
                    session,
                    RuntimeLaunchInput(
                        task_id=task_id,
                        task_root=task_root,
                        task_compose=_task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-2-transient-index-proof",
                    ),
                )

            transient_path = task_root / "tmp" / "transfers" / "root" / "bootstrap-carryover.md"
            transient_path.parent.mkdir(parents=True, exist_ok=True)
            transient_path.write_text("keep this staged carryover", encoding="utf-8")

            async with session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                assert dispatch.assignment_id is not None
                assert dispatch.attempt_id is not None
                attempt_id = dispatch.attempt_id

                assignment = await session.get(AssignmentModel, dispatch.assignment_id)
                assert assignment is not None
                assignment.transient_refs_json = [
                    {
                        "kind": "transient",
                        "path": str(transient_path),
                        "description": (
                            "Assignment-staged transient carryover before any checkpoint."
                        ),
                    }
                ]
                await session.flush()

                await materialize_attempt_files(session, task_id, attempt_id)

            transient_index_path = (
                task_root / "_runtime" / "attempts" / attempt_id / "transient-index.json"
            )
            assert transient_index_path.is_file()
            assert json.loads(transient_index_path.read_text(encoding="utf-8")) == [
                {
                    "path": str(transient_path),
                    "description": "Assignment-staged transient carryover before any checkpoint.",
                }
            ]
    finally:
        await dispose_db_engine()
