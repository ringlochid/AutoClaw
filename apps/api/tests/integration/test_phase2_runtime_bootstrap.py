from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
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
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
)
from app.db.session import dispose_db_engine, get_session_factory
from app.registry import compile_current_workflow_launch_snapshot
from app.runtime import (
    CheckpointHandoff,
    CheckpointKind,
    CheckpointProjection,
    PromptFamily,
    PromptSendMode,
    TaskComposeInput,
    localize_external_resource,
)
from app.runtime.contracts import RuntimeBootstrapResult, _RuntimeBootstrapProjectionInput
from app.runtime.ids import attempt_consumed_ref_id, checkpoint_id, dispatch_id_for_task
from app.runtime.launch import persist_bootstrap_runtime_from_precomputed
from app.runtime.launch.projection import _bootstrap_task_runtime_projection
from app.runtime.projection.materialize import (
    materialize_attempt_files,
    materialize_dispatch_files,
    render_dispatch_prompt,
)
from app.runtime.projection.state import build_dispatch_manifest_projection, current_runtime_state
from app.schemas.definitions import (
    PolicyDefinitionFile,
    RoleDefinitionFile,
    WorkflowDefinitionFile,
)
from app.schemas.definitions.workflow import WorkflowDefinitionInput
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def _persist_bootstrap_runtime(
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
    bootstrap_input = _RuntimeBootstrapProjectionInput(
        task_id=task_id,
        active_flow_revision_id=f"flowrev.{task_id}.01",
        attempt_id=f"attempt.{task_id}.root.01",
        assignment_key=f"{task_id}.root.assign-01",
        dispatch_id=dispatch_id_for_task(task_id, "root", 0),
        task_root=task_root,
        task_compose=task_compose or _task_compose_payload(workflow_key),
        workflow_definition=snapshot.workflow.definition,
        compiled_plan=snapshot.compiled_plan,
        role_policy_lookup=snapshot.role_policy_lookup,
        latest_checkpoint=latest_checkpoint,
    )
    return await persist_bootstrap_runtime_from_precomputed(
        session,
        bootstrap_input,
        commit=False,
    )


async def _seed_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    send_mode: PromptSendMode,
    previous_response_id: str | None = None,
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
        phase="execution",
        status="accepted",
        prompt_name=PromptFamily.PARENT_ROOT_DISPATCH.value,
        send_mode=send_mode.value,
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
            transport_family="phase2_local_runtime",
            transport_state="accepted",
            controller_observation_state="launching",
            send_mode=send_mode.value,
        )
    )
    session.add(
        DispatchContinuityStateModel(
            dispatch_id=dispatch.dispatch_id,
            task_id=task_id,
            attempt_id=state.current_attempt.attempt_id,
            assignment_key=state.current_assignment.assignment_key,
            node_key=state.current_node.node_key,
            continuity_state="candidate",
            previous_response_id=previous_response_id,
            session_key_present=previous_response_id is not None,
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

    assert localized_path.parent == result.paths.transfers_path / "localized"
    assert localized_path.is_relative_to(result.paths.task_root)
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
    assert result.manifest.current_context.latest_relevant_checkpoint_path is None
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
                await _persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-dispatch-proof",
                )
                await _seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.FULL_PROMPT,
                )
                await materialize_dispatch_files(session, task_id, dispatch_id)

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
                await _persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-same-session-render",
                )
                await _seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.SAME_SESSION_CONTINUE,
                    previous_response_id="resp_root_01",
                )
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None

                bundle, record = await render_dispatch_prompt(session, task_id, dispatch)

        same_session_request = json.loads(record.transport_request_path.read_text(encoding="utf-8"))
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
    surfaced_attempt_ids = (
        f"attempt.{task_id}.root.00z",
        f"attempt.{task_id}.root.00b",
        f"attempt.{task_id}.root.00a",
    )
    current_attempt_id = f"attempt.{task_id}.root.01"
    surfaced_checkpoint_paths = tuple(
        task_root / "_runtime" / "attempts" / attempt_id / "latest-checkpoint.md"
        for attempt_id in surfaced_attempt_ids
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
                result = await _persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-prior-checkpoint-proof",
                    latest_checkpoint=CheckpointProjection(
                        checkpoint_kind=CheckpointKind.PROGRESS,
                        handoff=CheckpointHandoff(
                            summary="Current root checkpoint for the active attempt.",
                            next_step="Use surfaced prior checkpoints for redispatch handoff.",
                        ),
                    ),
                )
                await materialize_attempt_files(
                    session,
                    task_id,
                    result.manifest.current_context.active_attempt_id,
                )
                dispatch = await _seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.FULL_PROMPT,
                    rendered_at=datetime.now(tz=UTC),
                )
                assert dispatch.assignment_id is not None
                assert dispatch.attempt_id is not None
                assert dispatch.flow_node_id is not None

                assignment = await session.get(AssignmentModel, dispatch.assignment_id)
                assert assignment is not None

                surfaced_summaries = (
                    "Old surfaced checkpoint that should lose on recorded_at.",
                    "New surfaced checkpoint that should lose on path tie-break.",
                    "New surfaced checkpoint selected by path tie-break.",
                )
                surfaced_offsets = (
                    timedelta(seconds=5),
                    timedelta(seconds=1),
                    timedelta(seconds=1),
                )
                for index, (attempt_id, checkpoint_path, summary, offset) in enumerate(
                    zip(
                        surfaced_attempt_ids,
                        surfaced_checkpoint_paths,
                        surfaced_summaries,
                        surfaced_offsets,
                        strict=True,
                    ),
                    start=1,
                ):
                    surfaced_checkpoint_id = checkpoint_id(attempt_id, 1)
                    prior_attempt = AttemptModel(
                        attempt_id=attempt_id,
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
                            checkpoint_id=surfaced_checkpoint_id,
                            assignment_id=assignment.assignment_id,
                            assignment_key=assignment.assignment_key,
                            attempt_id=attempt_id,
                            flow_node_id=dispatch.flow_node_id,
                            node_key=assignment.node_key,
                            checkpoint_kind=CheckpointKind.TERMINAL.value,
                            outcome="retry",
                            summary=summary,
                            next_step=(
                                "Reuse this surfaced checkpoint before staging the next child."
                            ),
                            blockers_json=[],
                            risks_json=["Prior child evidence remains the deciding input."],
                            produced_artifact_claims_json=[],
                            produced_artifacts_json=[],
                            artifact_refs_json=[],
                            transient_refs_json=[],
                            task_memory_search_hints_json=[],
                            recorded_at=dispatch.rendered_at - offset,
                        )
                    )
                    await session.flush()
                    prior_attempt.latest_checkpoint_id = surfaced_checkpoint_id
                    session.add(
                        AttemptConsumedRefModel(
                            attempt_consumed_ref_id=attempt_consumed_ref_id(
                                dispatch.attempt_id,
                                90 + index,
                            ),
                            attempt_id=dispatch.attempt_id,
                            ref_kind="checkpoint",
                            slot=None,
                            version=None,
                            path=str(checkpoint_path),
                            description=(
                                "Latest surfaced prior-attempt checkpoint for this root turn."
                            ),
                            order_index=90 + index,
                        )
                    )
                    await session.flush()
                    await materialize_attempt_files(session, task_id, attempt_id)

                manifest = await build_dispatch_manifest_projection(
                    session,
                    task_id=task_id,
                    dispatch=dispatch,
                )
                bundle, _ = await render_dispatch_prompt(session, task_id, dispatch)

        current_checkpoint_path = (
            task_root / "_runtime" / "attempts" / current_attempt_id / "latest-checkpoint.md"
        )
        selected_checkpoint_path = surfaced_checkpoint_paths[2]
        assert selected_checkpoint_path.is_file()
        assert current_checkpoint_path.is_file()
        assert manifest.current_context.latest_checkpoint_path == current_checkpoint_path
        assert manifest.current_context.latest_relevant_checkpoint_path == selected_checkpoint_path
        assert f"- path: {selected_checkpoint_path}" in bundle.full_markdown
        assert f"- path: {current_checkpoint_path}" not in bundle.full_markdown
        assert "New surfaced checkpoint selected by path tie-break." in bundle.full_markdown
        assert (
            "Reuse this surfaced checkpoint before staging the next child." in bundle.full_markdown
        )
        assert "Prior child evidence remains the deciding input." in bundle.full_markdown
        assert (
            "Old surfaced checkpoint that should lose on recorded_at." not in bundle.full_markdown
        )
        assert (
            "New surfaced checkpoint that should lose on path tie-break."
            not in bundle.full_markdown
        )
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
                result = await _persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-transient-index-proof",
                )

                transient_path = task_root / "tmp" / "transfers" / "root" / "bootstrap-carryover.md"
                transient_path.parent.mkdir(parents=True, exist_ok=True)
                transient_path.write_text("keep this staged carryover", encoding="utf-8")

                assignment = await session.scalar(
                    select(AssignmentModel).where(
                        AssignmentModel.assignment_key == result.assignment.assignment_key
                    )
                )
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

                await materialize_attempt_files(
                    session,
                    task_id,
                    result.manifest.current_context.active_attempt_id,
                )

        transient_index_path = (
            task_root
            / "_runtime"
            / "attempts"
            / result.manifest.current_context.active_attempt_id
            / "transient-index.json"
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
