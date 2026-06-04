from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.db.session import dispose_db_engine
from httpx import Response
from tests.helpers.runtime_seed import load_workflow_definition
from tests.integration.phase3.runtime_support import (
    ChildDispatchStage,
    Phase3RuntimeApi,
    boundary,
    current_session_key_after_dispatch_progress_for_node,
    drive_minimal_child_to_green,
    parent_tool,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    record_checkpoint,
    stage_child_dispatch,
    write_workspace_file,
)


async def _retry_stage_checkpoint(
    *,
    api: Phase3RuntimeApi,
    task_id: str,
    stage: ChildDispatchStage,
    outcome: str,
    summary: str,
    next_step: str,
    produced_artifacts: list[dict[str, str]] | None = None,
    wait_for_effects: bool = True,
) -> tuple[Response, str]:
    response = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        outcome=outcome,
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts or [],
        wait_for_effects=wait_for_effects,
    )
    if response.status_code != 409:
        return response, stage.worker_session_key
    refreshed_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=stage.active_flow_revision_id,
        expected_node_key=stage.worker_node_key,
    )
    response = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=refreshed_session_key,
        outcome=outcome,
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts or [],
        wait_for_effects=wait_for_effects,
    )
    return response, refreshed_session_key


async def _retry_stage_boundary(
    *,
    api: Phase3RuntimeApi,
    task_id: str,
    stage: ChildDispatchStage,
    session_key: str,
    boundary_name: str,
) -> Response:
    response = await boundary(
        api.client,
        task_id=task_id,
        session_key=session_key,
        boundary_name=boundary_name,
    )
    if response.status_code != 409:
        return response
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


@pytest.mark.asyncio
async def test_yield_after_release_green_maps_to_boundary_precondition_failed(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_yield_after_release_green"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key, active_flow_revision_id = await drive_minimal_child_to_green(
                api,
                task_id=task_id,
                task_root=task_root,
            )
            release = await parent_tool(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                tool_name="release_green",
                payload={},
                active_flow_revision_id=active_flow_revision_id,
            )
            assert release.status_code == 200

            yielded = await boundary(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                boundary_name="yield",
            )
            assert yielded.status_code == 422
            detail = yielded.json()["detail"]
            assert detail["code"] == "boundary_precondition_failed"
            assert (
                detail["summary"] == "yield is illegal after terminal release basis was committed"
            )
            assert (
                "close with the matching terminal boundary instead" in detail["suggested_next_step"]
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_worker_green_missing_required_publication_maps_to_boundary_precondition_failed(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_worker_green_missing_publication"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            stage = await stage_child_dispatch(api, task_id=task_id)
            checkpoint, worker_session_key = await _retry_stage_checkpoint(
                api=api,
                task_id=task_id,
                stage=stage,
                outcome="green",
                summary="Implementation completed but outputs were not published.",
                next_step="Boundary green should still reject until required outputs exist.",
            )
            assert checkpoint.status_code == 200

            worker_green = await _retry_stage_boundary(
                api=api,
                task_id=task_id,
                stage=stage,
                session_key=worker_session_key,
                boundary_name="green",
            )
            assert worker_green.status_code == 422
            detail = worker_green.json()["detail"]
            assert detail["code"] == "boundary_precondition_failed"
            assert detail["summary"].startswith("missing required publication")
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_worker_green_requires_current_artifact_file_not_pending_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-current-artifact"
    task_id = "task_worker_green_missing_current_artifact"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
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
            checkpoint, worker_session_key = await _retry_stage_checkpoint(
                api=api,
                task_id=task_id,
                stage=stage,
                outcome="green",
                summary="Implementation completed with synchronous artifact publication.",
                next_step=(
                    "Boundary green may proceed because current artifact files are "
                    "already readable."
                ),
                produced_artifacts=[
                    {"slot": "change_patch", "path": str(patch_file)},
                    {"slot": "verification_report", "path": str(verification_file)},
                ],
                wait_for_effects=False,
            )
            assert checkpoint.status_code == 200

            worker_green = await _retry_stage_boundary(
                api=api,
                task_id=task_id,
                stage=stage,
                session_key=worker_session_key,
                boundary_name="green",
            )
            assert worker_green.status_code == 200
    finally:
        await dispose_db_engine()
