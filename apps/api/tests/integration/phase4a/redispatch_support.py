from __future__ import annotations

from pathlib import Path
from typing import Any

from autoclaw.persistence import DispatchTurnModel, FlowModel
from autoclaw.runtime.post_commit import drive_runtime_once, drive_runtime_until
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase3.callback_api import ChildDispatchStage
from tests.integration.phase3.control.abort_support import (
    accept_green_boundary,
    assert_parent_redispatch_after_worker_green,
    assert_worker_green_flips_currentness_to_parent_while_worker_dispatch_stays_live,
    open_child_flow_after_yield,
)
from tests.integration.phase3.dispatch_support import (
    current_open_dispatch_id,
    mark_dispatch_provider_completed,
    stage_child_yield,
)
from tests.integration.phase3.runtime_harness.child_dispatch import (
    retry_terminal_green_checkpoint,
)


async def capture_root_gateway_state(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> tuple[str, str, str | None]:
    dispatch_id = await current_open_dispatch_id(session_factory, task_id=task_id)
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        assert dispatch.gateway_session_key is not None
        return dispatch_id, dispatch.gateway_session_key, dispatch.gateway_run_id


async def complete_worker_green_cycle(
    api: Any,
    *,
    task_id: str,
    task_root: Path,
    initial_root_dispatch_id: str,
    active_flow_revision_id: str,
) -> tuple[str, str, str]:
    patch_file = task_root / "workspace" / "change_patch.diff"
    patch_file.parent.mkdir(parents=True, exist_ok=True)
    patch_file.write_text("diff --git a/file.py b/file.py\n", encoding="utf-8")
    verification_file = task_root / "workspace" / "verification_report.md"
    verification_file.write_text("verification ok\n", encoding="utf-8")
    await mark_dispatch_provider_completed(
        api.session_factory,
        dispatch_id=initial_root_dispatch_id,
    )
    child_dispatch_id, child_attempt_id = await open_child_flow_after_yield(
        session_factory=api.session_factory,
        task_id=task_id,
        active_flow_revision_id=active_flow_revision_id,
    )
    await drive_runtime_until(
        lambda: _dispatch_gateway_session_present(
            api.session_factory,
            dispatch_id=child_dispatch_id,
        ),
        task_id=task_id,
        max_cycles=20,
    )
    async with api.session_factory() as session:
        child_dispatch = await session.get(DispatchTurnModel, child_dispatch_id)
        assert child_dispatch is not None
        assert child_dispatch.gateway_session_key is not None
        child_gateway_session_key = child_dispatch.gateway_session_key
    checkpoint, child_gateway_session_key = await retry_terminal_green_checkpoint(
        api,
        stage=ChildDispatchStage(
            root_session_key="",
            worker_session_key=child_gateway_session_key,
            active_flow_revision_id=active_flow_revision_id,
            worker_node_key="implement_change",
        ),
        task_id=task_id,
        summary="Implementation completed.",
        next_step="Return to the parent for review.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(patch_file)},
            {"slot": "verification_report", "path": str(verification_file)},
        ],
    )
    assert checkpoint.status_code == 200
    await drive_runtime_once(task_id=task_id)
    await accept_green_boundary(
        api.session_factory,
        task_id=task_id,
        child_attempt_id=child_attempt_id,
    )
    await assert_worker_green_flips_currentness_to_parent_while_worker_dispatch_stays_live(
        session_factory=api.session_factory,
        task_id=task_id,
        child_dispatch_id=child_dispatch_id,
        task_root=task_root,
    )
    return child_dispatch_id, child_attempt_id, child_gateway_session_key


async def prepare_parent_same_session_case(
    api: Any,
    *,
    task_id: str,
    task_root: Path,
) -> tuple[str, str, str | None, str, str, str]:
    (
        initial_root_dispatch_id,
        initial_root_gateway_session_key,
        initial_root_gateway_run_id,
    ) = await capture_root_gateway_state(
        api.session_factory,
        task_id=task_id,
    )
    active_flow_revision_id = await stage_child_yield(
        api,
        task_id=task_id,
        child_node_key="implement_change",
    )
    (
        child_dispatch_id,
        _child_attempt_id,
        child_gateway_session_key,
    ) = await complete_worker_green_cycle(
        api,
        task_id=task_id,
        task_root=task_root,
        initial_root_dispatch_id=initial_root_dispatch_id,
        active_flow_revision_id=active_flow_revision_id,
    )
    return (
        initial_root_dispatch_id,
        initial_root_gateway_session_key,
        initial_root_gateway_run_id,
        active_flow_revision_id,
        child_dispatch_id,
        child_gateway_session_key,
    )


async def finish_parent_same_session_case(
    api: Any,
    *,
    task_id: str,
    active_flow_revision_id: str,
    child_dispatch_id: str,
    child_gateway_session_key: str,
    initial_root_gateway_session_key: str,
    initial_root_gateway_run_id: str | None,
) -> None:
    await mark_dispatch_provider_completed(
        api.session_factory,
        dispatch_id=child_dispatch_id,
    )
    await assert_parent_redispatch_after_worker_green(
        session_factory=api.session_factory,
        task_id=task_id,
        active_flow_revision_id=active_flow_revision_id,
        child_dispatch_id=child_dispatch_id,
    )
    await assert_parent_redispatch_reused_root_session(
        api.session_factory,
        task_id=task_id,
        child_dispatch_id=child_dispatch_id,
        child_gateway_session_key=child_gateway_session_key,
        initial_root_gateway_session_key=initial_root_gateway_session_key,
        initial_root_gateway_run_id=initial_root_gateway_run_id,
    )


async def _dispatch_gateway_session_present(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    dispatch_id: str,
) -> bool:
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        return dispatch is not None and dispatch.gateway_session_key is not None


async def assert_parent_redispatch_reused_root_session(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    child_dispatch_id: str,
    child_gateway_session_key: str,
    initial_root_gateway_session_key: str,
    initial_root_gateway_run_id: str | None,
) -> None:
    await drive_runtime_until(
        lambda: _current_root_dispatch_ready(
            session_factory,
            task_id=task_id,
            child_dispatch_id=child_dispatch_id,
        ),
        task_id=task_id,
        max_cycles=20,
    )
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        resumed_root_dispatch = await session.get(
            DispatchTurnModel,
            flow.current_open_dispatch_id,
        )
        assert resumed_root_dispatch is not None
        assert resumed_root_dispatch.node_key == "root"
        assert resumed_root_dispatch.previous_dispatch_id == child_dispatch_id
        assert resumed_root_dispatch.gateway_session_key == initial_root_gateway_session_key
        assert resumed_root_dispatch.gateway_session_key != child_gateway_session_key
        assert resumed_root_dispatch.gateway_run_id != initial_root_gateway_run_id


async def assert_parent_redispatch_falls_back_to_fresh_root_session(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    child_dispatch_id: str,
    child_gateway_session_key: str,
    initial_root_gateway_session_key: str,
    initial_root_gateway_run_id: str | None,
) -> None:
    await drive_runtime_until(
        lambda: _current_root_dispatch_ready(
            session_factory,
            task_id=task_id,
            child_dispatch_id=child_dispatch_id,
        ),
        task_id=task_id,
        max_cycles=20,
    )
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        resumed_root_dispatch = await session.get(
            DispatchTurnModel,
            flow.current_open_dispatch_id,
        )
        assert resumed_root_dispatch is not None
        assert resumed_root_dispatch.node_key == "root"
        assert resumed_root_dispatch.previous_dispatch_id == child_dispatch_id
        assert resumed_root_dispatch.gateway_session_key is not None
        assert resumed_root_dispatch.gateway_session_key != initial_root_gateway_session_key
        assert resumed_root_dispatch.gateway_session_key != child_gateway_session_key
        assert resumed_root_dispatch.gateway_run_id != initial_root_gateway_run_id


async def _current_root_dispatch_ready(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    child_dispatch_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None or flow.current_open_dispatch_id is None:
            return False
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        return (
            dispatch is not None
            and dispatch.node_key == "root"
            and dispatch.previous_dispatch_id == child_dispatch_id
            and dispatch.gateway_session_key is not None
        )


__all__ = [
    "assert_parent_redispatch_falls_back_to_fresh_root_session",
    "assert_parent_redispatch_reused_root_session",
    "capture_root_gateway_state",
    "complete_worker_green_cycle",
    "finish_parent_same_session_case",
    "prepare_parent_same_session_case",
]
