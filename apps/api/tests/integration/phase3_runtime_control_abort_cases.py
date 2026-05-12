from __future__ import annotations

from pathlib import Path

import pytest
from app.db import (
    DispatchCallbackBindingModel,
    DispatchTurnModel,
    FlowModel,
    WorkspaceRootLeaseModel,
)
from app.db.session import dispose_db_engine
from app.runtime import (
    CheckpointKind,
    CheckpointOutcome,
    EgressBoundary,
    accept_boundary,
    cancel_runtime_flow,
    continue_runtime_flow,
    record_checkpoint,
    runtime_flow_read,
)
from app.runtime.post_commit import wait_for_runtime_effects
from app.schemas.runtime import BoundaryWrite as BoundaryWriteSchema
from app.schemas.runtime import (
    CheckpointHandoffRead,
    CheckpointWrite,
    CheckpointWriteBody,
    ProducedArtifactClaim,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase3_runtime_dispatch_support import (
    current_open_dispatch_id,
    delivery_state_path,
    mark_dispatch_provider_completed,
    read_json,
    stage_child_yield,
)
from tests.integration.phase3_runtime_support import (
    bootstrap_parent_runtime,
    phase3_runtime_api,
    prepare_runtime_db,
    write_workspace_file,
)


async def record_green_checkpoint_for_child(
    *,
    session: AsyncSession,
    task_id: str,
    task_root: Path,
) -> None:
    patch_source = write_workspace_file(
        task_root,
        "workspace/change_patch.diff",
        "diff --git a/file.py b/file.py\n",
    )
    verification_source = write_workspace_file(
        task_root,
        "workspace/verification_report.md",
        "verification ok\n",
    )
    await record_checkpoint(
        session,
        task_id,
        CheckpointWrite(
            checkpoint=CheckpointWriteBody(
                checkpoint_kind=CheckpointKind.TERMINAL,
                outcome=CheckpointOutcome.GREEN,
                handoff=CheckpointHandoffRead(
                    summary="Implementation completed.",
                    next_step="Return to the parent for review.",
                ),
                produced_artifacts=(
                    ProducedArtifactClaim(slot="change_patch", path=patch_source),
                    ProducedArtifactClaim(
                        slot="verification_report",
                        path=verification_source,
                    ),
                ),
            )
        ),
    )


async def open_child_flow_after_yield(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    active_flow_revision_id: str,
) -> tuple[str, str]:
    async with session_factory() as session:
        child_flow = await continue_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=active_flow_revision_id,
        )
        await session.commit()
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        assert child_flow.active_attempt_id is not None
        return flow.current_open_dispatch_id, child_flow.active_attempt_id


async def assert_worker_green_kept_current(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    child_dispatch_id: str,
    child_attempt_id: str,
    task_root: Path,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, child_dispatch_id)
        flow_read = await runtime_flow_read(session, task_id)
        assert flow is not None
        assert dispatch is not None
        assert flow.current_open_dispatch_id == child_dispatch_id
        assert flow_read.current_node_key == "implement_change"
        assert flow_read.active_attempt_id == child_attempt_id
        assert dispatch.closed_by_boundary == EgressBoundary.GREEN.value
        assert dispatch.control_state == "live"
        await wait_for_runtime_effects(task_id=task_id)
        delivery_state = read_json(
            delivery_state_path(task_root=task_root, dispatch_id=child_dispatch_id)
        )
        assert delivery_state["controller_observation_state"] == "live"


@pytest.mark.asyncio
async def test_phase3_cancel_marks_abort_requested_without_auto_fencing(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_cancel"

    try:
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-cancel",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                cancelled = await cancel_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=flow_read.active_flow_revision_id,
                )
                await session.commit()
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                binding = await session.scalar(
                    select(DispatchCallbackBindingModel).where(
                        DispatchCallbackBindingModel.dispatch_id == dispatch_id
                    )
                )
                lease = await session.scalar(
                    select(WorkspaceRootLeaseModel).where(
                        WorkspaceRootLeaseModel.task_id == task_id,
                        WorkspaceRootLeaseModel.lease_status == "live",
                    )
                )
                assert flow is not None
                assert dispatch is not None
                assert binding is not None
                assert cancelled.status.value == "cancelled"
                assert flow.current_open_dispatch_id == dispatch_id
                assert dispatch.control_state == "abort_requested"
                assert dispatch.control_deadline_at is not None
                assert dispatch.fenced_at is None
                assert dispatch.status == "closed"
                assert binding.binding_status == "revoked"
                assert binding.revoked_at is not None
                if lease is not None:
                    assert lease.lease_status == "live"
                    assert lease.released_at is None
                await wait_for_runtime_effects(task_id=task_id)
                delivery_state = read_json(
                    delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
                )
                assert delivery_state["transport_state"] == "accepted"
                assert delivery_state["controller_observation_state"] == "abort_requested"
                assert delivery_state["last_controller_terminal_at"] is None
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_cancel_fences_after_inactivity_is_proven(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_cancel_proven"

    try:
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-cancel-proven",
        )

        async with phase3_runtime_api(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                await cancel_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=flow_read.active_flow_revision_id,
                )
                await session.commit()
            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=dispatch_id,
            )
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                cancelled = await cancel_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=flow_read.active_flow_revision_id,
                )
                await session.commit()
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                lease = await session.scalar(
                    select(WorkspaceRootLeaseModel).where(
                        WorkspaceRootLeaseModel.task_id == task_id,
                        WorkspaceRootLeaseModel.lease_status == "live",
                    )
                )
                assert flow is not None
                assert dispatch is not None
                assert cancelled.status.value == "cancelled"
                assert flow.current_open_dispatch_id is None
                assert dispatch.control_state == "fenced"
                assert dispatch.control_deadline_at is None
                assert dispatch.fenced_at is not None
                assert lease is None
                await wait_for_runtime_effects(task_id=task_id)
                delivery_state = read_json(
                    delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
                )
                assert delivery_state["transport_state"] == "provider_completed"
                assert delivery_state["controller_observation_state"] == "fenced"
                assert delivery_state["last_controller_terminal_at"] is not None
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_worker_green_keeps_worker_current_until_parent_redispatch(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_worker_parent_currentness"

    try:
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-worker-parent-currentness",
            workflow_key="minimal-implement-change",
        )

        async with phase3_runtime_api(config_path) as api:
            root_dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            active_flow_revision_id = await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implement_change",
            )
            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=root_dispatch_id,
            )
            child_dispatch_id, child_attempt_id = await open_child_flow_after_yield(
                session_factory=api.session_factory,
                task_id=task_id,
                active_flow_revision_id=active_flow_revision_id,
            )
            async with api.session_factory() as session:
                await record_green_checkpoint_for_child(
                    session=session,
                    task_id=task_id,
                    task_root=task_root,
                )
                await session.commit()
            async with api.session_factory() as session:
                green = await accept_boundary(
                    session,
                    task_id,
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                assert green.flow.current_node_key == "implement_change"
                assert green.flow.active_attempt_id == child_attempt_id
            await assert_worker_green_kept_current(
                session_factory=api.session_factory,
                task_id=task_id,
                child_dispatch_id=child_dispatch_id,
                child_attempt_id=child_attempt_id,
                task_root=task_root,
            )
            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=child_dispatch_id,
            )
            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                assert flow_read.current_node_key == "implement_change"
                assert flow_read.active_attempt_id == child_attempt_id
                returned_parent = await continue_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=active_flow_revision_id,
                )
                await session.commit()
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                parent_dispatch_id = flow.current_open_dispatch_id
                assert parent_dispatch_id is not None
                parent_dispatch = await session.get(DispatchTurnModel, parent_dispatch_id)
                assert parent_dispatch is not None
                assert parent_dispatch.previous_dispatch_id == child_dispatch_id
                assert returned_parent.current_node_key == "root"
                assert returned_parent.active_attempt_id == parent_dispatch.attempt_id
    finally:
        await dispose_db_engine()


__all__ = [
    "test_phase3_cancel_fences_after_inactivity_is_proven",
    "test_phase3_cancel_marks_abort_requested_without_auto_fencing",
    "test_phase3_worker_green_keeps_worker_current_until_parent_redispatch",
]
