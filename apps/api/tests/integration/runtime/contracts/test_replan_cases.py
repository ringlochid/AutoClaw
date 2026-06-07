from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from autoclaw.persistence import FlowModel, FlowNodeModel
from autoclaw.persistence.session import dispose_db_engine
from sqlalchemy import select
from tests.helpers.runtime_support import (
    current_session_key,
    parent_tool,
    persist_bootstrap,
    prepare_runtime_db,
    runtime_api_context,
    runtime_read_json,
    stage_child_dispatch,
)
from tests.integration.runtime.contracts.workflows import (
    child_defaults_workflow,
    criteria_defaults_refresh_workflow,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


def _manifest_payload(task_root: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((task_root / "_runtime" / "workflow-manifest.json").read_text(encoding="utf-8")),
    )


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

        async with runtime_api_context(config_path) as api:
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
            assert (
                "unknown local criteria slot 'missing_gate'"
                in add_child.json()["detail"]["summary"]
            )
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

        async with runtime_api_context(config_path) as api:
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
            manifest = _manifest_payload(task_root)
            node_tree = {
                node["node_key"]: node for node in cast(list[dict[str, Any]], manifest["node_tree"])
            }
            collect_cases = node_tree["collect_cases"]
            assert collect_cases["criteria"][0]["slot"] == "review_gate"
            assert collect_cases["criteria"][0]["description"] == "Updated review gate."
            assert str(collect_cases["criteria"][0]["path"]).endswith("review_gate.v02.md")

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

        async with runtime_api_context(config_path) as api:
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
    "test_update_child_refreshes_inherited_criteria_for_descendants",
]
