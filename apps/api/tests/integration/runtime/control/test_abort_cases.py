from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import DispatchTurnModel, FlowModel
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.clock import dispatch_control_deadline
from autoclaw.runtime.post_commit import drive_runtime_once, wait_for_runtime_effects
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import (
    bootstrap_parent_runtime,
    prepare_runtime_db,
    retry_terminal_green_checkpoint,
    runtime_api_context,
    runtime_read_json,
    set_dispatch_drain_timeout,
    stage_child_dispatch,
)
from tests.helpers.runtime_support.dispatch import current_open_dispatch_id
from tests.helpers.runtime_support.dispatch_progression import (
    accept_green_boundary,
    assert_parent_redispatch_after_worker_green,
    assert_worker_green_flips_currentness_to_parent_while_worker_dispatch_stays_live,
)
from tests.integration.runtime.control.abort_support import (
    assert_cancel_request_open,
    assert_cancelled_flow_fenced,
    cancel_flow,
)


async def _wait_ok_payload_for_dispatch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    dispatch_id: str,
) -> dict[str, object]:
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        assert isinstance(dispatch.gateway_run_id, str)
        return agent_wait_fixture(status="ok", run_id=dispatch.gateway_run_id)


def _worker_green_artifacts(task_root: Path) -> list[dict[str, str]]:
    patch_path = task_root / "workspace" / "change_patch.diff"
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text("diff --git a/file.py b/file.py\n", encoding="utf-8")
    verification_path = task_root / "workspace" / "verification_report.md"
    verification_path.write_text("verification ok\n", encoding="utf-8")
    return [
        {
            "slot": "change_patch",
            "path": str(patch_path),
        },
        {
            "slot": "verification_report",
            "path": str(verification_path),
        },
    ]


async def _prepare_worker_green_parent_cycle(
    api: Any,
    *,
    task_id: str,
    task_root: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> tuple[str, str, str]:
    root_dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
    openclaw_gateway_test_server.set_default_method_payload(
        "agent.wait",
        await _wait_ok_payload_for_dispatch(
            api.session_factory,
            dispatch_id=root_dispatch_id,
        ),
    )
    stage = await stage_child_dispatch(
        api,
        task_id=task_id,
        child_node_key="implement_change",
    )
    child_dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
    child_flow = await runtime_read_json(api.client, task_id)
    child_attempt_id = child_flow["active_attempt_id"]
    assert isinstance(child_attempt_id, str)
    checkpoint, _ = await retry_terminal_green_checkpoint(
        api,
        stage=stage,
        task_id=task_id,
        summary="Implementation completed.",
        next_step="Return to the parent for review.",
        produced_artifacts=_worker_green_artifacts(task_root),
    )
    assert checkpoint.status_code == 200
    await wait_for_runtime_effects(task_id=task_id)
    return stage.active_flow_revision_id, child_dispatch_id, child_attempt_id


@pytest.mark.asyncio
async def test_cancel_marks_abort_requested_without_auto_fencing(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_cancel"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-cancel",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await cancel_flow(api.session_factory, task_id=task_id)
            await assert_cancel_request_open(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
                task_root=task_root,
            )
            assert any(
                request.method == "sessions.abort"
                for request in openclaw_gateway_test_server.requests
            )
            assert any(
                request.method == "agent.wait" for request in openclaw_gateway_test_server.requests
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_cancel_fences_after_inactivity_is_proven(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_cancel_proven"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-cancel-proven",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            await cancel_flow(api.session_factory, task_id=task_id)
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await _wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=dispatch_id,
                ),
            )
            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
            await assert_cancelled_flow_fenced(
                session_factory=api.session_factory,
                task_id=task_id,
                dispatch_id=dispatch_id,
                task_root=task_root,
            )
            assert any(
                request.method == "sessions.abort"
                for request in openclaw_gateway_test_server.requests
            )
            assert any(
                request.method == "agent.wait" for request in openclaw_gateway_test_server.requests
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_cancel_rebases_abort_deadline_from_new_request_time(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_cancel_rebases_abort_deadline"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-cancel-rebases-abort-deadline",
        )

        async with runtime_api_context(config_path) as api:
            dispatch_id = await current_open_dispatch_id(api.session_factory, task_id=task_id)
            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                stale_deadline = dispatch.opened_at
                assert stale_deadline is not None
                dispatch.control_deadline_at = stale_deadline
                await session.commit()

            await cancel_flow(api.session_factory, task_id=task_id)

            async with api.session_factory() as session:
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None
                assert dispatch.control_state == "abort_requested"
                assert dispatch.abort_requested_at is not None
                assert dispatch.control_deadline_at == dispatch_control_deadline(
                    base=dispatch.abort_requested_at
                )
                assert dispatch.control_deadline_at is not None
                assert dispatch.control_deadline_at > stale_deadline
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_worker_green_flips_currentness_to_parent_before_parent_redispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_worker_parent_currentness"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-worker-parent-currentness",
            workflow_key="minimal-implement-change",
        )

        async with runtime_api_context(config_path) as api:
            (
                active_flow_revision_id,
                child_dispatch_id,
                child_attempt_id,
            ) = await _prepare_worker_green_parent_cycle(
                api,
                task_id=task_id,
                task_root=task_root,
                openclaw_gateway_test_server=openclaw_gateway_test_server,
            )
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
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                await _wait_ok_payload_for_dispatch(
                    api.session_factory,
                    dispatch_id=child_dispatch_id,
                ),
            )
            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
            await assert_parent_redispatch_after_worker_green(
                session_factory=api.session_factory,
                task_id=task_id,
                active_flow_revision_id=active_flow_revision_id,
                child_dispatch_id=child_dispatch_id,
            )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_parent_redispatch_reuses_latest_fenced_child_even_if_already_linked(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_parent_redispatch_latest_fenced_child"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="runtime-parent-redispatch-latest-fenced-child",
            workflow_key="minimal-implement-change",
        )

        async with runtime_api_context(config_path) as api:
            (
                active_flow_revision_id,
                child_dispatch_id,
                child_attempt_id,
            ) = await _prepare_worker_green_parent_cycle(
                api,
                task_id=task_id,
                task_root=task_root,
                openclaw_gateway_test_server=openclaw_gateway_test_server,
            )
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

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                child_dispatch = await session.get(DispatchTurnModel, child_dispatch_id)
                assert flow is not None
                assert child_dispatch is not None
                assert isinstance(child_dispatch.previous_dispatch_id, str)

                flow.current_open_dispatch_id = None
                child_dispatch.control_state = "fenced"
                child_dispatch.closed_at = child_dispatch.closed_at or datetime.now(UTC)
                child_dispatch.fenced_at = child_dispatch.fenced_at or datetime.now(UTC)
                child_dispatch.delivery_status = "provider_completed"
                child_dispatch.superseded_by_dispatch_id = child_dispatch.previous_dispatch_id
                await session.commit()

            await drive_runtime_once(task_id=task_id)
            await assert_parent_redispatch_after_worker_green(
                session_factory=api.session_factory,
                task_id=task_id,
                active_flow_revision_id=active_flow_revision_id,
                child_dispatch_id=child_dispatch_id,
            )
    finally:
        await dispose_db_engine()


__all__ = [
    "test_cancel_fences_after_inactivity_is_proven",
    "test_cancel_marks_abort_requested_without_auto_fencing",
    "test_cancel_rebases_abort_deadline_from_new_request_time",
    "test_parent_redispatch_reuses_latest_fenced_child_even_if_already_linked",
    "test_worker_green_flips_currentness_to_parent_before_parent_redispatch",
]
