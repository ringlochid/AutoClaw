from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway import (
    OpenClawCompatibilityError,
    OpenClawTransportError,
)
from autoclaw.integrations.openclaw.gateway.contracts import OpenClawAgentLaunchInput
from autoclaw.integrations.openclaw.gateway.fixtures import (
    agent_accepted_fixture,
    connect_challenge_fixture,
    hello_ok_fixture,
)
from autoclaw.integrations.openclaw.gateway.request_builders import build_openclaw_agent_request
from autoclaw.integrations.openclaw.gateway.runtime_handle import OpenClawRequestDispatchError
from autoclaw.runtime.post_commit import stop_runtime_effect_runner
from pydantic import ValidationError
from tests.helpers.openclaw_gateway_support import (
    LocalGatewayTestServer,
    gateway_server,
    recv_json,
    send_json,
)
from tests.helpers.runtime_support import (
    runtime_bootstrap_context,
    set_dispatch_launch_retry_policy,
)
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload
from tests.integration.gateway.dispatch_gateway_support import (
    load_latest_dispatch_snapshot,
    override_gateway_base_url,
)
from tests.integration.gateway.runtime_dispatch_gateway.launch.failure_assertions import (
    assert_transport_ambiguous_launch_snapshot,
    assert_transport_failed_launch_snapshot,
    load_dispatch_snapshot_from_config,
)
from tests.integration.gateway.runtime_dispatch_gateway.support import (
    assert_gateway_launch_snapshot,
)
from websockets.asyncio.server import ServerConnection
from websockets.exceptions import ConnectionClosed


@pytest.mark.asyncio
async def test_launch_runtime_persists_gateway_session_run_and_node_session_truth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_gateway_launch_success"
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
        "autoclaw.integrations.openclaw.gateway.runtime_handle.build_openclaw_agent_request",
        record_gateway_agent_request,
    )

    async with runtime_bootstrap_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("bounded-change"),
                compiler_version="gateway-launch-success",
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
async def test_launch_runtime_ignores_additive_session_key_in_accepted_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_gateway_launch_accepts_additive_session_key"
    recorded_launch_requests: list[tuple[str, OpenClawAgentLaunchInput]] = []
    original_builder = build_openclaw_agent_request
    accepted = agent_accepted_fixture(session_key="agent:autoclaw-worker:echoed-session-key")
    accepted["payload"]["runId"] = "run-1"

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
        "autoclaw.integrations.openclaw.gateway.runtime_handle.build_openclaw_agent_request",
        record_gateway_agent_request,
    )
    openclaw_gateway_test_server.set_default_method_payload("agent", accepted)

    async with runtime_bootstrap_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("bounded-change"),
                compiler_version="gateway-launch-additive-session-key",
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
    task_id = "task_gateway_launch_failure"
    config_path: Path | None = None
    async with runtime_bootstrap_context(tmp_path) as runtime:
        config_path = runtime.paths.config_path
        set_dispatch_launch_retry_policy(
            config_path,
            max_attempts=1,
            initial_backoff_seconds=0,
        )
        get_settings.cache_clear()
        with override_gateway_base_url("http://127.0.0.1:1"):
            async with runtime.session_factory() as session:
                with pytest.raises(OpenClawTransportError):
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("bounded-change"),
                        compiler_version="gateway-launch-failure",
                    )
                await session.rollback()
                await session.close()
                await stop_runtime_effect_runner()
    assert config_path is not None
    snapshot = await load_dispatch_snapshot_from_config(config_path=config_path, task_id=task_id)
    assert_transport_failed_launch_snapshot(
        snapshot,
        invalidation_reason="gateway_launch_failed:OpenClawTransportError",
        expected_event_kinds=["transport_failed"],
        expect_node_session_none=True,
        expect_provider_error=True,
        expect_transport_family=True,
    )


@pytest.mark.asyncio
async def test_launch_runtime_pre_send_payload_policy_failure_stays_transport_failed(
    tmp_path: Path,
) -> None:
    task_id = "task_gateway_launch_pre_send_policy_failure"
    config_path: Path | None = None
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
        async with runtime_bootstrap_context(tmp_path) as runtime:
            config_path = runtime.paths.config_path
            set_dispatch_launch_retry_policy(
                config_path,
                max_attempts=1,
                initial_backoff_seconds=0,
            )
            get_settings.cache_clear()
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    with pytest.raises(OpenClawCompatibilityError, match="maxPayload=128"):
                        await launch_seeded_runtime(
                            session,
                            task_id=task_id,
                            task_root=runtime.paths.task_root,
                            task_compose=task_compose_payload("bounded-change"),
                            compiler_version="gateway-pre-send-policy-failure",
                        )
                    await session.rollback()
                    await session.close()
                    await stop_runtime_effect_runner()
        assert config_path is not None
        snapshot = await load_dispatch_snapshot_from_config(
            config_path=config_path,
            task_id=task_id,
        )
    assert_transport_failed_launch_snapshot(
        snapshot,
        invalidation_reason="gateway_launch_failed:OpenClawCompatibilityError",
        expected_event_kinds=["transport_failed"],
        expect_node_session_none=True,
        expect_provider_error=True,
        expect_transport_family=True,
    )
    assert observed_methods == []


@pytest.mark.asyncio
async def test_launch_runtime_pre_send_transport_failure_stays_transport_failed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_gateway_launch_send_failure"

    async def fail_before_send(*_args: object, **_kwargs: object) -> object:
        raise OpenClawRequestDispatchError(
            error=OpenClawTransportError("synthetic pre-send failure"),
            request_sent=False,
        )

    monkeypatch.setattr(
        "autoclaw.integrations.openclaw.gateway.runtime_handle.OpenClawGatewayRuntimeHandle.send_request_with_tracking",
        fail_before_send,
    )

    async with runtime_bootstrap_context(tmp_path) as runtime:
        set_dispatch_launch_retry_policy(
            runtime.paths.config_path,
            max_attempts=1,
            initial_backoff_seconds=0,
        )
        get_settings.cache_clear()
        async with runtime.session_factory() as session:
            with pytest.raises(OpenClawTransportError, match="synthetic pre-send failure"):
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("bounded-change"),
                    compiler_version="gateway-send-failure",
                )
            await session.rollback()
            await stop_runtime_effect_runner()

        async with runtime.session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

    assert_transport_failed_launch_snapshot(
        snapshot,
        expected_event_kinds=["transport_failed"],
    )
    assert not any(
        request.method == "sessions.abort" for request in openclaw_gateway_test_server.requests
    )


@pytest.mark.asyncio
async def test_launch_runtime_post_send_normalization_failure_marks_dispatch_ambiguous(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_gateway_launch_post_send_failure"
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
        async with runtime.session_factory() as session:
            with pytest.raises(ValidationError):
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("bounded-change"),
                    compiler_version="gateway-post-send-failure",
                )
            await session.rollback()

        async with runtime.session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

    assert_transport_ambiguous_launch_snapshot(
        snapshot,
        invalidation_reason="gateway_launch_post_send_failed:ValidationError",
        expect_provider_error=True,
        expect_transport_family=True,
    )
    assert any(
        request.method == "sessions.abort" for request in openclaw_gateway_test_server.requests
    )
    assert openclaw_gateway_test_server.connection_count == 1


@pytest.mark.asyncio
async def test_launch_runtime_post_send_transport_failure_falls_back_to_fresh_cleanup_connection(
    tmp_path: Path,
) -> None:
    task_id = "task_gateway_launch_post_send_transport_failure"
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
        async with runtime_bootstrap_context(tmp_path) as runtime:
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    with pytest.raises(OpenClawTransportError):
                        await launch_seeded_runtime(
                            session,
                            task_id=task_id,
                            task_root=runtime.paths.task_root,
                            task_compose=task_compose_payload("bounded-change"),
                            compiler_version="gateway-post-send-transport-failure",
                        )
                    await session.rollback()

            async with runtime.session_factory() as session:
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

    assert_transport_ambiguous_launch_snapshot(snapshot)
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
    task_id = "task_gateway_launch_record_failure_cleanup"
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

    original_close_dispatch_launch_lease = __import__(
        "autoclaw.runtime.dispatch.opening",
        fromlist=["close_dispatch_launch_lease"],
    ).close_dispatch_launch_lease

    async def record_close(lease: object) -> None:
        nonlocal lease_closed
        lease_closed = True
        await original_close_dispatch_launch_lease(lease)

    monkeypatch.setattr(
        "autoclaw.runtime.dispatch.opening._record_gateway_launch_failure_and_commit",
        fail_recording,
    )
    monkeypatch.setattr(
        "autoclaw.runtime.dispatch.opening.close_dispatch_launch_lease",
        record_close,
    )

    async with gateway_server(handler) as base_url:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    with pytest.raises(RuntimeError, match="failure recording blew up"):
                        await launch_seeded_runtime(
                            session,
                            task_id=task_id,
                            task_root=runtime.paths.task_root,
                            task_compose=task_compose_payload("bounded-change"),
                            compiler_version="gateway-record-failure-cleanup",
                        )
                    await session.rollback()

    assert lease_closed is True
