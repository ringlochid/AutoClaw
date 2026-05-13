from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import app.db.session as db_session
import pytest
from app.db import ArtifactCurrentPointerModel
from app.db.session import dispose_db_engine
from app.runtime.effects import stop_runtime_effect_runner
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase3.contracts.pending_materialization_support import (
    artifact_handoff_workflow,
    stage_pending_file_copy_effect,
)
from tests.integration.phase3.runtime_support import (
    Phase3RuntimeApi,
    assign_child,
    boundary,
    current_session_key,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    record_checkpoint,
    runtime_read_json,
    stage_child_dispatch,
    write_workspace_file,
)


@pytest.mark.asyncio
async def test_assign_child_allows_pending_current_artifact_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-pending-assign"
    task_id = "task_pending_assign_child"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=artifact_handoff_workflow(),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            worker_flow_revision_id = await complete_implementation_child(
                api=api,
                task_id=task_id,
                task_root=task_root,
            )
            await stop_runtime_effect_runner()
            monkeypatch.setattr(db_session, "notify_runtime_effect_runner", lambda: None)
            await stage_pending_review_artifact_copy(
                session_factory=api.session_factory,
                task_id=task_id,
            )

            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
                client=api.client,
                expected_active_flow_revision_id=worker_flow_revision_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            review_assign = await assign_child(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                child_node_key="review_change",
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
                summary="Review the current implementation evidence.",
                instruction="Publish only the bounded review report.",
            )
            assert review_assign.status_code == 200
    finally:
        await dispose_db_engine()


async def complete_implementation_child(
    *,
    api: Phase3RuntimeApi,
    task_id: str,
    task_root: Path,
) -> str:
    stage = await stage_child_dispatch(
        api,
        task_id=task_id,
        child_node_key="implement_change",
    )
    patch_file = write_workspace_file(
        task_root,
        "workspace/change_patch.diff",
        "diff --git a b",
    )
    verification_file = write_workspace_file(
        task_root,
        "workspace/verification_report.md",
        "verification ok",
    )
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        outcome="green",
        summary="Implementation completed.",
        next_step="Root should review the current implementation evidence.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(patch_file)},
            {"slot": "verification_report", "path": str(verification_file)},
        ],
    )
    assert checkpoint.status_code == 200
    worker_green = await boundary(
        api.client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        boundary_name="green",
    )
    assert worker_green.status_code == 200
    return cast(str, worker_green.json()["flow"]["active_flow_revision_id"])


async def stage_pending_review_artifact_copy(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> None:
    async with session_factory() as session:
        pointer = await session.scalar(
            select(ArtifactCurrentPointerModel).where(
                ArtifactCurrentPointerModel.task_id == task_id,
                ArtifactCurrentPointerModel.owner_node_key == "implement_change",
                ArtifactCurrentPointerModel.slot == "change_patch",
            )
        )
        assert pointer is not None
        artifact_path = Path(pointer.current_path)
        if await asyncio.to_thread(artifact_path.is_file):
            await asyncio.to_thread(artifact_path.unlink)
        await stage_pending_file_copy_effect(pointer=pointer, session=session)
        await session.commit()
        assert not await asyncio.to_thread(artifact_path.is_file)


__all__ = ["test_assign_child_allows_pending_current_artifact_materialization"]
