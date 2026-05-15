from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.runtime.openclaw import OpenClawAbortRequest, OpenClawWaitRequest, OpenClawWaitStatus
from app.runtime.openclaw.auth_state import load_gateway_auth_state
from app.runtime.openclaw.contracts import OpenClawProtocolError
from app.runtime.openclaw.fixtures import (
    agent_accepted_fixture,
    agent_wait_fixture,
    connect_challenge_fixture,
    hello_ok_fixture,
    sessions_abort_fixture,
)
from tests.integration.phase4a.support import (
    build_test_adapter,
    build_test_launch_request,
    gateway_server,
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
        assert connect_request["params"]["minProtocol"] == 3
        assert connect_request["params"]["maxProtocol"] == 3
        response = hello_ok_fixture(device_token="device-token-abc")
        response["id"] = connect_request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data")
        compatibility = await adapter.check_compatibility()

    assert compatibility.protocol_version == 3
    assert compatibility.issued_device_token == "device-token-abc"
    assert compatibility.available_methods == ("agent", "agent.wait", "sessions.abort")
    assert compatibility.tick_interval_ms == 15000
    assert received_connect["params"]["client"]["id"] == "gateway-client"
    assert received_connect["params"]["client"]["mode"] == "backend"
    assert received_connect["params"]["auth"]["token"] == "gateway-config-token"
    assert "device" not in received_connect["params"]
    auth_state = load_gateway_auth_state(
        tmp_path / "data" / "openclaw" / "gateway-device-auth.json"
    )
    assert auth_state is not None
    assert auth_state.primary_token is not None
    assert auth_state.primary_token.device_token == "device-token-abc"


@pytest.mark.asyncio
async def test_launch_wait_and_abort_round_trip(tmp_path: Path) -> None:
    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        response_id = connect_request["id"]
        hello_ok = hello_ok_fixture(device_token=None)
        hello_ok["id"] = response_id
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        if request["method"] == "agent":
            assert request["params"]["sessionKey"] == "agent:worker-agent:session-123"
            assert request["params"]["idempotencyKey"] == "dispatch:dispatch-123"
            assert request["params"]["message"] == "system\n\nbody"
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
