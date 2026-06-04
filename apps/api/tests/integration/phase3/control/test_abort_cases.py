from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from autoclaw.db import DispatchTurnModel
from autoclaw.db.session import dispose_db_engine
from autoclaw.runtime.effects import wait_for_runtime_effects
from autoclaw.runtime.openclaw.fixtures import agent_wait_fixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_test_config import set_dispatch_drain_timeout
from tests.integration.phase3.control.abort_support import (
    accept_green_boundary,
    assert_cancel_request_open,
    assert_cancelled_flow_fenced,
    assert_parent_redispatch_after_worker_green,
    assert_worker_green_flips_currentness_to_parent_while_worker_dispatch_stays_live,
    cancel_flow,
)
from tests.integration.phase3.dispatch_support import current_open_dispatch_id
from tests.integration.phase3.runtime_harness.child_dispatch import (
    retry_terminal_green_checkpoint,
    stage_child_dispatch,
)
from tests.integration.phase3.runtime_support import (
    bootstrap_parent_runtime,
    phase3_runtime_api,
    prepare_runtime_db,
    runtime_read_json,
)
from tests.integration.phase4a.support import LocalGatewayTestServer


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
async def test_phase3_cancel_marks_abort_requested_without_auto_fencing(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_cancel"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-cancel",
        )

        async with phase3_runtime_api(config_path) as api:
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
async def test_phase3_cancel_fences_after_inactivity_is_proven(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_control_cancel_proven"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-cancel-proven",
        )

        async with phase3_runtime_api(config_path) as api:
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
async def test_phase3_worker_green_flips_currentness_to_parent_before_parent_redispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_worker_parent_currentness"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-worker-parent-currentness",
            workflow_key="minimal-implement-change",
        )

        async with phase3_runtime_api(config_path) as api:
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


__all__ = [
    "test_phase3_cancel_fences_after_inactivity_is_proven",
    "test_phase3_cancel_marks_abort_requested_without_auto_fencing",
    "test_phase3_worker_green_flips_currentness_to_parent_before_parent_redispatch",
]
