from __future__ import annotations

from pathlib import Path
from typing import Any

from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import (
    DispatchContinuityStateModel,
    DispatchTurnModel,
    FlowModel,
    NodeSessionModel,
)
from autoclaw.runtime import continue_runtime_flow, pause_runtime_flow, runtime_flow_read
from autoclaw.runtime.post_commit import drive_runtime_once, drive_runtime_until
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_dispatch_support import delivery_state_path, read_json
from tests.integration.gateway.dispatch_gateway_support import (
    wait_for_latest_dispatch_snapshot,
)


async def pause_dispatch_and_assert_abort_requested(
    api: Any,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    async with api.session_factory() as session:
        flow_read = await runtime_flow_read(session, task_id)
        paused = await pause_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=flow_read.active_flow_revision_id,
        )
        await session.commit()
        assert paused.flow.status.value == "paused"

    await drive_runtime_once(task_id=task_id)

    async with api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert flow is not None
        assert dispatch is not None
        assert flow.status == "paused"
        assert dispatch.control_state in {"abort_requested", "fenced"}


async def assert_pause_dispatch_fenced_after_wait_ok(
    api: Any,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    snapshot = await wait_for_latest_dispatch_snapshot(
        api.session_factory,
        task_id=task_id,
        predicate=lambda current: (
            current.flow.status == "paused"
            and current.flow.current_open_dispatch_id is None
            and current.dispatch.control_state == "fenced"
            and current.dispatch.fenced_at is not None
            and current.node_session is not None
            and current.node_session.session_status == "fenced"
            and current.node_session.closed_at is not None
        ),
        timeout_seconds=5.0,
        drive_runtime=True,
    )
    assert snapshot.flow.status == "paused"
    assert snapshot.flow.current_open_dispatch_id is None
    assert snapshot.dispatch.control_state == "fenced"
    assert snapshot.dispatch.fenced_at is not None
    assert snapshot.node_session is not None
    assert snapshot.node_session.session_status == "fenced"
    assert snapshot.node_session.closed_at is not None


async def force_pause_timeout_fence(
    api: Any,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    async with api.session_factory() as session:
        flow_read = await runtime_flow_read(session, task_id)
        paused = await pause_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=flow_read.active_flow_revision_id,
        )
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        dispatch.control_deadline_at = dispatch.closed_at
        await session.commit()
        assert paused.flow.status.value == "paused"

    await drive_runtime_until(
        lambda: dispatch_fenced_and_cleared(
            api.session_factory,
            task_id=task_id,
            dispatch_id=dispatch_id,
        ),
        task_id=task_id,
        max_cycles=40,
    )


async def continue_fenced_paused_dispatch(
    api: Any,
    *,
    task_id: str,
    dispatch_id: str,
) -> str | None:
    async with api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        node_session = await session.get(NodeSessionModel, f"node-session.{dispatch_id}")
        assert flow is not None
        assert dispatch is not None
        assert node_session is not None
        assert flow.status == "paused"
        assert flow.current_open_dispatch_id is None
        assert dispatch.control_state == "fenced"
        assert dispatch.delivery_status == "transport_ambiguous"
        assert node_session.session_status == "fenced"
        assert dispatch.flow_node_id is not None
        assert dispatch.assignment_id is not None
        assert dispatch.attempt_id is not None
        assert dispatch.gateway_session_key is not None
        session.add(
            NodeSessionModel(
                node_session_id=f"node-session.{dispatch_id}.stale-live",
                flow_node_id=dispatch.flow_node_id,
                assignment_id=dispatch.assignment_id,
                attempt_id=dispatch.attempt_id,
                dispatch_id=dispatch_id,
                session_key=dispatch.gateway_session_key,
                session_status="live",
                opened_at=dispatch.opened_at,
            )
        )
        paused = await runtime_flow_read(session, task_id)
        resumed = await continue_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=paused.active_flow_revision_id,
        )
        await session.commit()
        assert resumed.status.value == "running"
        return flow.current_open_dispatch_id


async def assert_pause_timeout_replacement_dispatch(
    api: Any,
    *,
    dispatch_id: str,
    task_id: str,
    task_root: Path,
) -> None:
    async with api.session_factory() as session:
        original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
        original_continuity_state = await session.get(
            DispatchContinuityStateModel,
            dispatch_id,
        )
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        replacement_dispatch_id = flow.current_open_dispatch_id
        replacement_dispatch = await session.get(
            DispatchTurnModel,
            replacement_dispatch_id,
        )
        assert original_dispatch is not None
        assert original_continuity_state is not None
        assert replacement_dispatch is not None
        assert replacement_dispatch.dispatch_id != dispatch_id
        assert replacement_dispatch.previous_dispatch_id == dispatch_id
        assert original_dispatch.superseded_by_dispatch_id == replacement_dispatch.dispatch_id
        assert replacement_dispatch.attempt_id == original_dispatch.attempt_id
        assert original_continuity_state.session_key_present is False
        assert original_continuity_state.invalidation_reason == (
            f"superseded:{replacement_dispatch.dispatch_id}"
        )

    delivery_state = read_json(delivery_state_path(task_root=task_root, dispatch_id=dispatch_id))
    assert delivery_state["transport_state"] == "transport_ambiguous"


async def wait_ok_payload_for_dispatch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    dispatch_id: str,
) -> dict[str, object]:
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        assert isinstance(dispatch.gateway_run_id, str)
        return agent_wait_fixture(status="ok", run_id=dispatch.gateway_run_id)


async def dispatch_fenced_and_cleared(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    dispatch_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        return (
            flow is not None
            and dispatch is not None
            and flow.current_open_dispatch_id is None
            and dispatch.control_state == "fenced"
        )


__all__ = [
    "assert_pause_dispatch_fenced_after_wait_ok",
    "assert_pause_timeout_replacement_dispatch",
    "continue_fenced_paused_dispatch",
    "dispatch_fenced_and_cleared",
    "force_pause_timeout_fence",
    "pause_dispatch_and_assert_abort_requested",
    "wait_ok_payload_for_dispatch",
]
