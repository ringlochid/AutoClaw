from __future__ import annotations

from pathlib import Path

import pytest
from app.db import AssignmentModel, DispatchTurnModel, FlowModel
from app.db.session import dispose_db_engine
from sqlalchemy import select
from tests.helpers.runtime_seed import load_workflow_definition
from tests.integration.phase3.dispatch_support import mark_dispatch_provider_completed
from tests.integration.phase3.runtime_support import (
    assign_child,
    boundary,
    continue_flow,
    current_session_key,
    drive_minimal_child_to_green,
    parent_tool,
    persist_bootstrap,
    phase3_runtime_api,
    prepare_runtime_db,
    record_checkpoint,
    runtime_read_json,
    stage_child_dispatch,
)


@pytest.mark.asyncio
async def test_parent_retry_boundary_maps_to_illegal_caller(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_parent_retry_illegal"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            retry = await boundary(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                boundary_name="retry",
            )
            assert retry.status_code == 422
            detail = retry.json()["detail"]
            assert detail["code"] == "illegal_caller"
            assert detail["summary"] == "parent/root retry is illegal"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_continue_route_maps_incomplete_staged_child_assignment_to_illegal_state(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_incomplete_staged_child_continue"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with phase3_runtime_api(config_path) as api:
            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            assign = await assign_child(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                child_node_key="implementation_subtree",
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert assign.status_code == 200
            yielded = await boundary(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                boundary_name="yield",
            )
            assert yielded.status_code == 200

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
                assert dispatch is not None
                assert dispatch.staged_child_assignment_id is not None
                assignment = await session.get(AssignmentModel, dispatch.staged_child_assignment_id)
                assert assignment is not None
                assignment.current_attempt_id = None
                paused_dispatch_id = dispatch.dispatch_id
                await session.commit()

            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=paused_dispatch_id,
            )
            resumed = await continue_flow(
                api.client,
                task_id=task_id,
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert resumed.status_code == 422
            detail = resumed.json()["detail"]
            assert detail["code"] == "illegal_state"
            assert detail["summary"] == "staged child assignment is incomplete"
            assert (
                "repair or restage a complete child continuation" in detail["suggested_next_step"]
            )
    finally:
        await dispose_db_engine()


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
            checkpoint = await record_checkpoint(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                outcome="green",
                summary="Implementation completed but outputs were not published.",
                next_step="Boundary green should still reject until required outputs exist.",
            )
            assert checkpoint.status_code == 200

            worker_green = await boundary(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                boundary_name="green",
            )
            assert worker_green.status_code == 422
            detail = worker_green.json()["detail"]
            assert detail["code"] == "boundary_precondition_failed"
            assert detail["summary"].startswith("missing required publication")
    finally:
        await dispose_db_engine()


__all__ = [
    "test_continue_route_maps_incomplete_staged_child_assignment_to_illegal_state",
    "test_parent_retry_boundary_maps_to_illegal_caller",
    "test_worker_green_missing_required_publication_maps_to_boundary_precondition_failed",
    "test_yield_after_release_green_maps_to_boundary_precondition_failed",
]
