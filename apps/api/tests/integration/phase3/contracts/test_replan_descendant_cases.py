from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from autoclaw.db import FlowModel, FlowNodeModel
from autoclaw.db.session import dispose_db_engine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase3.contracts.workflows import root_descendant_replan_workflow
from tests.integration.phase3.runtime_support import (
    current_session_key,
    parent_tool,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    runtime_read_json,
    stage_child_dispatch,
)


def _manifest_payload(task_root: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")),
    )


async def assert_root_descendant_update(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
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


async def assert_root_descendant_removal(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> None:
    async with session_factory() as session:
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
        assert "nested_parent" not in node_by_key
        assert "existing_leaf" not in node_by_key
        assert node_by_key["subtree"].child_node_keys_json == []


async def _run_root_descendant_replan(
    *,
    task_root: Path,
    task_id: str,
    api: Any,
) -> None:
    root_session_key = await current_session_key(
        session_factory=api.session_factory,
        task_id=task_id,
    )
    runtime_read = await runtime_read_json(api.client, task_id)
    add_child = await parent_tool(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        tool_name="add_child",
        payload={
            "target_parent_node_key": "nested_parent",
            "child": {
                "node_key": "qa_probe",
                "role": "researcher",
                "description": "Added under the nested parent by root.",
            },
        },
        active_flow_revision_id=runtime_read["active_flow_revision_id"],
    )
    assert add_child.status_code == 200
    update_child = await parent_tool(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        tool_name="update_child",
        payload={
            "child_node_key": "existing_leaf",
            "patch": {"description": "Updated by the root whole-tree replan."},
        },
        active_flow_revision_id=add_child.json()["flow"]["active_flow_revision_id"],
    )
    assert update_child.status_code == 200
    updated_manifest = _manifest_payload(task_root)
    updated_nodes = {
        node["node_key"]: node for node in cast(list[dict[str, Any]], updated_manifest["node_tree"])
    }
    assert updated_nodes["existing_leaf"]["description"] == "Updated by the root whole-tree replan."
    assert updated_nodes["qa_probe"]["parent_node_key"] == "nested_parent"
    await assert_root_descendant_update(
        session_factory=api.session_factory,
        task_id=task_id,
    )

    remove_child = await parent_tool(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        tool_name="remove_child",
        payload={"child_node_key": "nested_parent"},
        active_flow_revision_id=update_child.json()["flow"]["active_flow_revision_id"],
    )
    assert remove_child.status_code == 200
    removed_manifest = _manifest_payload(task_root)
    removed_node_keys = {
        node["node_key"] for node in cast(list[dict[str, Any]], removed_manifest["node_tree"])
    }
    assert "nested_parent" not in removed_node_keys
    assert "existing_leaf" not in removed_node_keys
    assert "qa_probe" not in removed_node_keys
    await assert_root_descendant_removal(
        session_factory=api.session_factory,
        task_id=task_id,
    )


@pytest.mark.asyncio
async def test_root_can_update_and_remove_explicit_descendant_nodes(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_root_descendant_replan"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=root_descendant_replan_workflow(),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            await _run_root_descendant_replan(
                task_root=task_root,
                task_id=task_id,
                api=api,
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_non_root_parent_cannot_update_non_direct_descendant(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_parent_descendant_scope"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=root_descendant_replan_workflow(),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            stage = await stage_child_dispatch(api, task_id=task_id, child_node_key="subtree")
            rejected_add = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                tool_name="add_child",
                payload={
                    "target_parent_node_key": "nested_parent",
                    "child": {
                        "node_key": "qa_probe",
                        "role": "researcher",
                        "description": "This grandchild add should stay out of scope.",
                    },
                },
                active_flow_revision_id=stage.active_flow_revision_id,
            )
            assert rejected_add.status_code == 422
            assert rejected_add.json()["detail"]["code"] == "illegal_target_relation"
            assert "direct child" in rejected_add.json()["detail"]["summary"]
            rejected = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                tool_name="update_child",
                payload={
                    "child_node_key": "existing_leaf",
                    "patch": {"description": "This grandchild update should stay out of scope."},
                },
                active_flow_revision_id=stage.active_flow_revision_id,
            )
            assert rejected.status_code == 422
            assert rejected.json()["detail"]["code"] == "illegal_target_relation"
            assert "direct child" in rejected.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()


__all__ = [
    "test_non_root_parent_cannot_update_non_direct_descendant",
    "test_root_can_update_and_remove_explicit_descendant_nodes",
]
