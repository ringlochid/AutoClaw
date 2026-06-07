from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest
from autoclaw.persistence import AttemptCheckpointModel, DispatchTurnModel, FlowModel
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.post_commit import drive_runtime_once
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_dispatch_support import mark_dispatch_provider_completed
from tests.helpers.runtime_support import (
    assign_child,
    boundary,
    continue_flow,
    current_session_key,
    pause_flow,
    persist_bootstrap,
    prepare_runtime_db,
    record_checkpoint,
    runtime_api_context,
    runtime_read_json,
    set_dispatch_drain_timeout,
    stage_child_dispatch,
    write_workspace_file,
)
from tests.helpers.seeded_runtime_support import load_workflow_definition

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def assert_paused_staged_assignment(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    paused_dispatch_id: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, paused_dispatch_id)
        assert flow is not None
        assert dispatch is not None
        assert flow.status == "paused"
        assert flow.current_open_dispatch_id == paused_dispatch_id
        assert dispatch.control_state == "abort_requested"
        assert dispatch.control_deadline_at is not None
        assert dispatch.fenced_at is None
        assert dispatch.staged_child_assignment_id is not None


async def assert_resumed_staged_assignment(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    paused_dispatch_id: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        prior_dispatch = await session.get(DispatchTurnModel, paused_dispatch_id)
        assert flow is not None
        assert prior_dispatch is not None
        assert flow.current_open_dispatch_id is not None
        replacement = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert replacement is not None
        assert prior_dispatch.control_state == "fenced"
        assert replacement.previous_dispatch_id == paused_dispatch_id
        assert replacement.staged_child_assignment_id == prior_dispatch.staged_child_assignment_id


async def assert_staged_assignment_can_only_yield(
    *,
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    active_flow_revision_id: str,
) -> None:
    resumed_session_key = await current_session_key(
        session_factory=session_factory,
        task_id=task_id,
    )
    second_assign = await assign_child(
        client,
        task_id=task_id,
        session_key=resumed_session_key,
        child_node_key="review_change",
        active_flow_revision_id=active_flow_revision_id,
        summary="should fail",
        instruction="should fail",
    )
    assert second_assign.status_code == 422
    assert "staging a child assignment" in second_assign.json()["detail"]["summary"]
    yielded = await boundary(
        client,
        task_id=task_id,
        session_key=resumed_session_key,
        boundary_name="yield",
    )
    assert yielded.status_code == 200
    assert yielded.json()["flow"]["current_node_key"] == "implementation_subtree"


@pytest.mark.asyncio
async def test_pause_revokes_callback_route_access(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_pause_contract"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with runtime_api_context(config_path) as api:
            session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            pause = await pause_flow(
                api.client,
                task_id=task_id,
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert pause.status_code == 200
            rejected = await assign_child(
                api.client,
                task_id=task_id,
                session_key=session_key,
                child_node_key="implementation_subtree",
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
                summary="blocked",
                instruction="blocked",
            )
            assert rejected.status_code == 422
            assert rejected.json()["detail"]["summary"] == "inactive callback session key"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_callback_authority_uses_live_node_session_key_not_dispatch_echo(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_callback_authority_node_session"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with runtime_api_context(config_path) as api:
            session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
                assert dispatch is not None
                dispatch.gateway_session_key = "dispatch.echo.should.not.authorize"
                await session.commit()

            assert (
                await current_session_key(
                    session_factory=api.session_factory,
                    task_id=task_id,
                )
                == session_key
            )
            assign = await assign_child(
                api.client,
                task_id=task_id,
                session_key=session_key,
                child_node_key="implementation_subtree",
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert assign.status_code == 200
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_pause_continue_waits_for_inactivity_before_reopening_staged_child_assignment(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_pause_resume_stage"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with runtime_api_context(config_path) as api:
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
            current_flow_revision_id = assign.json()["flow"]["active_flow_revision_id"]
            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                paused_dispatch_id = flow.current_open_dispatch_id
            pause = await pause_flow(
                api.client,
                task_id=task_id,
                active_flow_revision_id=current_flow_revision_id,
            )
            assert pause.status_code == 200
            paused_flow_revision_id = pause.json()["flow"]["active_flow_revision_id"]
            await assert_paused_staged_assignment(
                session_factory=api.session_factory,
                task_id=task_id,
                paused_dispatch_id=paused_dispatch_id,
            )

            blocked_continue = await continue_flow(
                api.client,
                task_id=task_id,
                active_flow_revision_id=paused_flow_revision_id,
            )
            assert blocked_continue.status_code == 422
            assert "awaiting inactivity proof" in blocked_continue.json()["detail"]["summary"]

            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=paused_dispatch_id,
            )
            resumed = await continue_flow(
                api.client,
                task_id=task_id,
                active_flow_revision_id=paused_flow_revision_id,
            )
            assert resumed.status_code == 200
            await assert_resumed_staged_assignment(
                session_factory=api.session_factory,
                task_id=task_id,
                paused_dispatch_id=paused_dispatch_id,
            )
            await assert_staged_assignment_can_only_yield(
                client=api.client,
                session_factory=api.session_factory,
                task_id=task_id,
                active_flow_revision_id=resumed.json()["active_flow_revision_id"],
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_checkpoint_route_rejects_undeclared_artifact_slot(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_bad_artifact"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=4,
        )

        async with runtime_api_context(config_path) as api:
            stage = await stage_child_dispatch(api, task_id=task_id)
            bad_artifact = write_workspace_file(
                task_root,
                "workspace/typo_artifact.md",
                "typo artifact",
            )
            checkpoint = await record_checkpoint(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                outcome="green",
                summary="done",
                next_step="close",
                produced_artifacts=[{"slot": "typo_output", "path": str(bad_artifact)}],
            )
            assert checkpoint.status_code == 400
            assert checkpoint.json()["detail"]["code"] == "invalid_request_shape"
            assert "not declared" in checkpoint.json()["detail"]["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_checkpoint_transient_surface_under_task_root_is_copied_into_transfers(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_transient_copy"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("minimal_implement_change"),
            revision_no=4,
        )

        async with runtime_api_context(config_path) as api:
            stage = await stage_child_dispatch(api, task_id=task_id)
            patch_file = write_workspace_file(
                task_root,
                "workspace/change_patch.diff",
                "diff --git a b",
            )
            transient_file = write_workspace_file(
                task_root,
                "workspace/workspace-note.md",
                "mutable workspace note",
            )
            checkpoint = await record_checkpoint(
                api.client,
                task_id=task_id,
                session_key=stage.worker_session_key,
                outcome="green",
                summary="done",
                next_step="close",
                produced_artifacts=[{"slot": "change_patch", "path": str(patch_file)}],
                transient_surfaces=[
                    {
                        "path": str(transient_file),
                        "description": "Workspace handoff note.",
                    }
                ],
            )
            assert checkpoint.status_code == 200
            await drive_runtime_once(task_id=task_id)

            async with api.session_factory() as session:
                checkpoint_row = await session.scalar(
                    select(AttemptCheckpointModel).order_by(
                        AttemptCheckpointModel.recorded_at.desc()
                    )
                )
                assert checkpoint_row is not None
                transient_path = Path(cast(str, checkpoint_row.transient_refs_json[0]["path"]))
                assert await asyncio.to_thread(transient_path.is_file)
                assert transient_path.is_relative_to(task_root / "tmp" / "transfers")
                assert transient_path != transient_file.resolve()
    finally:
        await dispose_db_engine()


__all__ = [
    "test_checkpoint_route_rejects_undeclared_artifact_slot",
    "test_checkpoint_transient_surface_under_task_root_is_copied_into_transfers",
    "test_pause_continue_waits_for_inactivity_before_reopening_staged_child_assignment",
    "test_pause_revokes_callback_route_access",
]
