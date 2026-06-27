from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway import OpenClawTransportError
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.integrations.openclaw.gateway.runtime_handle import (
    OpenClawGatewayRuntimeHandle,
    OpenClawRequestDispatchError,
)
from autoclaw.persistence import DispatchTurnModel
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.post_commit import drive_runtime_once, drive_runtime_until
from pydantic import ValidationError
from sqlalchemy import select
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import (
    bootstrap_parent_runtime,
    prepare_runtime_db,
    runtime_api_context,
    runtime_bootstrap_context,
    set_dispatch_drain_timeout,
    set_dispatch_launch_retry_policy,
)
from tests.helpers.runtime_support.dispatch import current_open_dispatch_id, stage_child_yield
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload


@pytest.mark.asyncio
async def test_pre_send_launch_failure_retries_after_backoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_gateway_pre_send_launch_retry"
    original_send_request = OpenClawGatewayRuntimeHandle.send_request_with_tracking
    failed_agent_sends = 0

    async def fail_first_agent_before_send(
        self: OpenClawGatewayRuntimeHandle,
        request: Any,
    ) -> object:
        nonlocal failed_agent_sends
        if request.method == "agent" and failed_agent_sends == 0:
            failed_agent_sends += 1
            raise OpenClawRequestDispatchError(
                error=OpenClawTransportError("synthetic pre-send launch failure"),
                request_sent=False,
            )
        return await original_send_request(self, request)

    monkeypatch.setattr(
        OpenClawGatewayRuntimeHandle,
        "send_request_with_tracking",
        fail_first_agent_before_send,
    )

    async with runtime_bootstrap_context(tmp_path) as runtime:
        set_dispatch_launch_retry_policy(
            runtime.paths.config_path,
            max_attempts=2,
            initial_backoff_seconds=30,
        )
        get_settings.cache_clear()
        async with runtime.session_factory() as session:
            with pytest.raises(
                OpenClawTransportError,
                match="synthetic pre-send launch failure",
            ):
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="gateway-pre-send-launch-retry",
                )
            await session.rollback()

        has_scheduled_retry = await drive_runtime_once(task_id=task_id)
        assert has_scheduled_retry is True
        assert _request_count(openclaw_gateway_test_server, "agent") == 0
        await _mark_latest_retry_due(runtime.session_factory, task_id=task_id)
        await drive_runtime_until(
            lambda: _latest_retry_dispatch_accepted(runtime.session_factory, task_id=task_id),
            task_id=task_id,
            max_cycles=20,
        )

        dispatches = await _dispatches_for_task(runtime.session_factory, task_id=task_id)

    failed_dispatches = [
        dispatch for dispatch in dispatches if dispatch.delivery_status == "transport_failed"
    ]
    accepted_retry = dispatches[-1]
    assert failed_agent_sends == 1
    assert len(failed_dispatches) == 1
    assert failed_dispatches[0].launch_retry_count == 1
    assert failed_dispatches[0].next_launch_retry_at is not None
    assert failed_dispatches[0].launch_failure_phase == "pre_send"
    assert failed_dispatches[0].launch_request_sent is False
    assert accepted_retry.dispatch_id != failed_dispatches[0].dispatch_id
    assert accepted_retry.previous_dispatch_id is None
    assert accepted_retry.launch_failure_phase is None
    assert accepted_retry.gateway_run_id is not None
    assert _request_count(openclaw_gateway_test_server, "agent") == 1
    assert _request_count(openclaw_gateway_test_server, "sessions.abort") == 0


@pytest.mark.asyncio
async def test_pre_send_retry_failure_does_not_shadow_previous_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    set_dispatch_launch_retry_policy(
        config_path,
        max_attempts=2,
        initial_backoff_seconds=0,
    )
    get_settings.cache_clear()
    task_root = tmp_path / "task-root"
    task_id = "task_gateway_boundary_launch_retry_shadow"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="gateway-boundary-launch-retry-shadow",
        )

        original_send_request = OpenClawGatewayRuntimeHandle.send_request_with_tracking
        failed_agent_sends = 0

        async def fail_first_child_agent_before_send(
            self: OpenClawGatewayRuntimeHandle,
            request: Any,
        ) -> object:
            nonlocal failed_agent_sends
            if request.method == "agent" and failed_agent_sends == 0:
                failed_agent_sends += 1
                raise OpenClawRequestDispatchError(
                    error=OpenClawTransportError("synthetic child pre-send failure"),
                    request_sent=False,
                )
            return await original_send_request(self, request)

        monkeypatch.setattr(
            OpenClawGatewayRuntimeHandle,
            "send_request_with_tracking",
            fail_first_child_agent_before_send,
        )

        async with runtime_api_context(config_path) as api:
            root_dispatch_id = await current_open_dispatch_id(
                api.session_factory,
                task_id=task_id,
            )
            openclaw_gateway_test_server.queue_method_payloads(
                "agent.wait",
                agent_wait_fixture(status="ok"),
            )
            await stage_child_yield(
                api,
                task_id=task_id,
                child_node_key="implementation_subtree",
            )
            await drive_runtime_until(
                lambda: _child_retry_dispatch_accepted(
                    api.session_factory,
                    task_id=task_id,
                    root_dispatch_id=root_dispatch_id,
                ),
                task_id=task_id,
                max_cycles=30,
            )
            dispatches = await _dispatches_for_task(api.session_factory, task_id=task_id)

        _assert_child_retry_reused_boundary(
            dispatches=dispatches,
            root_dispatch_id=root_dispatch_id,
            failed_agent_sends=failed_agent_sends,
        )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_post_send_no_run_id_ambiguity_does_not_blind_retry(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_gateway_post_send_no_run_id_no_retry"
    openclaw_gateway_test_server.set_default_method_payload(
        "agent",
        {
            "type": "res",
            "id": "agent-1",
            "ok": True,
            "payload": {
                "acceptedAt": "2026-05-13T00:00:00+00:00",
            },
        },
    )

    async with runtime_bootstrap_context(tmp_path) as runtime:
        set_dispatch_launch_retry_policy(
            runtime.paths.config_path,
            max_attempts=2,
            initial_backoff_seconds=0,
        )
        get_settings.cache_clear()
        async with runtime.session_factory() as session:
            with pytest.raises(ValidationError):
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="gateway-post-send-no-run-id-no-retry",
                )
            await session.rollback()

        agent_requests_before = _request_count(openclaw_gateway_test_server, "agent")
        await drive_runtime_once(task_id=task_id)
        dispatches = await _dispatches_for_task(runtime.session_factory, task_id=task_id)

    ambiguous_dispatch = dispatches[-1]
    assert agent_requests_before == 1
    assert _request_count(openclaw_gateway_test_server, "agent") == 1
    assert _request_count(openclaw_gateway_test_server, "sessions.abort") == 1
    assert ambiguous_dispatch.control_state == "ambiguous"
    assert ambiguous_dispatch.delivery_status == "transport_ambiguous"
    assert ambiguous_dispatch.gateway_run_id is None
    assert ambiguous_dispatch.launch_failure_phase == "post_send"
    assert ambiguous_dispatch.launch_request_sent is True
    assert ambiguous_dispatch.next_launch_retry_at is None


async def _latest_retry_dispatch_accepted(
    session_factory: Any,
    *,
    task_id: str,
) -> bool:
    dispatches = await _dispatches_for_task(session_factory, task_id=task_id)
    latest_dispatch = dispatches[-1] if dispatches else None
    return latest_dispatch is not None and latest_dispatch.gateway_run_id is not None


async def _mark_latest_retry_due(
    session_factory: Any,
    *,
    task_id: str,
) -> None:
    async with session_factory() as session:
        dispatch = await session.scalar(
            select(DispatchTurnModel)
            .where(
                DispatchTurnModel.task_id == task_id,
                DispatchTurnModel.launch_failure_phase == "pre_send",
            )
            .order_by(DispatchTurnModel.rendered_at.desc())
        )
        assert dispatch is not None
        dispatch.next_launch_retry_at = utc_now()
        await session.commit()


async def _child_retry_dispatch_accepted(
    session_factory: Any,
    *,
    task_id: str,
    root_dispatch_id: str,
) -> bool:
    dispatches = await _dispatches_for_task(session_factory, task_id=task_id)
    child_dispatches = [
        dispatch for dispatch in dispatches if dispatch.node_key == "implementation_subtree"
    ]
    return any(
        dispatch.gateway_run_id is not None and dispatch.previous_dispatch_id == root_dispatch_id
        for dispatch in child_dispatches
    )


async def _dispatches_for_task(
    session_factory: Any,
    *,
    task_id: str,
) -> list[DispatchTurnModel]:
    async with session_factory() as session:
        rows = await session.scalars(
            select(DispatchTurnModel)
            .where(DispatchTurnModel.task_id == task_id)
            .order_by(DispatchTurnModel.rendered_at)
        )
        dispatches = list(rows)
        for dispatch in dispatches:
            session.expunge(dispatch)
        return dispatches


def _dispatch_by_id(
    dispatches: list[DispatchTurnModel],
    dispatch_id: str,
) -> DispatchTurnModel:
    for dispatch in dispatches:
        if dispatch.dispatch_id == dispatch_id:
            return dispatch
    raise AssertionError(f"missing dispatch '{dispatch_id}'")


def _assert_child_retry_reused_boundary(
    *,
    dispatches: list[DispatchTurnModel],
    root_dispatch_id: str,
    failed_agent_sends: int,
) -> None:
    root_dispatch = _dispatch_by_id(dispatches, root_dispatch_id)
    failed_child_dispatches = [
        dispatch
        for dispatch in dispatches
        if dispatch.node_key == "implementation_subtree"
        and dispatch.delivery_status == "transport_failed"
    ]
    accepted_child_dispatches = [
        dispatch
        for dispatch in dispatches
        if dispatch.node_key == "implementation_subtree" and dispatch.gateway_run_id is not None
    ]
    assert failed_agent_sends == 1
    assert len(failed_child_dispatches) == 1
    assert len(accepted_child_dispatches) == 1
    failed_child = failed_child_dispatches[0]
    accepted_child = accepted_child_dispatches[0]
    assert failed_child.previous_dispatch_id == root_dispatch_id
    assert failed_child.launch_retry_count == 1
    assert accepted_child.previous_dispatch_id == root_dispatch_id
    assert accepted_child.dispatch_id != failed_child.dispatch_id
    assert root_dispatch.superseded_by_dispatch_id == accepted_child.dispatch_id


def _request_count(
    openclaw_gateway_test_server: LocalGatewayTestServer,
    method: str,
) -> int:
    return sum(1 for request in openclaw_gateway_test_server.requests if request.method == method)
