from __future__ import annotations

from pathlib import Path

import autoclaw.interfaces.cli as cli
import autoclaw.persistence.session as db_session
import pytest
from autoclaw.config import get_settings
from autoclaw.persistence import AssignmentModel, FlowModel, FlowNodeModel
from autoclaw.persistence.session import dispose_db_engine, get_session_factory
from autoclaw.runtime.post_commit import stop_runtime_effect_runner
from sqlalchemy import select
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase3.contracts.workflows import (
    child_defaults_workflow,
    optional_artifact_selector_workflow,
)
from tests.integration.phase3.runtime_support import (
    assign_child,
    current_session_key,
    parent_tool,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    runtime_read_json,
    stage_child_dispatch,
)


@pytest.mark.asyncio
async def test_add_child_persists_subtree_and_inherits_child_default_consumes(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_replan_subtree"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=child_defaults_workflow(),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            stage = await stage_child_dispatch(api, task_id=task_id, child_node_key="subtree")
            add_child = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                tool_name="add_child",
                payload={
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
                active_flow_revision_id=stage.active_flow_revision_id,
            )
            assert add_child.status_code == 200
            manifest_markdown = (task_root / "_runtime" / "workflow-manifest.md").read_text(
                encoding="utf-8"
            )
            assert "qa_sweep" in manifest_markdown
            assert "collect_cases" in manifest_markdown

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
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
async def test_launch_makes_root_manifest_and_assignment_readable_before_effect_drain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-launch-readability"
    task_id = "task_launch_readability"

    try:
        await stop_runtime_effect_runner()
        monkeypatch.setattr(db_session, "notify_runtime_effect_runner", lambda: None)
        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-3-launch-readability",
                )

        assert (task_root / "_runtime" / "workflow-manifest.md").is_file()
        assert (task_root / "_runtime" / "workflow-manifest.json").is_file()
        assert (
            task_root / "_runtime" / "attempts" / f"attempt.{task_id}.root.01" / "assignment.md"
        ).is_file()
        assert (
            task_root / "_runtime" / "attempts" / f"attempt.{task_id}.root.01" / "assignment.json"
        ).is_file()
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_assign_child_missing_required_artifact_is_semantic_invalid(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_missing_artifact_assign"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=child_defaults_workflow(),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            stage = await stage_child_dispatch(api, task_id=task_id, child_node_key="subtree")
            missing_artifact = await assign_child(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                child_node_key="existing_child",
                active_flow_revision_id=stage.active_flow_revision_id,
            )
            assert missing_artifact.status_code == 422
            assert missing_artifact.json()["detail"]["code"] == "missing_required_publication"
            assert "missing required publication" in missing_artifact.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_assign_child_optional_artifact_allows_missing_current_publication(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-optional-artifact"
    task_id = "task_optional_artifact_assign"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=optional_artifact_selector_workflow(),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            assign = await assign_child(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                child_node_key="optional_child",
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert assign.status_code == 200
            assignment_key = assign.json()["target_assignment_key"]

            async with api.session_factory() as session:
                assignment = await session.scalar(
                    select(AssignmentModel).where(AssignmentModel.assignment_key == assignment_key)
                )
                assert assignment is not None
                assert assignment.consumes_json == []
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_assign_child_optional_artifact_still_requires_provider_target(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-optional-artifact-target"
    task_id = "task_optional_artifact_target"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=optional_artifact_selector_workflow(),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                child_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                        FlowNodeModel.node_key == "optional_child",
                    )
                )
                assert child_node is not None
                child_node.consumes_json = {
                    "artifacts": [{"slot": "missing_brief", "required": False}],
                    "criteria": None,
                }
                await session.commit()

            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            assign = await assign_child(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                child_node_key="optional_child",
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert assign.status_code == 422
            detail = assign.json()["detail"]
            assert detail["code"] == "missing_resource"
            assert detail["summary"] == "missing artifact provider for slot 'missing_brief'"
    finally:
        await dispose_db_engine()


__all__ = [
    "test_add_child_persists_subtree_and_inherits_child_default_consumes",
    "test_assign_child_missing_required_artifact_is_semantic_invalid",
    "test_assign_child_optional_artifact_allows_missing_current_publication",
    "test_assign_child_optional_artifact_still_requires_provider_target",
    "test_launch_makes_root_manifest_and_assignment_readable_before_effect_drain",
]
