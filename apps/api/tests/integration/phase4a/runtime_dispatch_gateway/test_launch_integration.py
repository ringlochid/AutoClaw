from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from app import cli
from app.config import get_settings
from app.db.session import dispose_db_engine, get_session_factory
from app.runtime.openclaw import OpenClawCompatibilityError, OpenClawTransportError
from app.runtime.openclaw.contracts import OpenClawAgentLaunchInput
from app.runtime.openclaw.fixtures import (
    connect_challenge_fixture,
    hello_ok_fixture,
)
from app.runtime.openclaw.request_builders import build_openclaw_agent_request
from app.runtime.openclaw.runtime_handle import OpenClawRequestDispatchError
from pydantic import ValidationError
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase2.bootstrap.support import phase2_runtime_context
from tests.integration.phase4a.dispatch_gateway_support import (
    load_latest_dispatch_snapshot,
    override_gateway_base_url,
)
from tests.integration.phase4a.runtime_dispatch_gateway.support import (
    assert_gateway_launch_snapshot,
)
from tests.integration.phase4a.support import (
    LocalGatewayTestServer,
    gateway_server,
    recv_json,
    send_json,
)
from websockets.asyncio.server import ServerConnection
from websockets.exceptions import ConnectionClosed


@pytest.mark.asyncio
async def test_launch_runtime_persists_gateway_session_run_and_node_session_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4a_launch_gateway_success"
    recorded_launch_requests: list[tuple[str, OpenClawAgentLaunchInput]] = []
    original_builder = build_openclaw_agent_request

    def record_gateway_agent_request(
        *,
        request_id: str,
        launch_input: OpenClawAgentLaunchInput,
    ) -> object:
        recorded_launch_requests.append((request_id, launch_input))
        return original_builder(
            request_id=request_id,
            launch_input=launch_input,
        )

    monkeypatch.setattr(
        "app.runtime.control.dispatch.gateway.launch.build_openclaw_agent_request",
        record_gateway_agent_request,
    )

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("minimal-implement-change"),
                compiler_version="phase-4a-launch-success",
            )

        async with runtime.session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

    assert_gateway_launch_snapshot(
        snapshot,
        recorded_launch_requests=recorded_launch_requests,
        original_builder=original_builder,
        observed_requests=openclaw_gateway_test_server.requests,
    )


@pytest.mark.asyncio
async def test_launch_runtime_persists_transport_failure_without_fake_acceptance(
    tmp_path: Path,
) -> None:
    task_id = "task_phase4a_launch_gateway_failure"
    config_path: Path | None = None
    snapshot = None
    async with phase2_runtime_context(tmp_path) as runtime:
        config_path = runtime.paths.config_path
        with override_gateway_base_url("http://127.0.0.1:1"):
            async with runtime.session_factory() as session:
                with pytest.raises(OpenClawTransportError):
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-4a-launch-failure",
                    )
                await session.rollback()
                await session.close()
    assert config_path is not None
    try:
        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
    finally:
        await dispose_db_engine()
    assert snapshot is not None
    assert snapshot.flow.current_open_dispatch_id is None
    assert snapshot.delivery_state is not None
    assert snapshot.continuity_state is not None
    assert snapshot.dispatch.delivery_status == "transport_failed"
    assert snapshot.dispatch.control_state == "fenced"
    assert snapshot.dispatch.gateway_session_key is None
    assert snapshot.dispatch.gateway_run_id is None
    assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
    assert snapshot.delivery_state.transport_state == "transport_failed"
    assert snapshot.delivery_state.provider_error is not None
    assert snapshot.continuity_state.session_key_present is False
    assert snapshot.continuity_state.invalidation_reason == (
        "gateway_launch_failed:OpenClawTransportError"
    )
    assert snapshot.node_session is None
    assert len(snapshot.provider_events) == 1
    assert snapshot.provider_events[0].event_kind == "transport_failed"


@pytest.mark.asyncio
async def test_launch_runtime_pre_send_payload_policy_failure_stays_transport_failed(
    tmp_path: Path,
) -> None:
    task_id = "task_phase4a_launch_gateway_pre_send_policy_failure"
    config_path: Path | None = None
    snapshot = None
    observed_methods: list[str] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(max_payload=128, device_token="device-token-test")
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        try:
            request = await asyncio.wait_for(recv_json(connection), timeout=0.5)
        except (TimeoutError, ConnectionClosed):
            return
        observed_methods.append(str(request["method"]))
        if request["method"] == "sessions.abort":
            response = {"type": "res", "ok": True, "payload": {"accepted": True}}
            response["id"] = request["id"]
            await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        async with phase2_runtime_context(tmp_path) as runtime:
            config_path = runtime.paths.config_path
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    with pytest.raises(OpenClawCompatibilityError, match="maxPayload=128"):
                        await launch_seeded_runtime(
                            session,
                            task_id=task_id,
                            task_root=runtime.paths.task_root,
                            task_compose=task_compose_payload("minimal-implement-change"),
                            compiler_version="phase-4a-pre-send-policy-failure",
                        )
                    await session.rollback()
                    await session.close()
        assert config_path is not None
        try:
            with cli.command_env(config_path=config_path):
                get_settings.cache_clear()
                session_factory = get_session_factory()
                async with session_factory() as session:
                    snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
        finally:
            await dispose_db_engine()
    assert snapshot is not None
    assert snapshot.flow.current_open_dispatch_id is None
    assert snapshot.delivery_state is not None
    assert snapshot.continuity_state is not None
    assert snapshot.dispatch.delivery_status == "transport_failed"
    assert snapshot.dispatch.control_state == "fenced"
    assert snapshot.dispatch.gateway_session_key is None
    assert snapshot.dispatch.gateway_run_id is None
    assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
    assert snapshot.delivery_state.transport_state == "transport_failed"
    assert snapshot.delivery_state.provider_error is not None
    assert snapshot.continuity_state.session_key_present is False
    assert snapshot.continuity_state.invalidation_reason == (
        "gateway_launch_failed:OpenClawCompatibilityError"
    )
    assert snapshot.node_session is None
    assert [event.event_kind for event in snapshot.provider_events] == ["transport_failed"]
    assert observed_methods == []


@pytest.mark.asyncio
async def test_launch_runtime_pre_send_transport_failure_stays_transport_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4a_launch_gateway_send_failure"

    async def fail_before_send(*_args: object, **_kwargs: object) -> object:
        raise OpenClawRequestDispatchError(
            error=OpenClawTransportError("synthetic pre-send failure"),
            request_sent=False,
        )

    monkeypatch.setattr(
        "app.runtime.openclaw.runtime_handle.OpenClawGatewayRuntimeHandle.send_request_with_tracking",
        fail_before_send,
    )

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            with pytest.raises(OpenClawTransportError, match="synthetic pre-send failure"):
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-4a-send-failure",
                )
            await session.rollback()

        async with runtime.session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

    assert snapshot.flow.current_open_dispatch_id is None
    assert snapshot.dispatch.delivery_status == "transport_failed"
    assert snapshot.dispatch.control_state == "fenced"
    assert snapshot.dispatch.gateway_session_key is None
    assert snapshot.dispatch.gateway_run_id is None
    assert snapshot.delivery_state is not None
    assert snapshot.delivery_state.transport_state == "transport_failed"
    assert snapshot.continuity_state is not None
    assert snapshot.continuity_state.session_key_present is False
    assert [event.event_kind for event in snapshot.provider_events] == ["transport_failed"]
    assert not any(
        request.method == "sessions.abort" for request in openclaw_gateway_test_server.requests
    )


@pytest.mark.asyncio
async def test_launch_runtime_post_send_normalization_failure_marks_dispatch_ambiguous(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4a_launch_gateway_post_send_failure"
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

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            with pytest.raises(ValidationError):
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-4a-post-send-failure",
                )
            await session.rollback()

        async with runtime.session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

    assert snapshot.delivery_state is not None
    assert snapshot.continuity_state is not None
    assert snapshot.dispatch.delivery_status == "transport_ambiguous"
    assert snapshot.dispatch.control_state == "ambiguous"
    assert snapshot.dispatch.gateway_session_key is not None
    assert snapshot.dispatch.gateway_run_id is None
    assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
    assert snapshot.delivery_state.transport_state == "transport_ambiguous"
    assert snapshot.delivery_state.provider_error is not None
    assert snapshot.continuity_state.session_key_present is True
    assert snapshot.continuity_state.invalidation_reason == (
        "gateway_launch_post_send_failed:ValidationError"
    )
    assert [event.event_kind for event in snapshot.provider_events] == [
        "transport_failed",
        "tool_event",
    ]
    assert any(
        request.method == "sessions.abort" for request in openclaw_gateway_test_server.requests
    )
    assert openclaw_gateway_test_server.connection_count == 1


@pytest.mark.asyncio
async def test_launch_runtime_post_send_transport_failure_falls_back_to_fresh_cleanup_connection(
    tmp_path: Path,
) -> None:
    task_id = "task_phase4a_launch_gateway_post_send_transport_failure"
    seen_requests: list[tuple[int, str]] = []
    connection_count = 0

    async def handler(connection: ServerConnection) -> None:
        nonlocal connection_count
        connection_count += 1
        current_connection = connection_count
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(device_token="device-token-test")
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        seen_requests.append((current_connection, str(request["method"])))
        if current_connection == 1:
            assert request["method"] == "agent"
            await connection.close()
            return
        assert request["method"] == "sessions.abort"
        response = {"type": "res", "ok": True, "payload": {"status": "accepted"}}
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        async with phase2_runtime_context(tmp_path) as runtime:
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    with pytest.raises(OpenClawTransportError):
                        await launch_seeded_runtime(
                            session,
                            task_id=task_id,
                            task_root=runtime.paths.task_root,
                            task_compose=task_compose_payload("minimal-implement-change"),
                            compiler_version="phase-4a-post-send-transport-failure",
                        )
                    await session.rollback()

            async with runtime.session_factory() as session:
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

    assert snapshot.delivery_state is not None
    assert snapshot.continuity_state is not None
    assert snapshot.dispatch.delivery_status == "transport_ambiguous"
    assert snapshot.dispatch.control_state == "ambiguous"
    assert snapshot.dispatch.gateway_session_key is not None
    assert snapshot.dispatch.gateway_run_id is None
    assert snapshot.delivery_state.transport_state == "transport_ambiguous"
    assert snapshot.continuity_state.session_key_present is True
    assert [event.event_kind for event in snapshot.provider_events] == [
        "transport_failed",
        "tool_event",
    ]
    assert seen_requests == [
        (1, "agent"),
        (2, "sessions.abort"),
    ]
    assert connection_count == 2


@pytest.mark.asyncio
async def test_launch_runtime_post_send_failure_still_closes_lease_when_failure_recording_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_phase4a_launch_gateway_record_failure_cleanup"
    lease_closed = False

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(device_token="device-token-test")
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        assert request["method"] == "agent"
        await connection.close()

    async def fail_recording(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("failure recording blew up")

    original_close_dispatch_launch_lease = (
        __import__(
            "app.runtime.control.dispatch.opening",
            fromlist=["close_dispatch_launch_lease"],
        ).close_dispatch_launch_lease
    )

    async def record_close(lease: object) -> None:
        nonlocal lease_closed
        lease_closed = True
        await original_close_dispatch_launch_lease(lease)

    monkeypatch.setattr(
        "app.runtime.control.dispatch.opening._record_gateway_launch_failure_and_commit",
        fail_recording,
    )
    monkeypatch.setattr(
        "app.runtime.control.dispatch.opening.close_dispatch_launch_lease",
        record_close,
    )

    async with gateway_server(handler) as base_url:
        async with phase2_runtime_context(tmp_path) as runtime:
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    with pytest.raises(RuntimeError, match="failure recording blew up"):
                        await launch_seeded_runtime(
                            session,
                            task_id=task_id,
                            task_root=runtime.paths.task_root,
                            task_compose=task_compose_payload("minimal-implement-change"),
                            compiler_version="phase-4a-record-failure-cleanup",
                        )
                    await session.rollback()

    assert lease_closed is True
