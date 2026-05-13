from __future__ import annotations

import json
from pathlib import Path

import app.api.routes.callback as callback_route
import pytest
from app.db.session import dispose_db_engine
from app.runtime.projection import materialize_manifest
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers.runtime_seed import load_workflow_definition
from tests.integration.phase3.contracts.workflows import dependency_dedupe_workflow
from tests.integration.phase3.runtime_support import (
    current_session_key,
    parent_tool,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    runtime_read_json,
)


@pytest.mark.asyncio
async def test_manifest_rematerialization_keeps_workflow_description(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    workflow_definition = load_workflow_definition("normal_parent_first_release")
    task_id = "task_manifest_description"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=workflow_definition,
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            async with api.session_factory() as session:
                manifest = await materialize_manifest(session, task_id)
                manifest_json = json.loads(
                    (task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")
                )
                assert manifest.workflow.description == workflow_definition.description
                assert manifest_json["workflow"]["description"] == workflow_definition.description
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_manifest_rematerialization_dedupes_node_dependency_lists(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_manifest_dependency_dedupe"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=dependency_dedupe_workflow(),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            async with api.session_factory() as session:
                manifest = await materialize_manifest(session, task_id)
                node_by_key = {node.node_key: node for node in manifest.node_tree}
                assert node_by_key["implement_change"].depends_on_node_keys == ("root",)
                assert node_by_key["root"].depended_on_by_node_keys == ("implement_change",)
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_structural_tool_failure_does_not_commit_graph_change_after_manifest_prewrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_structural_commit_failure"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            original_revision = runtime_read["active_flow_revision_id"]

            async def fail_commit(session: AsyncSession) -> None:
                del session
                raise RuntimeError("forced structural commit failure")

            monkeypatch.setattr(callback_route, "commit_runtime_session", fail_commit)
            add_child = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                tool_name="add_child",
                payload={
                    "child": {
                        "node_key": "qa_probe",
                        "role": "architect",
                        "description": "Probe child that must not commit on failure.",
                    }
                },
                active_flow_revision_id=original_revision,
            )
            assert add_child.status_code == 500
            detail = add_child.json()["detail"]
            assert detail["code"] == "internal_error"
            refreshed_runtime = await runtime_read_json(api.client, task_id)
            assert refreshed_runtime["active_flow_revision_id"] == original_revision
            restored_manifest = (task_root / "_runtime" / "workflow-manifest.md").read_text(
                encoding="utf-8"
            )
            assert "qa_probe" not in restored_manifest
            restored_manifest_json = json.loads(
                (task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")
            )
            assert restored_manifest_json["active_flow_revision_id"] == original_revision
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_structural_manifest_prewrite_failure_rolls_back_graph_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_structural_prewrite_failure"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            original_revision = runtime_read["active_flow_revision_id"]
            original_manifest = (task_root / "_runtime" / "workflow-manifest.md").read_text(
                encoding="utf-8"
            )

            async def fail_prewrite(session: AsyncSession, task_id: str) -> None:
                del session, task_id
                raise RuntimeError("forced manifest prewrite failure")

            monkeypatch.setattr(callback_route, "materialize_manifest", fail_prewrite)
            add_child = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                tool_name="add_child",
                payload={
                    "child": {
                        "node_key": "qa_probe",
                        "role": "architect",
                        "description": "Probe child that must not commit on prewrite failure.",
                    }
                },
                active_flow_revision_id=original_revision,
            )
            assert add_child.status_code == 500
            assert add_child.json()["detail"]["code"] == "internal_error"

            refreshed_runtime = await runtime_read_json(api.client, task_id)
            assert refreshed_runtime["active_flow_revision_id"] == original_revision
            restored_manifest = (task_root / "_runtime" / "workflow-manifest.md").read_text(
                encoding="utf-8"
            )
            assert restored_manifest == original_manifest
    finally:
        await dispose_db_engine()


__all__ = [
    "test_manifest_rematerialization_dedupes_node_dependency_lists",
    "test_manifest_rematerialization_keeps_workflow_description",
    "test_structural_manifest_prewrite_failure_rolls_back_graph_change",
    "test_structural_tool_failure_does_not_commit_graph_change_after_manifest_prewrite",
]
