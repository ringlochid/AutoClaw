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
    EgressBoundary,
    ParentRootToolName,
    accept_boundary,
    call_parent_tool,
    cancel_runtime_flow,
    continue_runtime_flow,
    runtime_flow_read,
)
from app.schemas.runtime import (
    AssignChildPayload,
    AssignmentIntent,
    ParentToolCall,
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
) -> None:
    with cli._command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        async with session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=task_root,
                task_compose=task_compose_payload("normal-parent-first-release"),
                compiler_version=compiler_version,
            )


async def _stage_child_yield(
    *,
    config_path: Path,
    task_id: str,
    task_root: Path,
    expected_flow_revision_id: str,
    dispatch_id: str,
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
                        child_node_key="implementation_subtree",
                        assignment_intent=AssignmentIntent(
                            summary="Stage the implementation subtree.",
                            instruction="Stage the current implementation subtree only.",
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
            assert yielded.flow.current_node_key == "implementation_subtree"
            assert flow.current_open_dispatch_id == dispatch_id
            assert dispatch.closed_by_boundary == EgressBoundary.YIELD.value
            assert dispatch.control_state == "live"
            assert dispatch.control_deadline_at is not None
            assert dispatch.fenced_at is None
            delivery_state = _read_json(
                _delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
            )
            assert delivery_state["transport_state"] == "accepted"
            assert (
                delivery_state["controller_observation_state"]
                == "boundary_accepted_waiting_terminal"
            )
            assert delivery_state["last_controller_terminal_at"] is None
            return yielded.flow.active_flow_revision_id


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

            active_flow_revision_id = await _stage_child_yield(
                config_path=config_path,
                task_id=task_id,
                task_root=task_root,
                expected_flow_revision_id=flow_read.active_flow_revision_id,
                dispatch_id=dispatch_id,
            )

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
