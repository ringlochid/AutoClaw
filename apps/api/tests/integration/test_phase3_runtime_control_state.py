from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

import pytest
from app import cli
from app.config import get_settings
from app.db import (
    DispatchCallbackBindingModel,
    DispatchTurnModel,
    FlowModel,
    WorkspaceRootLeaseModel,
)
from app.db.session import dispose_db_engine, get_session_factory
from app.runtime import (
    CheckpointKind,
    CheckpointOutcome,
    EgressBoundary,
    ParentRootToolName,
    accept_boundary,
    call_parent_tool,
    cancel_runtime_flow,
    continue_runtime_flow,
    record_checkpoint,
    runtime_flow_read,
)
from app.schemas.runtime import (
    AssignChildPayload,
    AssignmentIntent,
    CheckpointHandoffRead,
    CheckpointWrite,
    CheckpointWriteBody,
    ParentToolCall,
    ProducedArtifactClaim,
)
from app.schemas.runtime import BoundaryWrite as BoundaryWriteSchema
from sqlalchemy import select
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload


def _delivery_state_path(*, task_root: Path, dispatch_id: str) -> Path:
    return task_root / "_runtime" / "dispatch" / dispatch_id / "delivery-state.json"


def _read_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


async def _prepare_runtime_db(tmp_path: Path) -> Path:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    await cli._cmd_init(
        argparse.Namespace(
            config=str(config_path),
            data_dir=str(data_dir),
            database_url=None,
            host="127.0.0.1",
            port=8123,
            log_level="INFO",
            api_key="api-test-key",
            internal_api_key="internal-test-key",
            force=True,
            skip_db_upgrade=False,
            json=False,
        )
    )
    return config_path


async def _bootstrap_parent_runtime(
    *,
    config_path: Path,
    task_id: str,
    task_root: Path,
    compiler_version: str,
    workflow_key: str = "normal-parent-first-release",
) -> None:
    with cli._command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        async with session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=task_root,
                task_compose=task_compose_payload(workflow_key),
                compiler_version=compiler_version,
            )


async def _stage_child_yield(
    *,
    config_path: Path,
    task_id: str,
    task_root: Path,
    expected_flow_revision_id: str,
    dispatch_id: str,
    child_node_key: str = "implementation_subtree",
) -> str:
    with cli._command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        async with session_factory() as session:
            await call_parent_tool(
                session,
                task_id,
                ParentRootToolName.ASSIGN_CHILD,
                ParentToolCall(
                    tool_name=ParentRootToolName.ASSIGN_CHILD,
                    payload=AssignChildPayload(
                        child_node_key=child_node_key,
                        assignment_intent=AssignmentIntent(
                            summary=f"Stage the {child_node_key} child.",
                            instruction=f"Stage only the current {child_node_key} child.",
                        ),
                    ),
                    expected_structural_revision_id=expected_flow_revision_id,
                ),
            )
            await session.commit()

        async with session_factory() as session:
            yielded = await accept_boundary(
                session,
                task_id,
                BoundaryWriteSchema(boundary=EgressBoundary.YIELD),
            )
            await session.commit()
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert flow is not None
            assert dispatch is not None
            assert yielded.flow.current_node_key == "root"
            assert flow.current_open_dispatch_id == dispatch_id
            assert dispatch.closed_by_boundary == EgressBoundary.YIELD.value
            assert dispatch.control_state == "live"
            assert dispatch.control_deadline_at is not None
            assert dispatch.fenced_at is None
            delivery_state = _read_json(
                _delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert delivery_state["transport_state"] == "accepted"
            assert delivery_state["controller_observation_state"] == "live"
            assert delivery_state["last_controller_terminal_at"] is None
            return yielded.flow.active_flow_revision_id


async def _prove_dispatch_inactive(*, config_path: Path, dispatch_id: str) -> None:
    with cli._command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        async with session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert dispatch is not None
            dispatch.delivery_status = "provider_completed"
            await session.commit()


@pytest.mark.asyncio
async def test_phase3_boundary_waits_for_inactivity_proof_before_opening_replacement_dispatch(
    tmp_path: Path,
) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_wait"

    try:
        await _bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-wait",
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                dispatch_id = flow.current_open_dispatch_id
                assert dispatch_id is not None
                root_attempt_id = flow_read.active_attempt_id

            active_flow_revision_id = await _stage_child_yield(
                config_path=config_path,
                task_id=task_id,
                task_root=task_root,
                expected_flow_revision_id=flow_read.active_flow_revision_id,
                dispatch_id=dispatch_id,
            )

            async with session_factory() as session:
                with pytest.raises(ValueError, match="awaiting inactivity proof"):
                    await continue_runtime_flow(
                        session,
                        task_id,
                        expected_active_flow_revision_id=active_flow_revision_id,
                    )
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                prior_dispatch = await session.get(DispatchTurnModel, dispatch_id)
                flow_read = await runtime_flow_read(session, task_id)
                assert flow is not None
                assert prior_dispatch is not None
                assert flow.current_open_dispatch_id == dispatch_id
                assert flow_read.current_node_key == "root"
                assert flow_read.active_attempt_id == root_attempt_id
                assert prior_dispatch.control_state == "live"
                assert prior_dispatch.control_deadline_at is not None
                assert prior_dispatch.fenced_at is None
                prior_delivery_state = _read_json(
                    _delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
                )
                assert prior_delivery_state["transport_state"] == "accepted"
                assert prior_delivery_state["controller_observation_state"] == "live"

            await _prove_dispatch_inactive(
                config_path=config_path,
                dispatch_id=dispatch_id,
            )

            async with session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                assert flow_read.current_node_key == "root"
                assert flow_read.active_attempt_id == root_attempt_id

            async with session_factory() as session:
                continued = await continue_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=active_flow_revision_id,
                )
                await session.commit()
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                prior_dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert prior_dispatch is not None
                assert prior_dispatch.control_state == "fenced"
                assert prior_dispatch.control_deadline_at is None
                assert prior_dispatch.fenced_at is not None
                assert flow.current_open_dispatch_id is not None
                replacement = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
                assert replacement is not None
                assert continued.current_node_key == "implementation_subtree"
                assert continued.active_attempt_id == replacement.attempt_id
                assert replacement.previous_dispatch_id == dispatch_id
                assert replacement.node_key == "implementation_subtree"
                prior_delivery_state = _read_json(
                    _delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
                )
                assert prior_delivery_state["transport_state"] == "provider_completed"
                assert prior_delivery_state["controller_observation_state"] == "fenced"
                assert prior_delivery_state["superseded_by_dispatch_id"] == replacement.dispatch_id
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_ambiguous_previous_dispatch_blocks_replacement_dispatch(
    tmp_path: Path,
) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_ambiguous"

    try:
        await _bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-ambiguous",
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                dispatch_id = flow.current_open_dispatch_id
                assert dispatch_id is not None

            active_flow_revision_id = await _stage_child_yield(
                config_path=config_path,
                task_id=task_id,
                task_root=task_root,
                expected_flow_revision_id=flow_read.active_flow_revision_id,
                dispatch_id=dispatch_id,
            )

            async with session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                dispatch.control_deadline_at = dispatch.closed_at
                await session.commit()

            async with session_factory() as session:
                with pytest.raises(ValueError, match="timed out"):
                    await continue_runtime_flow(
                        session,
                        task_id,
                        expected_active_flow_revision_id=active_flow_revision_id,
                    )
                await session.commit()
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert flow is not None
                assert dispatch is not None
                assert flow.current_open_dispatch_id == dispatch_id
                assert dispatch.control_state == "ambiguous"
                assert dispatch.control_deadline_at is None
                delivery_state = _read_json(
                    _delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
                )
                assert delivery_state["transport_state"] == "transport_ambiguous"
                assert delivery_state["controller_observation_state"] == "ambiguous"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_cancel_marks_abort_requested_without_auto_fencing(
    tmp_path: Path,
) -> None:
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_cancel"

    try:
        await _bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-cancel",
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                dispatch_id = flow.current_open_dispatch_id
                assert dispatch_id is not None

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
                delivery_state = _read_json(
                    _delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
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
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_cancel_proven"

    try:
        await _bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-cancel-proven",
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                dispatch_id = flow.current_open_dispatch_id
                assert dispatch_id is not None

                await cancel_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=flow_read.active_flow_revision_id,
                )
                await session.commit()

            await _prove_dispatch_inactive(
                config_path=config_path,
                dispatch_id=dispatch_id,
            )

            async with session_factory() as session:
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
                delivery_state = _read_json(
                    _delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
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
    config_path = await _prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_worker_parent_currentness"

    try:
        await _bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-worker-parent-currentness",
            workflow_key="minimal-implement-change",
        )

        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                root_dispatch_id = flow.current_open_dispatch_id
                assert root_dispatch_id is not None

            active_flow_revision_id = await _stage_child_yield(
                config_path=config_path,
                task_id=task_id,
                task_root=task_root,
                expected_flow_revision_id=flow_read.active_flow_revision_id,
                dispatch_id=root_dispatch_id,
                child_node_key="implement_change",
            )
            await _prove_dispatch_inactive(
                config_path=config_path,
                dispatch_id=root_dispatch_id,
            )

            async with session_factory() as session:
                child_flow = await continue_runtime_flow(
                    session,
                    task_id,
                    expected_active_flow_revision_id=active_flow_revision_id,
                )
                await session.commit()
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                child_dispatch_id = flow.current_open_dispatch_id
                assert child_dispatch_id is not None
                child_attempt_id = child_flow.active_attempt_id
                assert child_flow.current_node_key == "implement_change"
                assert child_attempt_id is not None

            patch_source = task_root / "workspace" / "change_patch.diff"
            patch_source.write_text("diff --git a/file.py b/file.py\n", encoding="utf-8")
            verification_source = task_root / "workspace" / "verification_report.md"
            verification_source.write_text("verification ok\n", encoding="utf-8")

            async with session_factory() as session:
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
                await session.commit()

            async with session_factory() as session:
                green = await accept_boundary(
                    session,
                    task_id,
                    BoundaryWriteSchema(boundary=EgressBoundary.GREEN),
                )
                await session.commit()
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.get(DispatchTurnModel, child_dispatch_id)
                flow_read = await runtime_flow_read(session, task_id)
                assert flow is not None
                assert dispatch is not None
                assert green.flow.current_node_key == "implement_change"
                assert green.flow.active_attempt_id == child_attempt_id
                assert flow.current_open_dispatch_id == child_dispatch_id
                assert flow_read.current_node_key == "implement_change"
                assert flow_read.active_attempt_id == child_attempt_id
                assert dispatch.closed_by_boundary == EgressBoundary.GREEN.value
                assert dispatch.control_state == "live"
                delivery_state = _read_json(
                    _delivery_state_path(task_root=task_root, dispatch_id=child_dispatch_id)
                )
                assert delivery_state["controller_observation_state"] == "live"

            await _prove_dispatch_inactive(
                config_path=config_path,
                dispatch_id=child_dispatch_id,
            )

            async with session_factory() as session:
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
