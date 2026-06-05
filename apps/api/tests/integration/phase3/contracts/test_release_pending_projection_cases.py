from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest
from autoclaw.persistence import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    FlowModel,
    FlowNodeModel,
)
from autoclaw.persistence.session import dispose_db_engine
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_seed import load_workflow_definition
from tests.integration.phase3.runtime_support import (
    Phase3RuntimeApi,
    boundary,
    current_session_key_after_dispatch_progress,
    parent_tool,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    record_checkpoint,
    runtime_read_json,
    stage_child_dispatch,
    write_workspace_file,
)


@pytest.mark.asyncio
async def test_release_green_rejects_missing_child_projections_when_current_files_are_missing(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-pending-release"
    task_id = "task_release_pending_child_projections"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            worker_flow_revision_id = await complete_child_for_root_release(
                task_id=task_id,
                task_root=task_root,
                client=api.client,
                api=api,
            )
            root_session_key = await current_session_key_after_dispatch_progress(
                session_factory=api.session_factory,
                task_id=task_id,
                client=api.client,
                expected_active_flow_revision_id=worker_flow_revision_id,
            )
            await remove_current_child_projection_files(
                session_factory=api.session_factory,
                task_id=task_id,
                task_root=task_root,
            )

            runtime_read = await runtime_read_json(api.client, task_id)
            release = await release_green(
                client=api.client,
                task_id=task_id,
                session_key=root_session_key,
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert release.status_code == 409
            detail = release.json()["detail"]
            assert detail["code"] == "stale_checkpoint"
            assert (
                detail["summary"] == "release_green requires current checkpoint evidence: "
                "current checkpoint projection files are missing"
            )
    finally:
        await dispose_db_engine()


async def release_green(
    *,
    task_id: str,
    session_key: str,
    active_flow_revision_id: str,
    client: AsyncClient,
) -> Response:
    return await parent_tool(
        client,
        task_id=task_id,
        session_key=session_key,
        tool_name="release_green",
        payload={},
        active_flow_revision_id=active_flow_revision_id,
    )


async def complete_child_for_root_release(
    *,
    api: Phase3RuntimeApi,
    task_id: str,
    task_root: Path,
    client: AsyncClient,
) -> str:
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
    checkpoint = await record_checkpoint(
        client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        outcome="green",
        summary="Implementation completed.",
        next_step="Root should verify the bounded change and close the flow.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(patch_file)},
            {"slot": "verification_report", "path": str(verification_file)},
        ],
    )
    assert checkpoint.status_code == 200
    worker_green = await boundary(
        client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        boundary_name="green",
    )
    assert worker_green.status_code == 200
    return cast(str, worker_green.json()["flow"]["active_flow_revision_id"])


async def remove_current_child_projection_files(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    task_root: Path,
) -> str:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        child_node = await session.scalar(
            select(FlowNodeModel).where(
                FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                FlowNodeModel.node_key == "implement_change",
            )
        )
        assert child_node is not None
        assert child_node.current_assignment_id is not None
        child_assignment = await session.get(AssignmentModel, child_node.current_assignment_id)
        assert child_assignment is not None
        assert child_assignment.current_attempt_id is not None
        child_attempt_id = child_assignment.current_attempt_id
        checkpoint_dir = task_root / "_runtime" / "attempts" / child_attempt_id
        current_pointer = await session.scalar(
            select(ArtifactCurrentPointerModel).where(
                ArtifactCurrentPointerModel.task_id == task_id,
                ArtifactCurrentPointerModel.owner_node_key == "implement_change",
                ArtifactCurrentPointerModel.slot == "change_patch",
            )
        )
        assert current_pointer is not None
        checkpoint_json = checkpoint_dir / "latest-checkpoint.json"
        checkpoint_markdown = checkpoint_dir / "latest-checkpoint.md"
        if await asyncio.to_thread(checkpoint_json.is_file):
            await asyncio.to_thread(checkpoint_json.unlink)
        if await asyncio.to_thread(checkpoint_markdown.is_file):
            await asyncio.to_thread(checkpoint_markdown.unlink)
        artifact_path = Path(current_pointer.current_path)
        if await asyncio.to_thread(artifact_path.is_file):
            await asyncio.to_thread(artifact_path.unlink)
        assert not await asyncio.to_thread(checkpoint_json.is_file)
        assert not await asyncio.to_thread(checkpoint_markdown.is_file)
        assert not await asyncio.to_thread(artifact_path.is_file)
    return child_attempt_id


__all__ = [
    "test_release_green_rejects_missing_child_projections_when_current_files_are_missing",
]
