from __future__ import annotations

from pathlib import Path
from typing import cast

from httpx import Response

from tests.helpers.runtime_support.dispatch_session_support import (
    current_session_key,
    current_session_key_after_dispatch_progress_for_node,
)
from tests.helpers.runtime_support.http_api_support import (
    ChildDispatchStage,
    RuntimeApiContext,
    assign_child,
    boundary,
    record_checkpoint,
    runtime_read_json,
)


async def stage_child_dispatch(
    api: RuntimeApiContext,
    *,
    task_id: str,
    child_node_key: str = "implement_change",
) -> ChildDispatchStage:
    runtime_read = await runtime_read_json(api.client, task_id)
    root_session_key = await current_session_key(
        session_factory=api.session_factory,
        task_id=task_id,
    )
    assign = await assign_child(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        child_node_key=child_node_key,
        active_flow_revision_id=cast(str, runtime_read["active_flow_revision_id"]),
    )
    assert assign.status_code == 200
    yielded = await boundary(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        boundary_name="yield",
    )
    assert yielded.status_code == 200
    assert yielded.json()["flow"]["current_node_key"] == child_node_key
    active_flow_revision_id = cast(str, yielded.json()["flow"]["active_flow_revision_id"])
    worker_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=active_flow_revision_id,
        expected_node_key=child_node_key,
    )
    return ChildDispatchStage(
        root_session_key,
        worker_session_key,
        active_flow_revision_id,
        child_node_key,
    )


async def retry_terminal_green_checkpoint(
    api: RuntimeApiContext,
    *,
    stage: ChildDispatchStage,
    task_id: str,
    summary: str,
    next_step: str,
    produced_artifacts: list[dict[str, str]] | None = None,
) -> tuple[Response, str]:
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        outcome="green",
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts or [],
    )
    if checkpoint.status_code != 409:
        return checkpoint, stage.worker_session_key
    refreshed_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=stage.active_flow_revision_id,
        expected_node_key=stage.worker_node_key,
    )
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=refreshed_session_key,
        outcome="green",
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts or [],
    )
    return checkpoint, refreshed_session_key


def write_workspace_file(task_root: Path, relative_path: str, body: str) -> Path:
    output_path = task_root / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return output_path


async def drive_bounded_child_to_green(
    api: RuntimeApiContext,
    *,
    task_id: str,
    task_root: Path,
) -> tuple[str, str]:
    stage = await stage_child_dispatch(api, task_id=task_id)
    patch_file = write_workspace_file(
        task_root,
        "workspace/change_patch.diff",
        "diff --git a b",
    )
    verification_file = write_workspace_file(
        task_root,
        "workspace/verification_report.md",
        "verification passed",
    )
    checkpoint, worker_session_key = await _retry_child_checkpoint(
        api=api,
        stage=stage,
        task_id=task_id,
        outcome="green",
        summary="done",
        next_step="root should verify the bounded change and close the flow.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(patch_file)},
            {"slot": "verification_report", "path": str(verification_file)},
        ],
    )
    assert checkpoint.status_code == 200
    worker_green = await _retry_child_boundary(
        api=api,
        stage=stage,
        task_id=task_id,
        session_key=worker_session_key,
        boundary_name="green",
    )
    assert worker_green.status_code == 200
    assert worker_green.json()["flow"]["current_node_key"] == "root"
    root_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=stage.active_flow_revision_id,
        expected_node_key="root",
    )
    resumed_root = await runtime_read_json(api.client, task_id)
    return root_session_key, cast(str, resumed_root["active_flow_revision_id"])


async def _retry_child_checkpoint(
    *,
    api: RuntimeApiContext,
    stage: ChildDispatchStage,
    task_id: str,
    outcome: str,
    summary: str,
    next_step: str,
    produced_artifacts: list[dict[str, str]],
) -> tuple[Response, str]:
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        outcome=outcome,
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts,
    )
    if checkpoint.status_code != 409:
        return checkpoint, stage.worker_session_key
    refreshed_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=stage.active_flow_revision_id,
        expected_node_key=stage.worker_node_key,
    )
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=refreshed_session_key,
        outcome=outcome,
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts,
    )
    return checkpoint, refreshed_session_key


async def _retry_child_boundary(
    *,
    api: RuntimeApiContext,
    stage: ChildDispatchStage,
    task_id: str,
    session_key: str,
    boundary_name: str,
) -> Response:
    boundary_response = await boundary(
        api.client,
        task_id=task_id,
        session_key=session_key,
        boundary_name=boundary_name,
    )
    if boundary_response.status_code != 409:
        return boundary_response
    refreshed_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=stage.active_flow_revision_id,
        expected_node_key=stage.worker_node_key,
    )
    return await boundary(
        api.client,
        task_id=task_id,
        session_key=refreshed_session_key,
        boundary_name=boundary_name,
    )


__all__ = [
    "drive_bounded_child_to_green",
    "retry_terminal_green_checkpoint",
    "stage_child_dispatch",
    "write_workspace_file",
]
