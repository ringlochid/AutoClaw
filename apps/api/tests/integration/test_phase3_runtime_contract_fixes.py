from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import cast

import pytest
from app import cli
from app.api.errors import runtime_exception_failure
from app.config import get_settings
from app.db import (
    AssignmentModel,
    AttemptCheckpointModel,
    DispatchCallbackBindingModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
)
from app.db.session import dispose_db_engine, get_session_factory
from app.main import create_app
from app.runtime.projection import materialize_manifest
from app.schemas.definitions.workflow import WorkflowDefinitionFile
from app.schemas.operation_failure import OperationFailureCode
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_seed import (
    launch_seeded_runtime,
    load_workflow_definition,
    task_compose_payload,
)

OPERATOR_HEADERS = {"X-AutoClaw-API-Key": "api-test-key"}


@pytest.mark.parametrize(
    ("exc", "expected_summary"),
    [
        (
            ValueError("missing artifact provider for slot 'brief'"),
            "missing artifact provider for slot 'brief'",
        ),
        (
            ValueError("missing current artifact for slot 'brief'"),
            "missing current artifact for slot 'brief'",
        ),
        (
            FileNotFoundError("produced artifact does not exist: /tmp/missing.txt"),
            "produced artifact does not exist: /tmp/missing.txt",
        ),
    ],
)
def test_runtime_exception_failure_maps_semantic_missing_dependencies_to_422(
    exc: Exception, expected_summary: str
) -> None:
    status_code, failure = runtime_exception_failure(exc)

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_RESOURCE
    assert failure.summary == expected_summary
    assert failure.retryable is False


def test_runtime_exception_failure_keeps_unknown_target_ids_on_404() -> None:
    status_code, failure = runtime_exception_failure(ValueError("unknown task_id 'task-1'"))

    assert status_code == 404
    assert failure.code == OperationFailureCode.MISSING_RESOURCE
    assert failure.summary == "unknown task_id 'task-1'"


@pytest.mark.parametrize(
    ("summary", "expected_code", "expected_next_step"),
    [
        (
            "green release precondition is stale",
            OperationFailureCode.STALE_ASSIGNMENT,
            "Reread the current assignment projection and resend the request only if the "
            "same assignment is still current.",
        ),
        (
            "blocked release precondition is stale",
            OperationFailureCode.STALE_ASSIGNMENT,
            "Reread the current assignment projection and resend the request only if the "
            "same assignment is still current.",
        ),
        (
            (
                "release_green requires current surfaced evidence: "
                "missing current artifact for slot 'brief'"
            ),
            OperationFailureCode.STALE_CHECKPOINT,
            "Reread the latest relevant checkpoint and current surfaced refs, then decide "
            "again from that newer handover.",
        ),
        (
            (
                "release_blocked requires current checkpoint evidence: "
                "current checkpoint projection files are missing"
            ),
            OperationFailureCode.STALE_CHECKPOINT,
            "Reread the latest relevant checkpoint and current surfaced refs, then decide "
            "again from that newer handover.",
        ),
    ],
)
def test_runtime_exception_failure_maps_stale_runtime_basis_to_409(
    summary: str,
    expected_code: OperationFailureCode,
    expected_next_step: str,
) -> None:
    status_code, failure = runtime_exception_failure(ValueError(summary))

    assert status_code == 409
    assert failure.code == expected_code
    assert failure.summary == summary
    assert failure.retryable is True
    assert failure.suggested_next_step == expected_next_step


def test_runtime_exception_failure_keeps_missing_required_publication_on_422() -> None:
    summary = "missing required publication for assignment 'assign.task.root.01'"

    status_code, failure = runtime_exception_failure(ValueError(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_REQUIRED_PUBLICATION
    assert failure.summary == summary
    assert failure.retryable is False


def test_runtime_exception_failure_keeps_non_stale_invalid_requests_on_422() -> None:
    summary = "release_blocked requires the current root basis to be terminal-blocked"

    status_code, failure = runtime_exception_failure(ValueError(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_REQUIRED_PUBLICATION
    assert failure.summary == summary
    assert failure.retryable is False
    assert failure.suggested_next_step == (
        "Publish the blocked checkpoint and any required blocked-basis evidence first, "
        "then retry release_blocked."
    )


def test_runtime_exception_failure_maps_budget_exhausted_to_422() -> None:
    summary = "child assignment budget exhausted for this path"

    status_code, failure = runtime_exception_failure(ValueError(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.BUDGET_EXHAUSTED
    assert failure.summary == summary
    assert failure.retryable is False
    assert failure.suggested_next_step == (
        "Surface the latest terminal checkpoint to the relevant parent or root so it can "
        "choose a fresh assignment or another legal path."
    )


async def _prepare_runtime_db(tmp_path: Path) -> Path:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
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
    return config_path


async def _persist_bootstrap(
    *,
    config_path: Path,
    task_id: str,
    task_root: Path,
    workflow_definition: WorkflowDefinitionFile,
    revision_no: int,
) -> None:
    with cli._command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        async with session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=task_root,
                task_compose=task_compose_payload(workflow_definition.id),
                compiler_version=f"phase-3-contract-fixes-r{revision_no}",
                workflow_definition=workflow_definition,
            )


async def _current_session_key(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    client: AsyncClient | None = None,
    expected_active_flow_revision_id: str | None = None,
) -> str:
    if client is not None and expected_active_flow_revision_id is not None:
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            assert flow.current_open_dispatch_id is not None
            dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
            assert dispatch is not None
            dispatch.delivery_status = "provider_completed"
            await session.commit()
        resumed = await client.post(
            f"/runtime/tasks/{task_id}/continue",
            headers=OPERATOR_HEADERS,
            params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
        )
        assert resumed.status_code == 200
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        binding = await session.get(
            DispatchCallbackBindingModel,
            f"dispatch-callback-binding.{flow.current_open_dispatch_id}",
        )
        assert binding is not None
        assert binding.binding_status == "live"
        assert isinstance(binding.session_key, str)
        return binding.session_key


async def _drive_minimal_child_to_green(
    *,
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    task_root: Path,
) -> tuple[str, str]:
    root_session_key = await _current_session_key(
        session_factory=session_factory,
        task_id=task_id,
    )
    runtime_read = await client.get(
        f"/runtime/tasks/{task_id}",
        headers=OPERATOR_HEADERS,
    )
    assert runtime_read.status_code == 200
    assign = await client.post(
        f"/callback/tasks/{task_id}/tools/assign_child",
        headers={"X-Autoclaw-Session-Key": root_session_key},
        json={
            "tool_name": "assign_child",
            "payload": {
                "child_node_key": "implement_change",
                "assignment_intent": {"summary": "go", "instruction": "go"},
            },
            "expected_structural_revision_id": runtime_read.json()["active_flow_revision_id"],
        },
    )
    assert assign.status_code == 200
    yielded = await client.post(
        f"/callback/tasks/{task_id}/boundary",
        headers={"X-Autoclaw-Session-Key": root_session_key},
        json={"boundary": "yield"},
    )
    assert yielded.status_code == 200

    worker_session_key = await _current_session_key(
        session_factory=session_factory,
        task_id=task_id,
        client=client,
        expected_active_flow_revision_id=yielded.json()["flow"]["active_flow_revision_id"],
    )
    patch_file = task_root / "workspace" / "change_patch.diff"
    patch_file.parent.mkdir(parents=True, exist_ok=True)
    patch_file.write_text("diff --git a b", encoding="utf-8")
    verification_file = task_root / "workspace" / "verification_report.md"
    verification_file.write_text("verification passed", encoding="utf-8")
    checkpoint = await client.post(
        f"/callback/tasks/{task_id}/checkpoint",
        headers={"X-Autoclaw-Session-Key": worker_session_key},
        json={
            "checkpoint": {
                "checkpoint_kind": "terminal",
                "outcome": "green",
                "handoff": {
                    "summary": "done",
                    "next_step": "root should verify the bounded change and close the flow.",
                },
                "produced_artifacts": [
                    {"slot": "change_patch", "path": str(patch_file)},
                    {"slot": "verification_report", "path": str(verification_file)},
                ],
            }
        },
    )
    assert checkpoint.status_code == 200
    worker_green = await client.post(
        f"/callback/tasks/{task_id}/boundary",
        headers={"X-Autoclaw-Session-Key": worker_session_key},
        json={"boundary": "green"},
    )
    assert worker_green.status_code == 200

    root_session_key = await _current_session_key(
        session_factory=session_factory,
        task_id=task_id,
        client=client,
        expected_active_flow_revision_id=worker_green.json()["flow"]["active_flow_revision_id"],
    )
    resumed_root = await client.get(
        f"/runtime/tasks/{task_id}",
        headers=OPERATOR_HEADERS,
    )
    assert resumed_root.status_code == 200
    return root_session_key, resumed_root.json()["active_flow_revision_id"]


@pytest.mark.asyncio
async def test_release_green_uses_relational_children_and_maps_stale_checkpoint_to_409(
    tmp_path: Path,
) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = load_workflow_definition("minimal_implement_change")

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_release_relational_child",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                root_session_key, active_flow_revision_id = await _drive_minimal_child_to_green(
                    client=client,
                    session_factory=session_factory,
                    task_id="task_release_relational_child",
                    task_root=task_root,
                )

                async with session_factory() as session:
                    flow = await session.scalar(
                        select(FlowModel).where(
                            FlowModel.task_id == "task_release_relational_child"
                        )
                    )
                    assert flow is not None
                    child_node = await session.scalar(
                        select(FlowNodeModel).where(
                            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                            FlowNodeModel.node_key == "implement_change",
                        )
                    )
                    assert child_node is not None
                    assert child_node.current_assignment_id is not None
                    child_assignment = await session.get(
                        AssignmentModel,
                        child_node.current_assignment_id,
                    )
                    assert child_assignment is not None
                    assert child_assignment.current_attempt_id is not None
                    child_node.parent_node_key = child_node.node_key
                    checkpoint_dir = (
                        task_root / "_runtime" / "attempts" / child_assignment.current_attempt_id
                    )
                    checkpoint_json = checkpoint_dir / "latest-checkpoint.json"
                    checkpoint_md = checkpoint_dir / "latest-checkpoint.md"
                    assert checkpoint_json.is_file()
                    assert checkpoint_md.is_file()
                    checkpoint_json.unlink()
                    checkpoint_md.unlink()
                    await session.commit()

                release = await client.post(
                    "/callback/tasks/task_release_relational_child/tools/release_green",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "release_green",
                        "payload": {},
                        "expected_structural_revision_id": active_flow_revision_id,
                    },
                )

                assert release.status_code == 409
                detail = release.json()["detail"]
                assert detail["code"] == "stale_checkpoint"
                assert "requires current checkpoint evidence" in detail["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_release_green_keeps_missing_required_publication_on_422(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = load_workflow_definition("minimal_implement_change")

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_release_missing_publication",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                root_session_key, active_flow_revision_id = await _drive_minimal_child_to_green(
                    client=client,
                    session_factory=session_factory,
                    task_id="task_release_missing_publication",
                    task_root=task_root,
                )

                async with session_factory() as session:
                    flow = await session.scalar(
                        select(FlowModel).where(
                            FlowModel.task_id == "task_release_missing_publication"
                        )
                    )
                    assert flow is not None
                    root_node = await session.scalar(
                        select(FlowNodeModel).where(
                            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                            FlowNodeModel.node_key == "root",
                        )
                    )
                    assert root_node is not None
                    assert root_node.current_assignment_id is not None
                    root_assignment = await session.get(
                        AssignmentModel,
                        root_node.current_assignment_id,
                    )
                    assert root_assignment is not None
                    root_assignment.produces_json = [
                        {
                            "slot": "missing_release_basis",
                            "description": "Synthetic required release basis for route mapping.",
                            "file_hint": "missing_release_basis.md",
                        }
                    ]
                    await session.commit()

                release = await client.post(
                    "/callback/tasks/task_release_missing_publication/tools/release_green",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "release_green",
                        "payload": {},
                        "expected_structural_revision_id": active_flow_revision_id,
                    },
                )

                assert release.status_code == 422
                detail = release.json()["detail"]
                assert detail["code"] == "missing_required_publication"
                assert detail["summary"].startswith("missing required publication")
    finally:
        await dispose_db_engine()


def _child_defaults_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "child-defaults-consumes-review",
            "description": "Validate runtime structural replan inheritance.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "produces": {
                    "artifacts": [
                        {
                            "slot": "brief",
                            "description": "Shared briefing artifact.",
                        }
                    ]
                },
                "children": [
                    {
                        "id": "subtree",
                        "role": "planning_lead",
                        "policy": "standard-parent-planning",
                        "description": "Parent subtree.",
                        "child_defaults": {
                            "consumes": {"artifacts": [{"slot": "brief"}]},
                        },
                        "children": [
                            {
                                "id": "existing_child",
                                "role": "researcher",
                                "description": "Existing worker child.",
                            }
                        ],
                    }
                ],
            },
        }
    )


def _criteria_defaults_refresh_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "criteria-defaults-refresh-review",
            "description": "Validate inherited criteria refresh during runtime replan.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "subtree",
                        "role": "planning_lead",
                        "policy": "standard-parent-planning",
                        "description": "Parent subtree.",
                        "criteria": [
                            {
                                "slot": "review_gate",
                                "description": "Original review gate.",
                                "criteria": ["Child work must satisfy the current review gate."],
                            }
                        ],
                        "child_defaults": {
                            "criteria": ["review_gate"],
                        },
                        "children": [
                            {
                                "id": "collect_cases",
                                "role": "researcher",
                                "description": "Collect QA cases.",
                            }
                        ],
                    }
                ],
            },
        }
    )


def _dependency_dedupe_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "dependency-dedupe-review",
            "description": "Validate manifest dependency dedupe during rematerialization.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "criteria": [
                    {
                        "slot": "acceptance_gate",
                        "description": "Acceptance gate.",
                        "criteria": ["Child work must satisfy the shared acceptance gate."],
                    }
                ],
                "produces": {
                    "artifacts": [
                        {
                            "slot": "brief",
                            "description": "Shared brief.",
                        }
                    ]
                },
                "children": [
                    {
                        "id": "implement_change",
                        "role": "engineer",
                        "description": "Implement the change.",
                        "consumes": {
                            "artifacts": [{"slot": "brief"}],
                            "criteria": [{"slot": "acceptance_gate"}],
                        },
                    }
                ],
            },
        }
    )


def _root_descendant_replan_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "root-descendant-replan-review",
            "description": "Validate root whole-tree replan breadth without widening parent scope.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "subtree",
                        "role": "planning_lead",
                        "policy": "standard-parent-planning",
                        "description": "Parent subtree.",
                        "children": [
                            {
                                "id": "nested_parent",
                                "role": "planning_lead",
                                "policy": "standard-parent-planning",
                                "description": "Nested subtree.",
                                "children": [
                                    {
                                        "id": "existing_leaf",
                                        "role": "researcher",
                                        "description": "Leaf worker.",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        }
    )


@pytest.mark.asyncio
async def test_pause_revokes_callback_route_access(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = load_workflow_definition("normal_parent_first_release")

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_pause_contract",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=7,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            session_key = await _current_session_key(
                session_factory=session_factory,
                task_id="task_pause_contract",
            )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    "/runtime/tasks/task_pause_contract",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                pause = await client.post(
                    "/runtime/tasks/task_pause_contract/pause",
                    headers=OPERATOR_HEADERS,
                    params={
                        "expected_active_flow_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ]
                    },
                )
                assert pause.status_code == 200
                rejected = await client.post(
                    "/callback/tasks/task_pause_contract/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implementation_subtree",
                            "assignment_intent": {"summary": "blocked", "instruction": "blocked"},
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert rejected.status_code == 409
                assert "callback session key" in rejected.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_pause_continue_preserves_staged_child_assignment(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = load_workflow_definition("normal_parent_first_release")

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_pause_resume_stage",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=7,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            root_session_key = await _current_session_key(
                session_factory=session_factory,
                task_id="task_pause_resume_stage",
            )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    "/runtime/tasks/task_pause_resume_stage",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                assign = await client.post(
                    "/callback/tasks/task_pause_resume_stage/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implementation_subtree",
                            "assignment_intent": {"summary": "go", "instruction": "go"},
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign.status_code == 200

                pause = await client.post(
                    "/runtime/tasks/task_pause_resume_stage/pause",
                    headers=OPERATOR_HEADERS,
                    params={
                        "expected_active_flow_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ]
                    },
                )
                assert pause.status_code == 200

                resumed = await client.post(
                    "/runtime/tasks/task_pause_resume_stage/continue",
                    headers=OPERATOR_HEADERS,
                    params={
                        "expected_active_flow_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ]
                    },
                )
                assert resumed.status_code == 200

                resumed_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_pause_resume_stage",
                )
                second_assign = await client.post(
                    "/callback/tasks/task_pause_resume_stage/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": resumed_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "review_change",
                            "assignment_intent": {
                                "summary": "should fail",
                                "instruction": "should fail",
                            },
                        },
                        "expected_structural_revision_id": resumed.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert second_assign.status_code == 422
                assert "staging a child assignment" in second_assign.json()["detail"]["summary"]

                yielded = await client.post(
                    "/callback/tasks/task_pause_resume_stage/boundary",
                    headers={"X-Autoclaw-Session-Key": resumed_session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200
                assert yielded.json()["flow"]["current_node_key"] == "root"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_checkpoint_route_rejects_undeclared_artifact_slot(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = load_workflow_definition("minimal_implement_change")

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_bad_artifact",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=4,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                root_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_bad_artifact",
                )
                runtime_read = await client.get(
                    "/runtime/tasks/task_bad_artifact",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                assign = await client.post(
                    "/callback/tasks/task_bad_artifact/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implement_change",
                            "assignment_intent": {"summary": "go", "instruction": "go"},
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign.status_code == 200
                yielded = await client.post(
                    "/callback/tasks/task_bad_artifact/boundary",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200

                worker_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_bad_artifact",
                    client=client,
                    expected_active_flow_revision_id=yielded.json()["flow"][
                        "active_flow_revision_id"
                    ],
                )
                bad_artifact = task_root / "workspace" / "typo_artifact.md"
                bad_artifact.parent.mkdir(parents=True, exist_ok=True)
                bad_artifact.write_text("typo artifact", encoding="utf-8")
                checkpoint = await client.post(
                    "/callback/tasks/task_bad_artifact/checkpoint",
                    headers={"X-Autoclaw-Session-Key": worker_session_key},
                    json={
                        "checkpoint": {
                            "checkpoint_kind": "terminal",
                            "outcome": "green",
                            "handoff": {
                                "summary": "done",
                                "next_step": "close",
                            },
                            "produced_artifacts": [
                                {"slot": "typo_output", "path": str(bad_artifact)}
                            ],
                        }
                    },
                )
                assert checkpoint.status_code == 422
                assert checkpoint.json()["detail"]["code"] == "illegal_state"
                assert "not declared" in checkpoint.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_manifest_rematerialization_keeps_workflow_description(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = load_workflow_definition("normal_parent_first_release")

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_manifest_description",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=7,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                manifest = await materialize_manifest(session, "task_manifest_description")
                manifest_json = json.loads(
                    (task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")
                )
                assert manifest.workflow.description == workflow_definition.description
                assert manifest_json["workflow"]["description"] == workflow_definition.description
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_manifest_rematerialization_dedupes_node_dependency_lists(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = _dependency_dedupe_workflow()

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_manifest_dependency_dedupe",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                manifest = await materialize_manifest(session, "task_manifest_dependency_dedupe")
                node_by_key = {node.node_key: node for node in manifest.node_tree}
                assert node_by_key["implement_change"].depends_on_node_keys == ("root",)
                assert node_by_key["root"].depended_on_by_node_keys == ("implement_change",)
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_checkpoint_transient_surface_under_task_root_is_copied_into_transfers(
    tmp_path: Path,
) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = load_workflow_definition("minimal_implement_change")

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_transient_copy",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=4,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                root_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_transient_copy",
                )
                runtime_read = await client.get(
                    "/runtime/tasks/task_transient_copy",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                assign = await client.post(
                    "/callback/tasks/task_transient_copy/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "implement_change",
                            "assignment_intent": {"summary": "go", "instruction": "go"},
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign.status_code == 200
                yielded = await client.post(
                    "/callback/tasks/task_transient_copy/boundary",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200

                worker_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_transient_copy",
                    client=client,
                    expected_active_flow_revision_id=yielded.json()["flow"][
                        "active_flow_revision_id"
                    ],
                )
                patch_file = task_root / "workspace" / "change_patch.diff"
                patch_file.parent.mkdir(parents=True, exist_ok=True)
                patch_file.write_text("diff --git a b", encoding="utf-8")
                transient_file = task_root / "workspace" / "workspace-note.md"
                transient_file.write_text("mutable workspace note", encoding="utf-8")
                checkpoint = await client.post(
                    "/callback/tasks/task_transient_copy/checkpoint",
                    headers={"X-Autoclaw-Session-Key": worker_session_key},
                    json={
                        "checkpoint": {
                            "checkpoint_kind": "terminal",
                            "outcome": "green",
                            "handoff": {
                                "summary": "done",
                                "next_step": "close",
                            },
                            "produced_artifacts": [
                                {"slot": "change_patch", "path": str(patch_file)}
                            ],
                            "transient_surfaces": [
                                {
                                    "path": str(transient_file),
                                    "description": "Workspace handoff note.",
                                }
                            ],
                        }
                    },
                )
                assert checkpoint.status_code == 200

            async with session_factory() as session:
                checkpoint_row = await session.scalar(
                    select(AttemptCheckpointModel).order_by(
                        AttemptCheckpointModel.recorded_at.desc()
                    )
                )
                assert checkpoint_row is not None
                transient_path = Path(cast(str, checkpoint_row.transient_refs_json[0]["path"]))
                assert await asyncio.to_thread(transient_path.is_file)
                assert transient_path.is_relative_to(task_root / "tmp" / "transfers")
                assert transient_path != transient_file.resolve()
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_add_child_persists_subtree_and_inherits_child_default_consumes(
    tmp_path: Path,
) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = _child_defaults_workflow()

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_replan_subtree",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            root_session_key = await _current_session_key(
                session_factory=session_factory,
                task_id="task_replan_subtree",
            )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    "/runtime/tasks/task_replan_subtree",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                assign = await client.post(
                    "/callback/tasks/task_replan_subtree/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "subtree",
                            "assignment_intent": {"summary": "go", "instruction": "go"},
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign.status_code == 200
                yielded = await client.post(
                    "/callback/tasks/task_replan_subtree/boundary",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200

                subtree_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_replan_subtree",
                    client=client,
                    expected_active_flow_revision_id=yielded.json()["flow"][
                        "active_flow_revision_id"
                    ],
                )
                add_child = await client.post(
                    "/callback/tasks/task_replan_subtree/tools/add_child",
                    headers={"X-Autoclaw-Session-Key": subtree_session_key},
                    json={
                        "tool_name": "add_child",
                        "payload": {
                            "child": {
                                "node_key": "qa_sweep",
                                "role": "planning_lead",
                                "description": "Parent QA subtree.",
                                "children": [
                                    {
                                        "node_key": "collect_cases",
                                        "role": "researcher",
                                        "description": "Collect QA cases.",
                                    }
                                ],
                            }
                        },
                        "expected_structural_revision_id": yielded.json()["flow"][
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert add_child.status_code == 200

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_replan_subtree")
                )
                assert flow is not None
                nodes = list(
                    await session.scalars(
                        select(FlowNodeModel)
                        .where(FlowNodeModel.flow_revision_id == flow.active_flow_revision_id)
                        .order_by(FlowNodeModel.order_index.asc())
                    )
                )
                node_by_key = {node.node_key: node for node in nodes}
                assert "qa_sweep" in node_by_key
                assert "collect_cases" in node_by_key
                assert node_by_key["qa_sweep"].child_node_keys_json == ["collect_cases"]
                assert node_by_key["collect_cases"].parent_node_key == "qa_sweep"
                assert node_by_key["qa_sweep"].consumes_json == {
                    "artifacts": [{"slot": "brief", "required": True}],
                    "criteria": None,
                }
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_assign_child_missing_required_artifact_is_semantic_invalid(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = _child_defaults_workflow()

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_missing_artifact_assign",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            root_session_key = await _current_session_key(
                session_factory=session_factory,
                task_id="task_missing_artifact_assign",
            )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    "/runtime/tasks/task_missing_artifact_assign",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                assign = await client.post(
                    "/callback/tasks/task_missing_artifact_assign/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "subtree",
                            "assignment_intent": {"summary": "go", "instruction": "go"},
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign.status_code == 200
                yielded = await client.post(
                    "/callback/tasks/task_missing_artifact_assign/boundary",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200

                subtree_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_missing_artifact_assign",
                    client=client,
                    expected_active_flow_revision_id=yielded.json()["flow"][
                        "active_flow_revision_id"
                    ],
                )
                missing_artifact = await client.post(
                    "/callback/tasks/task_missing_artifact_assign/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": subtree_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "existing_child",
                            "assignment_intent": {"summary": "go", "instruction": "go"},
                        },
                        "expected_structural_revision_id": yielded.json()["flow"][
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert missing_artifact.status_code == 422
                assert missing_artifact.json()["detail"]["code"] == "missing_resource"
                assert "missing current artifact" in missing_artifact.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_add_child_rejects_unknown_child_default_criteria_slot(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = _child_defaults_workflow()

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_invalid_child_defaults",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            root_session_key = await _current_session_key(
                session_factory=session_factory,
                task_id="task_invalid_child_defaults",
            )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    "/runtime/tasks/task_invalid_child_defaults",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                assign = await client.post(
                    "/callback/tasks/task_invalid_child_defaults/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "subtree",
                            "assignment_intent": {"summary": "go", "instruction": "go"},
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign.status_code == 200
                yielded = await client.post(
                    "/callback/tasks/task_invalid_child_defaults/boundary",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200

                subtree_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_invalid_child_defaults",
                    client=client,
                    expected_active_flow_revision_id=yielded.json()["flow"][
                        "active_flow_revision_id"
                    ],
                )
                add_child = await client.post(
                    "/callback/tasks/task_invalid_child_defaults/tools/add_child",
                    headers={"X-Autoclaw-Session-Key": subtree_session_key},
                    json={
                        "tool_name": "add_child",
                        "payload": {
                            "child": {
                                "node_key": "bad_parent",
                                "role": "planning_lead",
                                "description": "Bad parent subtree.",
                                "criteria": [
                                    {
                                        "slot": "known_gate",
                                        "description": "Known gate.",
                                        "criteria": ["Known gate must stay satisfied."],
                                    }
                                ],
                                "child_defaults": {
                                    "criteria": ["missing_gate", "missing_gate"],
                                },
                                "children": [
                                    {
                                        "node_key": "bad_leaf",
                                        "role": "researcher",
                                        "description": "Bad leaf.",
                                    }
                                ],
                            }
                        },
                        "expected_structural_revision_id": yielded.json()["flow"][
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert add_child.status_code == 422
                assert add_child.json()["detail"]["code"] == "illegal_state"
                assert (
                    "unknown local criteria slot 'missing_gate'"
                    in add_child.json()["detail"]["summary"]
                )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_update_child_refreshes_inherited_criteria_for_descendants(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = _criteria_defaults_refresh_workflow()

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_refresh_defaults",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            root_session_key = await _current_session_key(
                session_factory=session_factory,
                task_id="task_refresh_defaults",
            )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    "/runtime/tasks/task_refresh_defaults",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                update_child = await client.post(
                    "/callback/tasks/task_refresh_defaults/tools/update_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "update_child",
                        "payload": {
                            "child_node_key": "subtree",
                            "patch": {
                                "criteria": [
                                    {
                                        "slot": "review_gate",
                                        "description": "Updated review gate.",
                                        "criteria": ["Updated review gate must now hold."],
                                    }
                                ]
                            },
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert update_child.status_code == 200

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_refresh_defaults")
                )
                assert flow is not None
                nodes = list(
                    await session.scalars(
                        select(FlowNodeModel)
                        .where(FlowNodeModel.flow_revision_id == flow.active_flow_revision_id)
                        .order_by(FlowNodeModel.order_index.asc())
                    )
                )
                node_by_key = {node.node_key: node for node in nodes}
                collect_cases_criteria = node_by_key["collect_cases"].criteria_json
                assert len(collect_cases_criteria) == 1
                assert collect_cases_criteria[0]["slot"] == "review_gate"
                assert collect_cases_criteria[0]["description"] == "Updated review gate."
                assert collect_cases_criteria[0]["criteria"] == [
                    "Updated review gate must now hold."
                ]
                assert collect_cases_criteria[0]["version"] == 2
                assert str(collect_cases_criteria[0]["path"]).endswith("review_gate.v02.md")
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_root_can_update_and_remove_explicit_descendant_nodes(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = _root_descendant_replan_workflow()

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_root_descendant_replan",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            root_session_key = await _current_session_key(
                session_factory=session_factory,
                task_id="task_root_descendant_replan",
            )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    "/runtime/tasks/task_root_descendant_replan",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                add_child = await client.post(
                    "/callback/tasks/task_root_descendant_replan/tools/add_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "add_child",
                        "payload": {
                            "target_parent_node_key": "nested_parent",
                            "child": {
                                "node_key": "qa_probe",
                                "role": "researcher",
                                "description": "Added under the nested parent by root.",
                            },
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert add_child.status_code == 200
                update_child = await client.post(
                    "/callback/tasks/task_root_descendant_replan/tools/update_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "update_child",
                        "payload": {
                            "child_node_key": "existing_leaf",
                            "patch": {"description": "Updated by the root whole-tree replan."},
                        },
                        "expected_structural_revision_id": add_child.json()["flow"][
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert update_child.status_code == 200

                async with session_factory() as session:
                    flow = await session.scalar(
                        select(FlowModel).where(FlowModel.task_id == "task_root_descendant_replan")
                    )
                    assert flow is not None
                    leaf = await session.scalar(
                        select(FlowNodeModel).where(
                            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                            FlowNodeModel.node_key == "existing_leaf",
                        )
                    )
                    qa_probe = await session.scalar(
                        select(FlowNodeModel).where(
                            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                            FlowNodeModel.node_key == "qa_probe",
                        )
                    )
                    nested_parent = await session.scalar(
                        select(FlowNodeModel).where(
                            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                            FlowNodeModel.node_key == "nested_parent",
                        )
                    )
                    assert leaf is not None
                    assert qa_probe is not None
                    assert nested_parent is not None
                    assert leaf.description == "Updated by the root whole-tree replan."
                    assert qa_probe.parent_node_key == "nested_parent"
                    assert nested_parent.child_node_keys_json == ["existing_leaf", "qa_probe"]

                remove_child = await client.post(
                    "/callback/tasks/task_root_descendant_replan/tools/remove_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "remove_child",
                        "payload": {
                            "child_node_key": "nested_parent",
                        },
                        "expected_structural_revision_id": update_child.json()["flow"][
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert remove_child.status_code == 200

            async with session_factory() as session:
                flow = await session.scalar(
                    select(FlowModel).where(FlowModel.task_id == "task_root_descendant_replan")
                )
                assert flow is not None
                nodes = list(
                    await session.scalars(
                        select(FlowNodeModel)
                        .where(FlowNodeModel.flow_revision_id == flow.active_flow_revision_id)
                        .order_by(FlowNodeModel.order_index.asc())
                    )
                )
                node_by_key = {node.node_key: node for node in nodes}
                assert "nested_parent" not in node_by_key
                assert "existing_leaf" not in node_by_key
                assert node_by_key["subtree"].child_node_keys_json == []
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_non_root_parent_cannot_update_non_direct_descendant(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = _root_descendant_replan_workflow()

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_parent_descendant_scope",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            root_session_key = await _current_session_key(
                session_factory=session_factory,
                task_id="task_parent_descendant_scope",
            )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    "/runtime/tasks/task_parent_descendant_scope",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                assign = await client.post(
                    "/callback/tasks/task_parent_descendant_scope/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "subtree",
                            "assignment_intent": {"summary": "go", "instruction": "go"},
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign.status_code == 200
                yielded = await client.post(
                    "/callback/tasks/task_parent_descendant_scope/boundary",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200

                subtree_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_parent_descendant_scope",
                    client=client,
                    expected_active_flow_revision_id=yielded.json()["flow"][
                        "active_flow_revision_id"
                    ],
                )
                rejected_add = await client.post(
                    "/callback/tasks/task_parent_descendant_scope/tools/add_child",
                    headers={"X-Autoclaw-Session-Key": subtree_session_key},
                    json={
                        "tool_name": "add_child",
                        "payload": {
                            "target_parent_node_key": "nested_parent",
                            "child": {
                                "node_key": "qa_probe",
                                "role": "researcher",
                                "description": "This grandchild add should stay out of scope.",
                            },
                        },
                        "expected_structural_revision_id": yielded.json()["flow"][
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert rejected_add.status_code == 422
                assert "direct child" in rejected_add.json()["detail"]["summary"]
                rejected = await client.post(
                    "/callback/tasks/task_parent_descendant_scope/tools/update_child",
                    headers={"X-Autoclaw-Session-Key": subtree_session_key},
                    json={
                        "tool_name": "update_child",
                        "payload": {
                            "child_node_key": "existing_leaf",
                            "patch": {
                                "description": "This grandchild update should stay out of scope."
                            },
                        },
                        "expected_structural_revision_id": yielded.json()["flow"][
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert rejected.status_code == 422
                assert "direct child" in rejected.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_add_child_rejects_incompatible_role_and_duplicate_slots(tmp_path: Path) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = _child_defaults_workflow()

    try:
        await _persist_bootstrap(
            config_path=config_path,
            task_id="task_replan_invalid",
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=1,
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            root_session_key = await _current_session_key(
                session_factory=session_factory,
                task_id="task_replan_invalid",
            )
            app = create_app()
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                runtime_read = await client.get(
                    "/runtime/tasks/task_replan_invalid",
                    headers=OPERATOR_HEADERS,
                )
                assert runtime_read.status_code == 200
                assign = await client.post(
                    "/callback/tasks/task_replan_invalid/tools/assign_child",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={
                        "tool_name": "assign_child",
                        "payload": {
                            "child_node_key": "subtree",
                            "assignment_intent": {"summary": "go", "instruction": "go"},
                        },
                        "expected_structural_revision_id": runtime_read.json()[
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert assign.status_code == 200
                yielded = await client.post(
                    "/callback/tasks/task_replan_invalid/boundary",
                    headers={"X-Autoclaw-Session-Key": root_session_key},
                    json={"boundary": "yield"},
                )
                assert yielded.status_code == 200

                subtree_session_key = await _current_session_key(
                    session_factory=session_factory,
                    task_id="task_replan_invalid",
                    client=client,
                    expected_active_flow_revision_id=yielded.json()["flow"][
                        "active_flow_revision_id"
                    ],
                )
                incompatible = await client.post(
                    "/callback/tasks/task_replan_invalid/tools/add_child",
                    headers={"X-Autoclaw-Session-Key": subtree_session_key},
                    json={
                        "tool_name": "add_child",
                        "payload": {
                            "child": {
                                "node_key": "bad_parent",
                                "role": "engineer",
                                "description": "Illegal parent role.",
                                "children": [
                                    {
                                        "node_key": "leaf",
                                        "role": "researcher",
                                        "description": "Leaf worker.",
                                    }
                                ],
                            }
                        },
                        "expected_structural_revision_id": yielded.json()["flow"][
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert incompatible.status_code == 422
                assert "incompatible" in incompatible.json()["detail"]["summary"]

                duplicate_slot = await client.post(
                    "/callback/tasks/task_replan_invalid/tools/add_child",
                    headers={"X-Autoclaw-Session-Key": subtree_session_key},
                    json={
                        "tool_name": "add_child",
                        "payload": {
                            "child": {
                                "node_key": "duplicate_slot_child",
                                "role": "researcher",
                                "description": "Duplicate slot child.",
                                "produces": {
                                    "artifacts": [
                                        {
                                            "slot": "brief",
                                            "description": "Conflicting slot.",
                                        }
                                    ]
                                },
                            }
                        },
                        "expected_structural_revision_id": yielded.json()["flow"][
                            "active_flow_revision_id"
                        ],
                    },
                )
                assert duplicate_slot.status_code == 422
                assert "duplicate artifact slot" in duplicate_slot.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()
