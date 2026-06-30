from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.persistence.session import dispose_db_engine
from tests.helpers.runtime_support import (
    drive_minimal_child_to_green,
    parent_tool,
    persist_bootstrap,
    prepare_runtime_db,
    runtime_api_context,
)
from tests.helpers.seeded_runtime_support import load_workflow_definition

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


@pytest.mark.asyncio
async def test_assign_child_rejects_same_child_supplemental_artifact_feedback_loop(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-feedback-loop"
    task_id = "task_release_feedback_loop_child"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=1,
        )
        async with runtime_api_context(config_path) as api:
            root_session_key, active_flow_revision_id = await drive_minimal_child_to_green(
                api,
                task_id=task_id,
                task_root=task_root,
            )
            second_assign = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                tool_name="assign_child",
                payload={
                    "child_node_key": "implement_change",
                    "assignment_intent": {
                        "summary": "patch the same child again",
                        "instruction": "reuse prior notes as transient context only.",
                    },
                    "supplemental_durable_context": {
                        "artifact_slots": [
                            {"slot": "change_patch"},
                            {"slot": "verification_report"},
                        ]
                    },
                },
                active_flow_revision_id=active_flow_revision_id,
            )
            assert second_assign.status_code == 400
            detail = second_assign.json()["detail"]
            assert detail["code"] == "invalid_request_shape"
            assert "same-node context" in detail["summary"]
            assert "transient_surfaces or task memory" in detail["summary"]
    finally:
        await dispose_db_engine()


__all__ = ["test_assign_child_rejects_same_child_supplemental_artifact_feedback_loop"]
