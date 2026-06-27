from __future__ import annotations

from pathlib import Path

from autoclaw.persistence import (
    DispatchTurnModel,
    FlowModel,
    WorkspaceRootLeaseModel,
)
from autoclaw.runtime import cancel_runtime_flow, runtime_flow_read
from autoclaw.runtime.post_commit import drive_runtime_once, drive_runtime_until
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_support import (
    live_node_session_key_for_dispatch,
    write_workspace_file,
)
from tests.helpers.runtime_support import (
    record_checkpoint as callback_record_checkpoint,
)
from tests.helpers.runtime_support.dispatch import delivery_state_path, read_json


async def cancel_flow(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> None:
    async with session_factory() as session:
        flow_read = await runtime_flow_read(session, task_id)
        cancelled = await cancel_runtime_flow(
            session,
            task_id,
            expected_active_flow_revision_id=flow_read.active_flow_revision_id,
        )
        await session.commit()
        assert cancelled.status.value == "cancelled"


async def assert_cancel_request_open(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    dispatch_id: str,
    task_root: Path,
) -> None:
    async with session_factory() as session:
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
        assert flow.current_open_dispatch_id == dispatch_id
        assert dispatch.control_state == "abort_requested"
        assert dispatch.control_deadline_at is not None
        assert dispatch.fenced_at is None
        if lease is not None:
            assert lease.lease_status == "live"
            assert lease.released_at is None
        await drive_runtime_once(task_id=task_id)
        delivery_state = read_json(
            delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
        )
        assert delivery_state["transport_state"] == "accepted"
        assert delivery_state["last_controller_terminal_at"] is None


async def assert_cancelled_flow_fenced(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    dispatch_id: str,
    task_root: Path,
) -> None:
    await drive_runtime_until(
        lambda: _cancelled_flow_fenced(
            session_factory,
            task_id=task_id,
            dispatch_id=dispatch_id,
        ),
        task_id=task_id,
        max_cycles=20,
    )
    async with session_factory() as session:
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
        assert flow.status == "cancelled"
        assert flow.current_open_dispatch_id is None
        assert dispatch.control_state == "fenced"
        assert dispatch.control_deadline_at is None
        assert dispatch.fenced_at is not None
        assert lease is None
        delivery_state = read_json(
            delivery_state_path(task_root=task_root, dispatch_id=dispatch_id)
        )
        assert delivery_state["transport_state"] in {"accepted", "provider_completed"}
        assert delivery_state["last_controller_terminal_at"] is not None


async def _cancelled_flow_fenced(
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
            and flow.status == "cancelled"
            and flow.current_open_dispatch_id is None
            and dispatch.control_state == "fenced"
            and dispatch.fenced_at is not None
        )


async def record_green_checkpoint_for_child(
    *,
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    task_root: Path,
    child_dispatch_id: str,
) -> None:
    worker_session_key = await _live_session_key_for_dispatch(
        session_factory=session_factory,
        task_id=task_id,
        dispatch_id=child_dispatch_id,
    )
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
    response = await callback_record_checkpoint(
        client,
        task_id=task_id,
        session_key=worker_session_key,
        checkpoint_kind="terminal",
        outcome="green",
        summary="Implementation completed.",
        next_step="Return to the parent for review.",
        produced_artifacts=(
            {"slot": "change_patch", "path": str(patch_source)},
            {"slot": "verification_report", "path": str(verification_source)},
        ),
    )
    assert response.status_code == 200, response.text


async def _live_session_key_for_dispatch(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    dispatch_id: str,
) -> str:
    live_session_key: str | None = None

    async def live_session_ready() -> bool:
        nonlocal live_session_key
        async with session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            live_session_key = await live_node_session_key_for_dispatch(
                session,
                dispatch=dispatch,
            )
            return live_session_key is not None

    try:
        await drive_runtime_until(
            live_session_ready,
            task_id=task_id,
            max_cycles=40,
        )
    except AssertionError as exc:
        raise AssertionError(
            f"dispatch '{dispatch_id}' did not expose a live node session key"
        ) from exc
    assert live_session_key is not None
    return live_session_key
