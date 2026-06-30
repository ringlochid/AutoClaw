from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from autoclaw.integrations.openclaw.gateway import (
    OPENCLAW_PROTOCOL_VERSION,
    OpenClawAbortRequest,
    OpenClawAgentLaunchInput,
    OpenClawConfigurationError,
    OpenClawWaitRequest,
    OpenClawWaitStatus,
)
from autoclaw.integrations.openclaw.gateway.auth_state import load_gateway_auth_state
from autoclaw.integrations.openclaw.gateway.contracts import OpenClawProtocolError
from autoclaw.integrations.openclaw.gateway.fixtures import (
    agent_accepted_fixture,
    agent_wait_fixture,
    connect_challenge_fixture,
    hello_ok_fixture,
    sessions_abort_fixture,
)
from autoclaw.integrations.openclaw.gateway.session_keys import normalize_agent_launch_input
from tests.helpers.openclaw_gateway_support import (
    build_test_adapter,
    build_test_launch_request,
    gateway_server,
    hello_ok_without,
    recv_json,
    send_json,
)
from websockets.asyncio.server import ServerConnection


@pytest.mark.asyncio
async def test_check_compatibility_persists_device_token(tmp_path: Path) -> None:
    received_connect: dict[str, Any] = {}

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        received_connect.update(connect_request)
        assert connect_request["method"] == "connect"
        assert connect_request["params"]["auth"]["token"] == "gateway-config-token"
        assert connect_request["params"]["minProtocol"] == OPENCLAW_PROTOCOL_VERSION
        assert connect_request["params"]["maxProtocol"] == OPENCLAW_PROTOCOL_VERSION
        response = hello_ok_fixture(
            device_token="device-token-abc",
            plugin_surface_urls={
                "canvas": "https://plugins.example.test/canvas",
            },
        )
        response["id"] = connect_request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data")
        compatibility = await adapter.check_compatibility()

    assert compatibility.protocol_version == OPENCLAW_PROTOCOL_VERSION == 4
    assert compatibility.issued_device_token == "device-token-abc"
    assert compatibility.available_methods == ("agent", "agent.wait", "sessions.abort")
    assert compatibility.tick_interval_ms == 15000
    assert received_connect["params"]["client"]["id"] == "openclaw-control-ui"
    assert received_connect["params"]["client"]["mode"] == "webchat"
    assert received_connect["params"]["auth"]["token"] == "gateway-config-token"
    assert "device" not in received_connect["params"]
    auth_state = load_gateway_auth_state(
        tmp_path / "data" / "openclaw" / "gateway-device-auth.json"
    )
    assert auth_state is not None
    assert auth_state.primary_token is not None
    assert auth_state.primary_token.device_token == "device-token-abc"


@pytest.mark.asyncio
async def test_check_compatibility_allows_omitted_method_advertisement(
    tmp_path: Path,
) -> None:
    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        response = hello_ok_without("payload", "features", "methods")
        response["id"] = connect_request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data")
        compatibility = await adapter.check_compatibility()

    assert compatibility.available_methods == ()
    assert compatibility.available_events == (
        "agent",
        "sessions.changed",
    )


@pytest.mark.asyncio
async def test_launch_wait_and_abort_round_trip(tmp_path: Path) -> None:
    seen_methods: list[str] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        response_id = connect_request["id"]
        hello_ok = hello_ok_fixture(device_token=None)
        hello_ok["id"] = response_id
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        seen_methods.append(str(request["method"]))
        if request["method"] == "agent":
            assert request["params"]["sessionKey"] == "agent:worker-agent:session-123"
            assert request["params"]["channel"] == "webchat"
            assert request["params"]["idempotencyKey"] == "dispatch:dispatch-123"
            assert request["params"]["message"] == "body"
            assert request["params"]["extraSystemPrompt"] == "system"
            assert "instructions" not in request["params"]
            assert "input" not in request["params"]
            assert "meta" not in request["params"]
            assert "previousResponseId" not in request["params"]
            response = agent_accepted_fixture()
            response["id"] = request["id"]
            await send_json(connection, response)
            return
        if request["method"] == "agent.wait":
            response = agent_wait_fixture(status="timeout")
            response["id"] = request["id"]
            await send_json(connection, response)
            return
        if request["method"] == "sessions.abort":
            response = sessions_abort_fixture()
            response["id"] = request["id"]
            await send_json(connection, response)
            return
        raise AssertionError(f"unexpected method {request['method']}")

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data")
        launch_result = await adapter.launch_run(build_test_launch_request())
        wait_result = await adapter.wait_for_run(OpenClawWaitRequest(run_id=launch_result.run_id))
        abort_result = await adapter.abort_run(
            OpenClawAbortRequest(
                session_key="agent:worker-agent:session-123",
                run_id=launch_result.run_id,
            )
        )

    assert launch_result.session_key == "agent:worker-agent:session-123"
    assert launch_result.run_id == "run-123"
    assert wait_result.status == OpenClawWaitStatus.TIMEOUT
    assert abort_result.accepted is True
    assert abort_result.run_id == "run-123"
    assert seen_methods == ["agent", "agent.wait", "sessions.abort"]


@pytest.mark.asyncio
async def test_launch_falls_back_when_gateway_rejects_extra_system_prompt(
    tmp_path: Path,
) -> None:
    seen_agent_params: list[dict[str, Any]] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(device_token=None)
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)

        first_request = await recv_json(connection)
        assert first_request["method"] == "agent"
        seen_agent_params.append(dict(first_request["params"]))
        await send_json(
            connection,
            {
                "type": "res",
                "id": first_request["id"],
                "ok": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "params.extraSystemPrompt: additional property not allowed",
                },
            },
        )

        fallback_request = await recv_json(connection)
        assert fallback_request["method"] == "agent"
        seen_agent_params.append(dict(fallback_request["params"]))
        response = agent_accepted_fixture()
        response["id"] = fallback_request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data")
        launch_result = await adapter.launch_run(build_test_launch_request())

    assert launch_result.run_id == "run-123"
    assert seen_agent_params == [
        {
            "sessionKey": "agent:worker-agent:session-123",
            "message": "body",
            "channel": "webchat",
            "extraSystemPrompt": "system",
            "idempotencyKey": "dispatch:dispatch-123",
        },
        {
            "sessionKey": "agent:worker-agent:session-123",
            "message": "# AutoClaw Dispatch Prompt\n\nsystem\n\nbody",
            "channel": "webchat",
            "idempotencyKey": "dispatch:dispatch-123",
        },
    ]


@pytest.mark.asyncio
async def test_dispatch_handle_routes_interleaved_events_and_ignores_late_agent_followup(
    tmp_path: Path,
) -> None:
    seen_methods: list[str] = []

    async with gateway_server(
        lambda connection: _handle_scoped_interleaved_events(connection, seen_methods)
    ) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
            agent_id=None,
        )
        async with adapter.dispatch_handle() as handle:
            launch_result = await handle.launch_run(
                normalize_agent_launch_input(build_test_launch_request(), None)
            )
            observed_event = await handle.next_event(timeout_seconds=0.5)
            wait_result = await handle.wait_for_run(
                OpenClawWaitRequest(run_id=launch_result.run_id)
            )

    assert launch_result.run_id == "run-live"
    assert observed_event is not None
    assert observed_event.event == "agent"
    assert observed_event.seq == 3
    assert observed_event.payload["runId"] == "run-live"
    assert wait_result.status == OpenClawWaitStatus.OK
    assert seen_methods == ["agent", "agent.wait"]


async def _handle_scoped_interleaved_events(
    connection: ServerConnection,
    seen_methods: list[str],
) -> None:
    await send_json(connection, connect_challenge_fixture())
    connect_request = await recv_json(connection)
    hello_ok = hello_ok_fixture(device_token=None)
    hello_ok["id"] = connect_request["id"]
    await send_json(connection, hello_ok)
    launch_request = await recv_json(connection)
    seen_methods.append(str(launch_request["method"]))
    assert launch_request["method"] == "agent"
    await _send_interleaved_launch_events(connection, launch_request)
    wait_request = await recv_json(connection)
    seen_methods.append(str(wait_request["method"]))
    assert wait_request["method"] == "agent.wait"
    wait_response = agent_wait_fixture(run_id="run-live", status="ok")
    wait_response["id"] = wait_request["id"]
    await send_json(connection, wait_response)


async def _send_interleaved_launch_events(
    connection: ServerConnection,
    launch_request: dict[str, Any],
) -> None:
    session_key = str(launch_request["params"]["sessionKey"])
    await send_json(
        connection,
        {
            "type": "event",
            "event": "presence",
            "payload": {"presence": []},
            "seq": 1,
            "stateVersion": {"presence": 1},
        },
    )
    accepted = agent_accepted_fixture()
    accepted["id"] = launch_request["id"]
    accepted["payload"]["runId"] = "run-live"
    await send_json(connection, accepted)
    await send_json(connection, _agent_event("run-orin", "agent:orin:direct", "wrong", 2))
    await send_json(connection, _agent_event("run-live", session_key, "right", 3))
    await send_json(
        connection,
        {
            "type": "res",
            "id": launch_request["id"],
            "ok": True,
            "payload": {"runId": "run-live", "status": "completed"},
        },
    )


def _agent_event(run_id: str, session_key: str, delta: str, seq: int) -> dict[str, Any]:
    return {
        "type": "event",
        "event": "agent",
        "payload": {
            "runId": run_id,
            "sessionKey": session_key,
            "stream": "assistant",
            "data": {"delta": delta},
        },
        "seq": seq,
    }


@pytest.mark.asyncio
async def test_launch_accepts_case_insensitive_already_scoped_session_key_without_double_prefix(
    tmp_path: Path,
) -> None:
    seen_session_keys: list[str] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(device_token=None)
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        assert request["method"] == "agent"
        seen_session_keys.append(str(request["params"]["sessionKey"]))
        response = agent_accepted_fixture()
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data")
        launch_result = await adapter.launch_run(
            OpenClawAgentLaunchInput(
                session_key="AGENT:Main:main",
                message="body",
                extra_system_prompt="system",
                idempotency_key="dispatch:dispatch-123",
            )
        )

    assert seen_session_keys == ["agent:main:main"]
    assert launch_result.session_key == "agent:main:main"


@pytest.mark.asyncio
async def test_launch_rejects_malformed_already_scoped_session_key(tmp_path: Path) -> None:
    seen_methods: list[str] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(device_token=None)
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        try:
            request = await recv_json(connection)
        except Exception:
            return
        seen_methods.append(str(request["method"]))

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data")
        with pytest.raises(OpenClawConfigurationError, match="Malformed agent-scoped"):
            await adapter.launch_run(
                OpenClawAgentLaunchInput(
                    session_key="agent:worker-agent",
                    message="body",
                    extra_system_prompt="system",
                    idempotency_key="dispatch:dispatch-123",
                )
            )

    assert seen_methods == []


@pytest.mark.asyncio
async def test_launch_rejects_non_accepted_gateway_status(tmp_path: Path) -> None:
    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(device_token=None)
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        assert request["method"] == "agent"
        response = agent_accepted_fixture()
        response["id"] = request["id"]
        response["payload"]["status"] = "queued"
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data")
        with pytest.raises(Exception, match="accepted"):
            await adapter.launch_run(build_test_launch_request())


@pytest.mark.asyncio
async def test_wait_rejects_mismatched_gateway_run_id(tmp_path: Path) -> None:
    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(device_token=None)
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        assert request["method"] == "agent.wait"
        response = agent_wait_fixture(run_id="run-wrong", status="ok")
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
            agent_id=None,
        )
        with pytest.raises(OpenClawProtocolError, match="runId"):
            await adapter.wait_for_run(OpenClawWaitRequest(run_id="run-123"))
