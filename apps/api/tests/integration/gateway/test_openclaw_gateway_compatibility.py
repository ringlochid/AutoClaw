from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway import (
    OpenClawAuthError,
    OpenClawCompatibilityError,
    OpenClawWaitRequest,
    OpenClawWaitStatus,
)
from autoclaw.integrations.openclaw.gateway.fixtures import (
    agent_wait_fixture,
    auth_token_mismatch_fixture,
    connect_challenge_fixture,
    hello_ok_fixture,
)
from autoclaw.main import create_app
from pytest import MonkeyPatch
from tests.helpers.openclaw_gateway_support import (
    build_test_adapter,
    build_test_launch_request,
    configure_gateway_env,
    gateway_server,
    hello_ok_without,
    recv_json,
    save_cached_auth_state,
    send_json,
)
from websockets.asyncio.server import ServerConnection


@pytest.mark.asyncio
async def test_auth_token_mismatch_retries_once_with_cached_device_token(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing-openclaw.json"))
    auth_state_path = tmp_path / "data" / "openclaw" / "gateway-device-auth.json"
    save_cached_auth_state(auth_state_path)
    seen_auth_payloads: list[dict[str, Any]] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        request = await recv_json(connection)
        seen_auth_payloads.append(request["params"]["auth"])
        if len(seen_auth_payloads) == 1:
            response = auth_token_mismatch_fixture()
            response["id"] = request["id"]
            await send_json(connection, response)
            return
        response = hello_ok_fixture(device_token="device-token-cached")
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
            agent_id=None,
        )
        compatibility = await adapter.check_compatibility()

    assert len(seen_auth_payloads) == 2
    assert seen_auth_payloads[0] == {"token": "gateway-config-token"}
    assert seen_auth_payloads[1] == {"deviceToken": "device-token-cached"}
    assert compatibility.retry_used_cached_device_token is True


@pytest.mark.asyncio
async def test_cached_token_only_auth_token_mismatch_does_not_retry(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing-openclaw.json"))
    auth_state_path = tmp_path / "data" / "openclaw" / "gateway-device-auth.json"
    save_cached_auth_state(auth_state_path)
    seen_auth_payloads: list[dict[str, Any]] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        request = await recv_json(connection)
        seen_auth_payloads.append(request["params"]["auth"])
        response = auth_token_mismatch_fixture()
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
            gateway_token=None,
            agent_id=None,
        )
        with pytest.raises(OpenClawAuthError, match="AUTH_TOKEN_MISMATCH"):
            await adapter.check_compatibility()

    assert seen_auth_payloads == [{"deviceToken": "device-token-cached"}]


@pytest.mark.asyncio
async def test_loopback_auth_token_mismatch_retries_with_local_openclaw_gateway_token(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    local_config_path = tmp_path / "openclaw.json"
    local_config_path.write_text(
        json.dumps({"gateway": {"auth": {"token": "gateway-live-token"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(local_config_path))
    seen_auth_payloads: list[dict[str, Any]] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        request = await recv_json(connection)
        seen_auth_payloads.append(request["params"]["auth"])
        if len(seen_auth_payloads) == 1:
            response = auth_token_mismatch_fixture()
            response["id"] = request["id"]
            await send_json(connection, response)
            return
        response = hello_ok_fixture(device_token=None)
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
            gateway_token="gateway-config-token",
            agent_id=None,
        )
        compatibility = await adapter.check_compatibility()

    assert compatibility.role == "operator"
    assert seen_auth_payloads == [
        {"token": "gateway-config-token"},
        {"token": "gateway-live-token"},
    ]


@pytest.mark.asyncio
async def test_loopback_auth_token_mismatch_stops_after_one_local_token_retry(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    local_config_path = tmp_path / "openclaw.json"
    local_config_path.write_text(
        json.dumps({"gateway": {"auth": {"token": "gateway-live-token"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(local_config_path))
    auth_state_path = tmp_path / "data" / "openclaw" / "gateway-device-auth.json"
    save_cached_auth_state(auth_state_path)
    seen_auth_payloads: list[dict[str, Any]] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        request = await recv_json(connection)
        seen_auth_payloads.append(request["params"]["auth"])
        response = auth_token_mismatch_fixture()
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
        )
        with pytest.raises(OpenClawAuthError, match="AUTH_TOKEN_MISMATCH"):
            await adapter.check_compatibility()

    assert seen_auth_payloads == [
        {"token": "gateway-config-token"},
        {"token": "gateway-live-token"},
    ]


@pytest.mark.asyncio
async def test_loopback_password_auth_uses_password_payload(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    local_config_path = tmp_path / "openclaw.json"
    local_config_path.write_text(
        json.dumps({"gateway": {"auth": {"mode": "password", "password": "gateway-password"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(local_config_path))
    seen_auth_payloads: list[dict[str, Any]] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        request = await recv_json(connection)
        seen_auth_payloads.append(request["params"]["auth"])
        response = hello_ok_fixture(device_token=None)
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
            gateway_token=None,
            agent_id=None,
        )
        compatibility = await adapter.check_compatibility()

    assert compatibility.role == "operator"
    assert seen_auth_payloads == [{"password": "gateway-password"}]


@pytest.mark.asyncio
async def test_loopback_no_auth_omits_auth_payload(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    local_config_path = tmp_path / "openclaw.json"
    local_config_path.write_text(
        json.dumps({"gateway": {"auth": {"mode": "none"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(local_config_path))
    seen_payloads: list[dict[str, Any]] = []

    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        request = await recv_json(connection)
        seen_payloads.append(request["params"])
        response = hello_ok_fixture(device_token=None)
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
            gateway_token=None,
            agent_id=None,
        )
        compatibility = await adapter.check_compatibility()

    assert compatibility.role == "operator"
    assert "auth" not in seen_payloads[0]


@pytest.mark.asyncio
async def test_non_loopback_gateway_is_blocked_before_connect(tmp_path: Path) -> None:
    adapter = build_test_adapter(
        base_url="https://gateway.example.test",
        data_dir=tmp_path / "data",
        gateway_token="gateway-config-token",
        agent_id=None,
    )
    with pytest.raises(Exception, match=r"NON_LOOPBACK_GATEWAY_UNSUPPORTED|unsupported"):
        await adapter.check_compatibility()


@pytest.mark.asyncio
async def test_ambiguous_loopback_auth_mode_is_blocked(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    local_config_path = tmp_path / "openclaw.json"
    local_config_path.write_text(
        json.dumps(
            {
                "gateway": {
                    "auth": {
                        "token": "gateway-token",
                        "password": "gateway-password",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(local_config_path))

    adapter = build_test_adapter(
        base_url="http://127.0.0.1:18789",
        data_dir=tmp_path / "data",
        gateway_token=None,
        agent_id=None,
    )
    with pytest.raises(Exception, match=r"AMBIGUOUS_GATEWAY_AUTH_MODE|unsupported"):
        await adapter.check_compatibility()


@pytest.mark.asyncio
async def test_launch_rejects_payload_over_gateway_max_payload(tmp_path: Path) -> None:
    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(max_payload=128)
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        await connection.wait_closed()

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data")
        with pytest.raises(OpenClawCompatibilityError, match="maxPayload=128"):
            await adapter.launch_run(
                build_test_launch_request(
                    instructions_text="system" * 20,
                    input_text="body" * 40,
                )
            )


@pytest.mark.asyncio
async def test_wait_rejects_buffering_over_gateway_max_buffered_bytes(
    tmp_path: Path,
) -> None:
    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture(max_buffered_bytes=64)
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        assert request["method"] == "agent.wait"
        await send_json(
            connection,
            {
                "type": "event",
                "event": "response.delta",
                "payload": {"chunk": "x" * 128},
            },
        )
        response = agent_wait_fixture(status="ok")
        response["id"] = request["id"]
        await send_json(connection, response)

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
            agent_id=None,
        )
        with pytest.raises(OpenClawCompatibilityError, match="maxBufferedBytes=64"):
            await adapter.wait_for_run(OpenClawWaitRequest(run_id="run-123"))


@pytest.mark.asyncio
async def test_wait_accepts_live_timeout_payload_without_timestamps(
    tmp_path: Path,
) -> None:
    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture()
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        assert request["method"] == "agent.wait"
        await send_json(
            connection,
            {
                "type": "event",
                "event": "presence",
                "payload": {"presence": []},
                "seq": 1,
                "stateVersion": {"presence": 1, "health": 1},
            },
        )
        await send_json(
            connection,
            {
                "type": "res",
                "id": request["id"],
                "ok": True,
                "payload": {"runId": "run-123", "status": "timeout"},
            },
        )

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(
            base_url=base_url,
            data_dir=tmp_path / "data",
            agent_id=None,
        )
        wait_result = await adapter.wait_for_run(OpenClawWaitRequest(run_id="run-123"))

    assert wait_result.status == OpenClawWaitStatus.TIMEOUT
    assert wait_result.started_at == wait_result.ended_at


@pytest.mark.asyncio
async def test_wait_accepts_terminal_timeout_payload_with_cancel_metadata(tmp_path: Path) -> None:
    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        hello_ok = hello_ok_fixture()
        hello_ok["id"] = connect_request["id"]
        await send_json(connection, hello_ok)
        request = await recv_json(connection)
        assert request["method"] == "agent.wait"
        await send_json(
            connection,
            {
                "type": "res",
                "id": request["id"],
                "ok": True,
                "payload": {
                    "runId": "run-123",
                    "status": "timeout",
                    "error": "aborted",
                    "stopReason": "rpc",
                    "livenessState": "blocked",
                },
            },
        )

    async with gateway_server(handler) as base_url:
        adapter = build_test_adapter(base_url=base_url, data_dir=tmp_path / "data", agent_id=None)
        wait_result = await adapter.wait_for_run(OpenClawWaitRequest(run_id="run-123"))

    assert wait_result.status == OpenClawWaitStatus.ERROR
    assert wait_result.error is not None
    assert wait_result.error.message == "aborted"
    assert wait_result.gateway_status == "timeout"
    assert wait_result.stop_reason == "rpc"
    assert wait_result.liveness_state == "blocked"
    assert wait_result.started_at == wait_result.ended_at


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("hello_ok_payload", "expected_message"),
    [
        (
            hello_ok_without("payload", "server"),
            "hello-ok.server",
        ),
        (
            hello_ok_without("payload", "snapshot"),
            "hello-ok.snapshot",
        ),
        (
            hello_ok_without("payload", "auth"),
            "hello-ok.auth",
        ),
        (
            hello_ok_without("payload", "auth", "role"),
            "hello-ok.auth.role",
        ),
        (
            hello_ok_without("payload", "auth", "scopes"),
            "hello-ok.auth.scopes",
        ),
        (
            hello_ok_without("payload", "features", "events"),
            "required event subset",
        ),
        (
            hello_ok_fixture(events=["health"]),
            "required event subset",
        ),
        (
            hello_ok_fixture(events=[]),
            "required event subset",
        ),
        (
            hello_ok_fixture(protocol=999),
            "protocol mismatch",
        ),
        (
            hello_ok_fixture(methods=["agent", "sessions.abort"]),
            "required agent/agent.wait/sessions.abort subset",
        ),
        (
            hello_ok_fixture(methods=[]),
            "required agent/agent.wait/sessions.abort subset",
        ),
        (
            hello_ok_fixture(scopes=["operator.read"]),
            "scopes do not satisfy operator.read/operator.write",
        ),
    ],
)
async def test_lifespan_fails_closed_on_gateway_compatibility_drift(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    hello_ok_payload: dict[str, Any],
    expected_message: str,
) -> None:
    async def handler(connection: ServerConnection) -> None:
        await send_json(connection, connect_challenge_fixture())
        connect_request = await recv_json(connection)
        payload = dict(hello_ok_payload)
        payload["id"] = connect_request["id"]
        await send_json(connection, payload)

    async with gateway_server(handler) as base_url:
        configure_gateway_env(monkeypatch, tmp_path=tmp_path, base_url=base_url)
        app = create_app()
        with pytest.raises(OpenClawCompatibilityError, match=expected_message):
            async with app.router.lifespan_context(app):
                pass
        get_settings.cache_clear()
