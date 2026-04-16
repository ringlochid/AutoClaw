from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from pytest import MonkeyPatch

from app.config import Settings
from app.integrations.openclaw import (
    OpenClawConfigurationError,
    OpenClawIntegrationError,
    OpenClawRequest,
    create_openclaw_client,
)


@pytest.fixture
def base_settings() -> Settings:
    return Settings.model_construct(
        openclaw_gateway_token="",
        openclaw_base_url="http://127.0.0.1:18789",
        openclaw_agent_id="autoclaw-worker",
        openclaw_timeout_ms=20_000,
        api_key="autoclaw-operator-test-key",
        internal_api_key="autoclaw-internal-test-key",
    )


def test_create_openclaw_client_prefers_explicit_autoclaw_token(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "from-openclaw-env")
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "from-autoclaw-config"

    client = create_openclaw_client(base_settings)

    assert client.gateway_token == "from-autoclaw-config"


def test_create_openclaw_client_falls_back_to_openclaw_gateway_env(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "from-openclaw-env")
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "__OPENCLAW_REDACTED__"

    client = create_openclaw_client(base_settings)

    assert client.gateway_token == "from-openclaw-env"


def test_create_openclaw_client_falls_back_to_openclaw_config(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    config_path = tmp_path / "openclaw.json"
    config_path.write_text('{"gateway":{"auth":{"token":"from-openclaw-config"}}}')
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(config_path))
    base_settings.openclaw_gateway_token = "__OPENCLAW_REDACTED__"

    client = create_openclaw_client(base_settings)

    assert client.gateway_token == "from-openclaw-config"


def test_create_openclaw_client_raises_when_no_token_source_exists(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "__OPENCLAW_REDACTED__"

    with pytest.raises(OpenClawConfigurationError):
        create_openclaw_client(base_settings)


def test_create_openclaw_client_uses_bounded_stream_idle_timeout(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "from-autoclaw-config"

    client = create_openclaw_client(base_settings)

    assert client.timeout.connect == 20.0
    assert client.timeout.write == 20.0
    assert client.timeout.pool == 20.0
    assert client.timeout.read == 300.0


@pytest.mark.asyncio
async def test_create_response_uses_streaming_sse_and_collects_output(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "from-autoclaw-config"

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["payload"] = request.read().decode()
        body = "".join(
            [
                'event: response.created\n',
                'data: {"type":"response.created","response":{"id":"resp_stream","status":"in_progress","output":[]}}\n\n',
                'event: response.output_text.delta\n',
                'data: {"type":"response.output_text.delta","delta":"hel"}\n\n',
                'event: response.output_text.delta\n',
                'data: {"type":"response.output_text.delta","delta":"lo"}\n\n',
                'event: response.completed\n',
                'data: {"type":"response.completed","response":{"id":"resp_stream","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":"hello"}]}]}}\n\n',
                'data: [DONE]\n\n',
            ]
        )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream; charset=utf-8"},
            content=body,
        )

    client = create_openclaw_client(base_settings, transport=httpx.MockTransport(handler))

    response = await client.create_response(
        OpenClawRequest(session_key="node-session", input="hello from AutoClaw")
    )

    assert response.response_id == "resp_stream"
    assert response.output_text == "hello"
    assert response.raw["status"] == "completed"
    assert '"stream":true' in str(captured["payload"]).lower()
    assert captured["headers"]["accept"] == "text/event-stream"


@pytest.mark.asyncio
async def test_create_response_raises_when_stream_ends_without_terminal_event(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "from-autoclaw-config"

    def handler(_request: httpx.Request) -> httpx.Response:
        body = "".join(
            [
                'event: response.created\n',
                'data: {"type":"response.created","response":{"id":"resp_stream","status":"in_progress","output":[]}}\n\n',
                'event: response.output_text.delta\n',
                'data: {"type":"response.output_text.delta","delta":"hello"}\n\n',
                'data: [DONE]\n\n',
            ]
        )
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream; charset=utf-8"},
            content=body,
        )

    client = create_openclaw_client(base_settings, transport=httpx.MockTransport(handler))

    with pytest.raises(OpenClawIntegrationError, match="terminal"):
        await client.create_response(OpenClawRequest(session_key="node-session", input="hi"))


@pytest.mark.asyncio
async def test_create_response_falls_back_to_json_when_gateway_does_not_stream(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "from-autoclaw-config"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={
                "id": "resp_json",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "plain json"}],
                    }
                ],
            },
        )

    client = create_openclaw_client(base_settings, transport=httpx.MockTransport(handler))

    response = await client.create_response(OpenClawRequest(session_key="node-session", input="hi"))

    assert response.response_id == "resp_json"
    assert response.output_text == "plain json"
