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
    ArtifactCurrentPointerModel,
    ArtifactPublicationModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowNodeModel,
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
from app.runtime.contracts import (
    EvidenceKind,
    EvidenceRef,
    RuntimeBootstrapResult,
    _RuntimeBootstrapProjectionInput,
)
from app.runtime.ids import checkpoint_id, dispatch_id_for_task
from app.runtime.launch import persist_bootstrap_runtime_from_precomputed
from app.runtime.launch.projection import _bootstrap_task_runtime_projection
from app.runtime.projection.materialize import (
    materialize_attempt_files,
    materialize_dispatch_files,
    materialize_manifest,
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


async def _seed_child_terminal_retry_checkpoint(
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
    assert "## Consumed Durable Refs" in result.prompt_bundle.full_markdown
    assert "- no current relevant checkpoint is surfaced" in result.prompt_bundle.full_markdown
    assert str(result.paths.criteria_path / "implementation_rules.v01.md") in (
        result.prompt_bundle.full_markdown
    )
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


def test_bootstrap_manifest_preserves_declaring_owner_for_inherited_criteria(
    tmp_path: Path,
) -> None:
    workflow_definition = _load_workflow_definition("normal_parent_first_release")
    compiled_plan = _compile_workflow(workflow_definition, revision_no=7)

    result = _bootstrap_task_runtime_projection(
        _RuntimeBootstrapProjectionInput(
            task_id="task_2026_criteria_owner_bootstrap",
            active_flow_revision_id="flowrev_criteria_owner_bootstrap",
            attempt_id="attempt.root.01",
            assignment_key="root.assign-01",
            dispatch_id="dispatch.root.01",
            task_root=tmp_path / "task-root",
            task_compose=_task_compose_payload("normal-parent-first-release"),
            workflow_definition=workflow_definition,
            compiled_plan=compiled_plan,
            role_policy_lookup=_load_seeded_lookup(),
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


async def test_live_materialization_localizes_external_surfaced_refs(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    shared_context = (tmp_path / "shared-context").resolve()
    task_id = "task_phase2_live_localization"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    shared_context.mkdir(parents=True)

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
                    compiler_version="phase-2-live-localization",
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
                )
                await materialize_manifest(session, task_id)
                await materialize_attempt_files(
                    session,
                    task_id,
                    result.manifest.current_context.active_attempt_id,
                )
                await _seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.FULL_PROMPT,
                )
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                manifest = await build_dispatch_manifest_projection(
                    session,
                    task_id=task_id,
                    dispatch=dispatch,
                )
                bundle, _ = await render_dispatch_prompt(session, task_id, dispatch)

        localized_criteria_path = (
            task_root / "tmp" / "transfers" / "localized" / ("implementation_rules.v01.md")
        )
        assignment_path = (
            task_root
            / "_runtime"
            / "attempts"
            / result.manifest.current_context.active_attempt_id
            / "assignment.json"
        )
        manifest_path = task_root / "_runtime" / "workflow-manifest.json"
        assignment_payload = json.loads(assignment_path.read_text(encoding="utf-8"))
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert localized_criteria_path.is_file()
        assert assignment_payload["criteria"][0]["path"] == str(localized_criteria_path)
        assert any(
            ref.kind == EvidenceKind.CRITERIA and ref.path == localized_criteria_path
            for ref in manifest.current_context.current_relevant_paths
        )
        root_node = next(
            node for node in manifest_payload["node_tree"] if node["node_key"] == "root"
        )
        assert root_node["criteria"][0]["path"] == str(localized_criteria_path)
        assert str(localized_criteria_path) in bundle.full_markdown
        assert str(shared_context / "criteria" / "implementation_rules.v01.md") not in (
            bundle.full_markdown
        )
    finally:
        await dispose_db_engine()


async def test_materialize_manifest_preserves_declaring_owner_for_inherited_criteria(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_manifest_criteria_owner"

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
                    compiler_version="phase-2-manifest-criteria-owner",
                    task_compose=_task_compose_payload("normal-parent-first-release"),
                )
                manifest = await materialize_manifest(session, task_id)

        manifest_payload = json.loads(
            (task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")
        )
        review_change = next(
            node for node in manifest.node_tree if node.node_key == "review_change"
        )
        review_change_payload = next(
            node for node in manifest_payload["node_tree"] if node["node_key"] == "review_change"
        )

        assert review_change.criteria[0].slot == "implementation_subtree_requirements"
        assert review_change.criteria[0].owner_node_key == "implementation_subtree"
        assert review_change_payload["criteria"][0]["owner_node_key"] == "implementation_subtree"
    finally:
        await dispose_db_engine()


async def test_parent_dispatch_surfaces_current_child_artifact_refs_from_current_pointers(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_child_artifact_refs"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    published_at = datetime.now(tz=UTC) - timedelta(seconds=3)

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
                    compiler_version="phase-2-child-artifact-refs",
                    task_compose=_task_compose_payload("normal-parent-first-release"),
                )
                state = await current_runtime_state(session, task_id)
                child_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == state.flow_revision.flow_revision_id,
                        FlowNodeModel.node_key == "implementation_subtree",
                    )
                )
                assert child_node is not None

                child_assignment = AssignmentModel(
                    assignment_id=f"{task_id}.implementation_subtree.assignment.db",
                    task_id=task_id,
                    flow_id=state.flow.flow_id,
                    flow_revision_id=state.flow_revision.flow_revision_id,
                    flow_node_id=child_node.flow_node_id,
                    assignment_key=f"{task_id}.implementation_subtree.assign-01",
                    node_key=child_node.node_key,
                    summary="Summarize the current change evidence for root review.",
                    instruction=None,
                    criteria_json=[],
                    consumes_json=[],
                    produces_json=[],
                    transient_refs_json=[],
                    task_memory_search_hints_json=[],
                    current_attempt_id=f"attempt.{task_id}.implementation_subtree.01",
                )
                child_attempt = AttemptModel(
                    attempt_id=f"attempt.{task_id}.implementation_subtree.01",
                    assignment_id=child_assignment.assignment_id,
                    assignment_key=child_assignment.assignment_key,
                    flow_node_id=child_node.flow_node_id,
                    task_id=task_id,
                    node_key=child_node.node_key,
                    status="succeeded",
                    opened_at=published_at,
                )
                artifact_path = (
                    task_root
                    / "outputs"
                    / "artifacts"
                    / child_node.node_key
                    / "subtree_review_report"
                    / "subtree_review_report.v01.md"
                )
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.write_text("root review summary", encoding="utf-8")
                session.add(child_assignment)
                session.add(child_attempt)
                session.add(
                    ArtifactPublicationModel(
                        artifact_publication_id=(
                            f"{task_id}.implementation_subtree.subtree_review_report.v01"
                        ),
                        task_id=task_id,
                        flow_node_id=child_node.flow_node_id,
                        owner_node_key=child_node.node_key,
                        slot="subtree_review_report",
                        version=1,
                        path=str(artifact_path),
                        description=(
                            "Current direct-child subtree review report for the root decision."
                        ),
                        assignment_key=child_assignment.assignment_key,
                        attempt_id=child_attempt.attempt_id,
                        published_at=published_at,
                        supersedes_version=None,
                        supersedes_path=None,
                    )
                )
                session.add(
                    ArtifactCurrentPointerModel(
                        artifact_current_pointer_id=(
                            f"{task_id}.implementation_subtree.subtree_review_report.current"
                        ),
                        task_id=task_id,
                        flow_node_id=child_node.flow_node_id,
                        owner_node_key=child_node.node_key,
                        slot="subtree_review_report",
                        current_version=1,
                        current_path=str(artifact_path),
                        description=(
                            "Current direct-child subtree review report for the root decision."
                        ),
                        assignment_key=child_assignment.assignment_key,
                        attempt_id=child_attempt.attempt_id,
                        published_at=published_at,
                        supersedes_path=None,
                    )
                )
                await session.flush()

                manifest = await materialize_manifest(session, task_id)
                dispatch = await _seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.FULL_PROMPT,
                    rendered_at=published_at + timedelta(seconds=1),
                )
                bundle, _ = await render_dispatch_prompt(session, task_id, dispatch)

        assert any(
            isinstance(ref, EvidenceRef)
            and ref.kind == EvidenceKind.ARTIFACT
            and ref.slot == "subtree_review_report"
            and ref.path == artifact_path
            for ref in manifest.current_context.current_relevant_paths
        )

        manifest_payload = json.loads(
            (task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")
        )
        assert any(
            ref["kind"] == "artifact"
            and ref["slot"] == "subtree_review_report"
            and ref["version"] == 1
            and ref["path"] == str(artifact_path)
            for ref in manifest_payload["current_context"]["current_relevant_paths"]
        )

        consumed_refs_section = bundle.full_markdown.split(
            "## Consumed Durable Refs",
            maxsplit=1,
        )[1].split("## Allowed Actions Now", maxsplit=1)[0]
        assert "subtree_review_report.v01.md" in consumed_refs_section
        assert "Current direct-child subtree review report for the root decision." in (
            consumed_refs_section
        )
        assert "version: 1" in consumed_refs_section
    finally:
        await dispose_db_engine()


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


async def test_materialize_dispatch_files_persists_raw_delivery_state_truth(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_raw_delivery_state"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    terminal_at = datetime.now(tz=UTC) - timedelta(seconds=7)

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
                    compiler_version="phase-2-raw-delivery-state",
                )
                await _seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.FULL_PROMPT,
                )
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
                assert dispatch is not None
                assert delivery_state is not None

                dispatch.accepted_boundary = "yield"
                delivery_state.transport_state = "provider_completed"
                delivery_state.controller_observation_state = "fenced"
                delivery_state.last_controller_terminal_at = terminal_at
                await session.flush()

                await materialize_dispatch_files(session, task_id, dispatch_id)

        delivery_state_payload = json.loads(
            (task_root / "_runtime" / "dispatch" / dispatch_id / "delivery-state.json").read_text(
                encoding="utf-8"
            )
        )
        assert delivery_state_payload["transport_state"] == "provider_completed"
        assert delivery_state_payload["controller_observation_state"] == "fenced"
        assert delivery_state_payload["last_controller_terminal_at"] == terminal_at.isoformat()
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


async def test_render_dispatch_prompt_rejects_same_session_without_previous_response_id(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_same_session_missing_basis"
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
                    compiler_version="phase-2-same-session-missing-basis",
                )
                await _seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.SAME_SESSION_CONTINUE,
                )
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None

                with pytest.raises(
                    ValueError,
                    match=("same_session_continue transport requests require previous_response_id"),
                ):
                    await render_dispatch_prompt(session, task_id, dispatch)
    finally:
        await dispose_db_engine()


async def test_render_dispatch_prompt_uses_controller_selected_checkpoint_truth(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_controller_selected_checkpoint"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    selected_child_attempt_id = f"attempt.{task_id}.implementation_subtree.00"
    current_child_attempt_id = f"attempt.{task_id}.implementation_subtree.01"
    selected_checkpoint_path = (
        task_root / "_runtime" / "attempts" / selected_child_attempt_id / "latest-checkpoint.md"
    )
    current_child_checkpoint_path = (
        task_root / "_runtime" / "attempts" / current_child_attempt_id / "latest-checkpoint.md"
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
                rendered_at = datetime.now(tz=UTC)
                result = await _persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-controller-selected-checkpoint",
                    task_compose=_task_compose_payload("normal-parent-first-release"),
                    latest_checkpoint=CheckpointProjection(
                        checkpoint_kind=CheckpointKind.PROGRESS,
                        handoff=CheckpointHandoff(
                            summary="Current root checkpoint for the active attempt.",
                            next_step="Use only the controller-selected checkpoint for redispatch.",
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
                    rendered_at=rendered_at,
                )
                assert dispatch.assignment_id is not None
                assert dispatch.attempt_id is not None
                assert dispatch.flow_node_id is not None

                assignment = await session.get(AssignmentModel, dispatch.assignment_id)
                child_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == dispatch.flow_revision_id,
                        FlowNodeModel.node_key == "implementation_subtree",
                    )
                )
                assert assignment is not None
                assert child_node is not None

                selected_checkpoint_path = await _seed_child_terminal_retry_checkpoint(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    dispatch=dispatch,
                    child_node=child_node,
                    attempt_id=selected_child_attempt_id,
                    assignment_suffix="selected",
                    assignment_summary=(
                        "Older child attempt selected explicitly for the next root review."
                    ),
                    checkpoint_summary=(
                        "Controller-selected child checkpoint for the next root review."
                    ),
                    checkpoint_next_step=(
                        "Re-read this explicit checkpoint before deciding the next turn."
                    ),
                    checkpoint_risk="This child checkpoint remains the selected handoff basis.",
                    recorded_at=rendered_at - timedelta(seconds=15),
                    make_current=False,
                )
                dispatch.relevant_checkpoint_attempt_id = selected_child_attempt_id

                current_child_checkpoint_path = await _seed_child_terminal_retry_checkpoint(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    dispatch=dispatch,
                    child_node=child_node,
                    attempt_id=current_child_attempt_id,
                    assignment_suffix="current",
                    assignment_summary=(
                        "Current child attempt with a newer checkpoint that should not win."
                    ),
                    checkpoint_summary=(
                        "Newer direct-child checkpoint that should stay ordinary context."
                    ),
                    checkpoint_next_step="Keep this visible as direct-child context only.",
                    checkpoint_risk="This checkpoint is newer but not controller-selected.",
                    recorded_at=rendered_at - timedelta(seconds=1),
                    make_current=True,
                )

                await materialize_attempt_files(session, task_id, selected_child_attempt_id)
                await materialize_attempt_files(session, task_id, current_child_attempt_id)

                manifest = await build_dispatch_manifest_projection(
                    session,
                    task_id=task_id,
                    dispatch=dispatch,
                )
                bundle, _ = await render_dispatch_prompt(session, task_id, dispatch)

        assert selected_checkpoint_path.is_file()
        assert current_child_checkpoint_path.is_file()
        assert manifest.current_context.latest_relevant_checkpoint_path == selected_checkpoint_path
        assert f"- path: {selected_checkpoint_path}" in bundle.full_markdown
        assert (
            "Controller-selected child checkpoint for the next root review." in bundle.full_markdown
        )
        assert (
            "Re-read this explicit checkpoint before deciding the next turn."
            in bundle.full_markdown
        )
        assert "Newer direct-child checkpoint that should stay ordinary context." not in (
            bundle.full_markdown
        )
    finally:
        await dispose_db_engine()


async def test_dispatch_manifest_surfaces_release_descendant_refs_from_controller_staging(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_release_descendant_surface"
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
                result = await _persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-release-descendant-surface",
                    task_compose=_task_compose_payload("normal-parent-first-release"),
                    latest_checkpoint=CheckpointProjection(
                        checkpoint_kind=CheckpointKind.PROGRESS,
                        handoff=CheckpointHandoff(
                            summary="Root is preparing a release reread turn.",
                            next_step="Use controller-staged descendant evidence for release.",
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
                assert dispatch is not None

                descendant_checkpoint_path = (
                    task_root
                    / "_runtime"
                    / "attempts"
                    / f"attempt.{task_id}.review_change.01"
                    / "latest-checkpoint.md"
                )
                descendant_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                descendant_checkpoint_path.write_text(
                    "staged descendant checkpoint", encoding="utf-8"
                )
                descendant_artifact_path = (
                    task_root
                    / "outputs"
                    / "artifacts"
                    / "review_change"
                    / "review_report"
                    / "review_report.v02.md"
                )
                descendant_artifact_path.parent.mkdir(parents=True, exist_ok=True)
                descendant_artifact_path.write_text("staged descendant artifact", encoding="utf-8")
                dispatch.release_precondition_descendant_refs_json = [
                    {
                        "kind": "checkpoint",
                        "path": str(descendant_checkpoint_path),
                        "description": (
                            "Controller-staged descendant checkpoint for the release reread."
                        ),
                    },
                    {
                        "kind": "artifact",
                        "slot": "review_report",
                        "version": 2,
                        "path": str(descendant_artifact_path),
                        "description": (
                            "Controller-staged descendant review artifact for the release reread."
                        ),
                    },
                ]
                await session.flush()

                manifest = await build_dispatch_manifest_projection(
                    session,
                    task_id=task_id,
                    dispatch=dispatch,
                )
                bundle, _ = await render_dispatch_prompt(session, task_id, dispatch)

        assert manifest.current_context.latest_relevant_checkpoint_path is None
        assert any(
            ref.path == descendant_checkpoint_path
            for ref in manifest.current_context.current_relevant_paths
        )
        assert any(
            isinstance(ref, EvidenceRef)
            and ref.kind == EvidenceKind.ARTIFACT
            and ref.path == descendant_artifact_path
            for ref in manifest.current_context.current_relevant_paths
        )

        consumed_refs_section = bundle.full_markdown.split(
            "## Consumed Durable Refs",
            maxsplit=1,
        )[1].split("## Allowed Actions Now", maxsplit=1)[0]
        assert "attempt.task_phase2_release_descendant_surface.review_change.01" in (
            consumed_refs_section
        )
        assert "review_report.v02.md" in consumed_refs_section
        assert "Controller-staged descendant checkpoint for the release reread." in (
            consumed_refs_section
        )
        assert "Controller-staged descendant review artifact for the release reread." in (
            consumed_refs_section
        )
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


async def test_materialize_attempt_files_includes_owner_node_key_in_artifact_index(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_artifact_index_owner"
    attempt_id = f"attempt.{task_id}.root.01"
    artifact_path = (
        task_root / "outputs" / "artifacts" / "root" / "release_summary" / "release_summary.v01.md"
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

        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("release summary", encoding="utf-8")

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                result = await _persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-artifact-index-owner",
                    latest_checkpoint=CheckpointProjection(
                        checkpoint_kind=CheckpointKind.PROGRESS,
                        handoff=CheckpointHandoff(
                            summary="Root published the release summary artifact.",
                            next_step="Stage downstream review with the current durable output.",
                        ),
                        produced_artifacts=(
                            EvidenceRef(
                                kind=EvidenceKind.ARTIFACT,
                                slot="release_summary",
                                version=1,
                                path=artifact_path,
                                description="Release summary for downstream review.",
                            ),
                        ),
                    ),
                )
                await materialize_attempt_files(session, task_id, attempt_id)

        artifact_index_path = (
            task_root / "_runtime" / "attempts" / attempt_id / "artifact-index.json"
        )
        artifact_index = json.loads(artifact_index_path.read_text(encoding="utf-8"))
        assert artifact_index["attempt_id"] == attempt_id
        assert artifact_index["node_key"] == "root"
        assert artifact_index["assignment_key"] == result.assignment.assignment_key
        assert artifact_index["publications"] == [
            {
                "owner_node_key": "root",
                "slot": "release_summary",
                "version": 1,
                "path": str(artifact_path),
                "description": "Release summary for downstream review.",
                "published_at": artifact_index["publications"][0]["published_at"],
                "became_current": True,
            }
        ]
    finally:
        await dispose_db_engine()
