from __future__ import annotations

from pathlib import Path

import pytest
from app.db import ArtifactCurrentPointerModel, AssignmentModel, FlowModel, FlowNodeModel
from app.db.session import dispose_db_engine
from app.runtime.effects import drive_runtime_once
from httpx import AsyncClient, Response
from sqlalchemy import select
from tests.helpers.runtime_seed import load_workflow_definition
from tests.integration.phase3.runtime_support import (
    ChildDispatchStage,
    Phase3RuntimeApi,
    boundary,
    current_session_key_after_dispatch_progress,
    current_session_key_after_dispatch_progress_for_node,
    drive_minimal_child_to_green,
    parent_tool,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    record_checkpoint,
    stage_child_dispatch,
)


async def _retry_record_checkpoint_with_live_session(
    *,
    api: Phase3RuntimeApi,
    stage: ChildDispatchStage,
    task_id: str,
    session_key: str,
    outcome: str,
    summary: str,
    next_step: str,
) -> tuple[Response, str]:
    response = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=session_key,
        outcome=outcome,
        summary=summary,
        next_step=next_step,
    )
    if response.status_code != 409:
        return response, session_key
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
    )
    return response, refreshed_session_key


async def _retry_boundary_with_live_session(
    *,
    api: Phase3RuntimeApi,
    stage: ChildDispatchStage,
    task_id: str,
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


@pytest.mark.asyncio
async def test_release_green_uses_relational_children_and_maps_stale_checkpoint_to_409(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_release_relational_child"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key, active_flow_revision_id = await drive_minimal_child_to_green(
                api,
                task_id=task_id,
                task_root=task_root,
            )
            await drive_runtime_once(task_id=task_id)

            async with api.session_factory() as session:
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
                child_assignment = await session.get(
                    AssignmentModel,
                    child_node.current_assignment_id,
                )
                assert child_assignment is not None
                assert child_assignment.current_attempt_id is not None
                child_node.parent_node_key = child_node.node_key
                checkpoint_dir = (
                    task_root / "_runtime" / "attempts" / child_assignment.current_attempt_id
                )
                (checkpoint_dir / "latest-checkpoint.json").unlink()
                (checkpoint_dir / "latest-checkpoint.md").unlink()
                await session.commit()

            release = await release_green(
                client=api.client,
                task_id=task_id,
                session_key=root_session_key,
                active_flow_revision_id=active_flow_revision_id,
            )
            assert release.status_code == 409
            detail = release.json()["detail"]
            assert detail["code"] == "stale_checkpoint"
            assert "requires current checkpoint evidence" in detail["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_retry_budget_exhaustion_surfaces_live_callback_failure(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root-retry-budget"
    task_id = "task_retry_budget_exhaustion"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            stage = await stage_child_dispatch(api, task_id=task_id)
            first_checkpoint, worker_session_key = await _retry_record_checkpoint_with_live_session(
                api=api,
                stage=stage,
                task_id=task_id,
                session_key=stage.worker_session_key,
                outcome="retry",
                summary="first retry request",
                next_step="redispatch the same assignment for one retry.",
            )
            assert first_checkpoint.status_code == 200
            first_retry = await _retry_boundary_with_live_session(
                api=api,
                stage=stage,
                task_id=task_id,
                session_key=worker_session_key,
                boundary_name="retry",
            )
            assert first_retry.status_code == 200
            assert first_retry.json()["flow"]["current_node_key"] == "implement_change"
            assert (
                first_retry.json()["flow"]["active_attempt_id"]
                == f"attempt.{task_id}.implement_change.02"
            )

            retry_session_key = await current_session_key_after_dispatch_progress(
                session_factory=api.session_factory,
                task_id=task_id,
                client=api.client,
                expected_active_flow_revision_id=first_retry.json()["flow"][
                    "active_flow_revision_id"
                ],
            )
            second_checkpoint, retry_session_key = await _retry_record_checkpoint_with_live_session(
                api=api,
                stage=stage,
                task_id=task_id,
                session_key=retry_session_key,
                outcome="retry",
                summary="second retry request",
                next_step="this second retry must be rejected by budget.",
            )
            assert second_checkpoint.status_code == 200
            second_retry = await _retry_boundary_with_live_session(
                api=api,
                stage=stage,
                task_id=task_id,
                session_key=retry_session_key,
                boundary_name="retry",
            )
            assert second_retry.status_code == 422
            detail = second_retry.json()["detail"]
            assert detail["code"] == "budget_exhausted"
            assert detail["summary"] == "retry budget exhausted for this path"
            assert detail["suggested_next_step"] == (
                "Surface the latest terminal checkpoint to the relevant parent or root so "
                "it can choose a fresh assignment or another legal path."
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_release_green_keeps_missing_required_publication_on_422(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_release_missing_publication"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key, active_flow_revision_id = await drive_minimal_child_to_green(
                api,
                task_id=task_id,
                task_root=task_root,
            )

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert root_node is not None
                assert root_node.current_assignment_id is not None
                root_assignment = await session.get(
                    AssignmentModel,
                    root_node.current_assignment_id,
                )
                assert root_assignment is not None
                root_assignment.produces_json = [
                    {
                        "slot": "missing_release_basis",
                        "description": "Synthetic required release basis for route mapping.",
                        "file_hint": "missing_release_basis.md",
                    }
                ]
                await session.commit()

            release = await release_green(
                client=api.client,
                task_id=task_id,
                session_key=root_session_key,
                active_flow_revision_id=active_flow_revision_id,
            )
            assert release.status_code == 422
            detail = release.json()["detail"]
            assert detail["code"] == "missing_required_publication"
            assert detail["summary"].startswith("missing required publication")
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_release_green_maps_missing_child_current_publication_to_422(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_release_missing_child_publication"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=1,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key, active_flow_revision_id = await drive_minimal_child_to_green(
                api,
                task_id=task_id,
                task_root=task_root,
            )

            async with api.session_factory() as session:
                current_pointer = await session.scalar(
                    select(ArtifactCurrentPointerModel).where(
                        ArtifactCurrentPointerModel.task_id == task_id,
                        ArtifactCurrentPointerModel.owner_node_key == "implement_change",
                        ArtifactCurrentPointerModel.slot == "change_patch",
                    )
                )
                assert current_pointer is not None
                await session.delete(current_pointer)
                await session.commit()

            release = await release_green(
                client=api.client,
                task_id=task_id,
                session_key=root_session_key,
                active_flow_revision_id=active_flow_revision_id,
            )
            assert release.status_code == 422
            detail = release.json()["detail"]
            assert detail["code"] == "missing_required_publication"
            assert detail["summary"].startswith("missing required publication")
    finally:
        await dispose_db_engine()


__all__ = [
    "test_release_green_keeps_missing_required_publication_on_422",
    "test_release_green_maps_missing_child_current_publication_to_422",
    "test_release_green_uses_relational_children_and_maps_stale_checkpoint_to_409",
    "test_retry_budget_exhaustion_surfaces_live_callback_failure",
]
