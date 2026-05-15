from __future__ import annotations

from pathlib import Path

import pytest
from app.db.session import dispose_db_engine
from app.runtime.effects import wait_for_runtime_effects
from app.runtime.openclaw.fixtures import agent_wait_fixture
from tests.integration.phase3.control.abort_support import (
    accept_green_boundary,
    assert_cancel_request_open,
    assert_cancelled_flow_fenced,
    assert_parent_redispatch_after_worker_green,
    assert_worker_green_kept_current,
    cancel_flow,
    open_child_flow_after_yield,
    record_green_checkpoint_for_child,
)
from tests.integration.phase3.dispatch_support import (
    current_open_dispatch_id,
    mark_dispatch_provider_completed,
    stage_child_yield,
)
from tests.integration.phase3.runtime_support import (
    bootstrap_parent_runtime,
    phase3_runtime_api,
    prepare_runtime_db,
)
from tests.integration.phase4a.support import LocalGatewayTestServer


@pytest.mark.asyncio
async def test_phase3_cancel_marks_abort_requested_without_auto_fencing(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
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
                agent_wait_fixture(status="ok"),
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
async def test_phase3_worker_green_keeps_worker_current_until_parent_redispatch(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
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
            await wait_for_runtime_effects(task_id=task_id)
            await accept_green_boundary(
                api.session_factory,
                task_id=task_id,
                child_attempt_id=child_attempt_id,
            )
            await assert_worker_green_kept_current(
                session_factory=api.session_factory,
                task_id=task_id,
                child_dispatch_id=child_dispatch_id,
                child_attempt_id=child_attempt_id,
                task_root=task_root,
            )
            openclaw_gateway_test_server.set_default_method_payload(
                "agent.wait",
                agent_wait_fixture(status="ok"),
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
    "test_phase3_worker_green_keeps_worker_current_until_parent_redispatch",
]
