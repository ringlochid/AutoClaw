from __future__ import annotations

from pathlib import Path

import pytest
from app.db import FlowModel, FlowNodeModel
from app.db.session import dispose_db_engine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase3.contracts.workflows import (
    child_defaults_workflow,
    criteria_defaults_refresh_workflow,
    root_descendant_replan_workflow,
)
from tests.integration.phase3.runtime_support import (
    current_session_key,
    parent_tool,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    runtime_read_json,
    stage_child_dispatch,
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

@pytest.mark.asyncio
async def test_add_child_rejects_unknown_child_default_criteria_slot(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_invalid_child_defaults"

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
                active_flow_revision_id=stage.active_flow_revision_id,
            )
            assert add_child.status_code == 422
            assert add_child.json()["detail"]["code"] == "illegal_state"
            assert "unknown local criteria slot 'missing_gate'" in add_child.json()["detail"][
                "summary"
            ]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_update_child_refreshes_inherited_criteria_for_descendants(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_refresh_defaults"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=criteria_defaults_refresh_workflow(),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            update_child = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                tool_name="update_child",
                payload={
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
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert update_child.status_code == 200

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
            await assert_root_descendant_removal(
                session_factory=api.session_factory,
                task_id=task_id,
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
            assert "direct child" in rejected_add.json()["detail"]["summary"]
            rejected = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                tool_name="update_child",
                payload={
                    "child_node_key": "existing_leaf",
                    "patch": {
                        "description": "This grandchild update should stay out of scope."
                    },
                },
                active_flow_revision_id=stage.active_flow_revision_id,
            )
            assert rejected.status_code == 422
            assert "direct child" in rejected.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_add_child_rejects_incompatible_role_and_duplicate_slots(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_replan_invalid"

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
            incompatible = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                tool_name="add_child",
                payload={
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
                active_flow_revision_id=stage.active_flow_revision_id,
            )
            assert incompatible.status_code == 422
            assert "incompatible" in incompatible.json()["detail"]["summary"]
            duplicate_slot = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                tool_name="add_child",
                payload={
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
                active_flow_revision_id=stage.active_flow_revision_id,
            )
            assert duplicate_slot.status_code == 422
            assert "duplicate artifact slot" in duplicate_slot.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()


__all__ = [
    "test_add_child_rejects_incompatible_role_and_duplicate_slots",
    "test_add_child_rejects_unknown_child_default_criteria_slot",
    "test_non_root_parent_cannot_update_non_direct_descendant",
    "test_root_can_update_and_remove_explicit_descendant_nodes",
    "test_update_child_refreshes_inherited_criteria_for_descendants",
]
