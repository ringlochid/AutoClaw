from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock

import pytest
from autoclaw.config import OpenClawSettings
from autoclaw.integrations.openclaw.gateway.connection import (
    ClientConnection,
    connect_and_handshake,
)
from autoclaw.integrations.openclaw.gateway.contracts import (
    OpenClawAuthError,
    OpenClawCompatibilityError,
)
from autoclaw.integrations.openclaw.gateway.fixtures import hello_ok_fixture
from autoclaw.integrations.openclaw.gateway.protocol import OpenClawHelloOkPayload
from autoclaw.integrations.openclaw.gateway.request_builders import (
    build_openclaw_compatibility_report,
)


@pytest.mark.asyncio
async def test_openclaw_loopback_connection_sends_origin_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyConnection:
        async def close(self) -> None:
            return None

    async def fake_connect(*args: object, **kwargs: object) -> ClientConnection:
        captured.update(kwargs)
        return cast(ClientConnection, DummyConnection())

    monkeypatch.setattr("autoclaw.integrations.openclaw.gateway.connection.connect", fake_connect)
    monkeypatch.setattr(
        "autoclaw.integrations.openclaw.gateway.connection.receive_connect_challenge",
        AsyncMock(return_value={"type": "connect_challenge", "challenge": "abc"}),
    )
    monkeypatch.setattr(
        "autoclaw.integrations.openclaw.gateway.connection.build_openclaw_connect_request",
        lambda **kwargs: type("Req", (), {"id": "connect-1"})(),
    )
    monkeypatch.setattr(
        "autoclaw.integrations.openclaw.gateway.connection.serialize_openclaw_gateway_request",
        lambda _req: "{}",
    )
    response = type(
        "Resp",
        (),
        {"ok": False, "error": type("Err", (), {"details": None, "message": "stop"})()},
    )()
    monkeypatch.setattr(
        "autoclaw.integrations.openclaw.gateway.connection._request_during_handshake",
        AsyncMock(return_value=response),
    )

    with pytest.raises(OpenClawAuthError):
        await connect_and_handshake(
            config=OpenClawSettings(base_url="http://127.0.0.1:18789"),
            auth_state_path=Path("/tmp/autoclaw-auth-state.json"),
            ws_url="ws://127.0.0.1:18789/ws",
            should_use_cached_device_token=False,
            auth_state=None,
        )

    assert captured["origin"] == "http://127.0.0.1:18789"


def test_build_openclaw_compatibility_report_rejects_missing_required_hello_auth_scopes() -> None:
    response = hello_ok_fixture(scopes=[])
    hello_ok = OpenClawHelloOkPayload.model_validate(response["payload"])
    with pytest.raises(OpenClawCompatibilityError, match=r"operator\.read/operator\.write"):
        build_openclaw_compatibility_report(
            ws_url="ws://127.0.0.1:18789/ws",
            hello_ok=hello_ok,
            retry_used_cached_device_token=False,
        )
