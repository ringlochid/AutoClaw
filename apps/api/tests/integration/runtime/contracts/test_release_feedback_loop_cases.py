from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from autoclaw.persistence.session import dispose_db_engine
from httpx import Response
from tests.helpers.runtime_support import (
    boundary,
    current_session_key_after_dispatch_progress_for_node,
    drive_minimal_child_to_green,
    parent_tool,
    persist_bootstrap,
    prepare_runtime_db,
    record_checkpoint,
    runtime_api_context,
    runtime_read_json,
    write_workspace_file,
)
from tests.helpers.seeded_runtime_support import load_workflow_definition

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


@pytest.mark.asyncio
async def test_release_green_allows_reassigned_child_with_stale_feedback_consumes(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-feedback-loop"
    task_id = "task_release_feedback_loop_child"

    try:
        await _bootstrap_feedback_loop_task(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
        )
        async with runtime_api_context(config_path) as api:
            root_session_key, active_flow_revision_id = await drive_minimal_child_to_green(
                api,
                task_id=task_id,
                task_root=task_root,
            )
            rerun_worker_session_key = await _stage_same_child_feedback_loop(
                api=api,
                task_id=task_id,
                root_session_key=root_session_key,
                active_flow_revision_id=active_flow_revision_id,
            )
            refreshed_root_session_key = await _complete_second_feedback_iteration(
                api=api,
                task_id=task_id,
                task_root=task_root,
                active_flow_revision_id=active_flow_revision_id,
                rerun_worker_session_key=rerun_worker_session_key,
            )
            release = await _release_feedback_loop_root(
                api=api,
                task_id=task_id,
                root_session_key=refreshed_root_session_key,
                active_flow_revision_id=active_flow_revision_id,
            )
            assert release.status_code == 200
    finally:
        await dispose_db_engine()


async def _bootstrap_feedback_loop_task(
    *,
    config_path: Path,
    task_id: str,
    task_root: Path,
) -> None:
    await persist_bootstrap(
        config_path=config_path,
        task_id=task_id,
        task_root=task_root,
        workflow_definition=load_workflow_definition("minimal_implement_change"),
        revision_no=1,
    )


async def _stage_same_child_feedback_loop(
    *,
    api: Any,
    task_id: str,
    root_session_key: str,
    active_flow_revision_id: str,
) -> str:
    second_assign = await parent_tool(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        tool_name="assign_child",
        payload={
            "child_node_key": "implement_change",
            "assignment_intent": {
                "summary": "patch the same child again",
                "instruction": "reuse prior artifacts as patch context and republish them.",
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
    assert second_assign.status_code == 200
    yielded = await boundary(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        boundary_name="yield",
    )
    assert yielded.status_code == 200
    assert yielded.json()["flow"]["current_node_key"] == "implement_change"
    return await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=active_flow_revision_id,
        expected_node_key="implement_change",
    )


async def _complete_second_feedback_iteration(
    *,
    api: Any,
    task_id: str,
    task_root: Path,
    active_flow_revision_id: str,
    rerun_worker_session_key: str,
) -> str:
    patch_v2 = write_workspace_file(
        task_root,
        "workspace/change_patch_v2.diff",
        "diff --git a b\n+second pass\n",
    )
    verification_v2 = write_workspace_file(
        task_root,
        "workspace/verification_report_v2.md",
        "verification passed again",
    )
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=rerun_worker_session_key,
        outcome="green",
        summary="second child run completed",
        next_step="root should release from the second child outputs.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(patch_v2)},
            {"slot": "verification_report", "path": str(verification_v2)},
        ],
    )
    assert checkpoint.status_code == 200
    worker_green = await boundary(
        api.client,
        task_id=task_id,
        session_key=rerun_worker_session_key,
        boundary_name="green",
    )
    assert worker_green.status_code == 200
    assert worker_green.json()["flow"]["current_node_key"] == "root"
    return await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=active_flow_revision_id,
        expected_node_key="root",
    )


async def _release_feedback_loop_root(
    *,
    api: Any,
    task_id: str,
    root_session_key: str,
    active_flow_revision_id: str,
) -> Response:
    runtime_read = await runtime_read_json(api.client, task_id)
    return await parent_tool(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        tool_name="release_green",
        payload={},
        active_flow_revision_id=cast(str, runtime_read["active_flow_revision_id"]),
    )
