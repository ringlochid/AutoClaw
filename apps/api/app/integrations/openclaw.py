from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings, get_settings


class OpenClawIntegrationError(RuntimeError):
    """Base class for OpenClaw HTTP bridge failures."""


class OpenClawConfigurationError(OpenClawIntegrationError):
    """Raised when AutoClaw is missing required OpenClaw bridge config."""


class OpenClawTimeoutError(OpenClawIntegrationError):
    """Raised when the OpenClaw Gateway request times out."""


class OpenClawRequestError(OpenClawIntegrationError):
    """Raised when the OpenClaw Gateway returns a non-success response."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"OpenClaw request failed with HTTP {status_code}: {body[:200]}")
        self.status_code = status_code
        self.body = body


@dataclass(slots=True)
class OpenClawResponse:
    response_id: str | None
    output_text: str | None
    raw: dict[str, Any]


@dataclass(slots=True)
class OpenClawRequest:
    session_key: str
    input: str | list[dict[str, Any]]
    instructions: str | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | None = None
    previous_response_id: str | None = None
    user: str | None = None
    max_output_tokens: int | None = None


_REDACTED_GATEWAY_TOKEN = "__OPENCLAW_REDACTED__"


class OpenClawClient:
    def __init__(
        self,
        *,
        base_url: str,
        gateway_token: str,
        agent_id: str,
        timeout_ms: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.gateway_token = gateway_token
        self.agent_id = agent_id
        self.timeout = httpx.Timeout(timeout_ms / 1000)
        self.transport = transport

    async def create_response(self, request: OpenClawRequest) -> OpenClawResponse:
        headers = {
            "Authorization": f"Bearer {self.gateway_token}",
            "x-openclaw-session-key": request.session_key,
            "x-openclaw-agent-id": self.agent_id,
        }
        payload: dict[str, Any] = {
            "model": f"openclaw/{self.agent_id}",
            "input": request.input,
        }
        if request.instructions is not None:
            payload["instructions"] = request.instructions
        if request.previous_response_id is not None:
            payload["previous_response_id"] = request.previous_response_id
        if request.user is not None:
            payload["user"] = request.user
        if request.tools is not None:
            payload["tools"] = request.tools
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice
        if request.max_output_tokens is not None:
            payload["max_output_tokens"] = request.max_output_tokens

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.post("/v1/responses", headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise OpenClawTimeoutError("OpenClaw request timed out") from exc
        except httpx.HTTPError as exc:
            raise OpenClawIntegrationError(f"OpenClaw HTTP transport failed: {exc}") from exc

        if response.status_code >= 400:
            raise OpenClawRequestError(response.status_code, response.text)

        try:
            raw = response.json()
        except ValueError as exc:
            raise OpenClawIntegrationError(
                f"OpenClaw returned non-JSON response: {response.text[:200]}"
            ) from exc

        return OpenClawResponse(
            response_id=_coerce_str(raw.get("id")),
            output_text=_extract_output_text(raw),
            raw=raw,
        )


def create_openclaw_client(
    settings: Settings | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> OpenClawClient:
    resolved_settings = settings or get_settings()
    gateway_token = _resolve_gateway_token(resolved_settings)
    if gateway_token is None:
        raise OpenClawConfigurationError(
            "OpenClaw gateway token is required to dispatch to OpenClaw. "
            "Set AUTOCLAW_OPENCLAW_GATEWAY_TOKEN or OPENCLAW_GATEWAY_TOKEN, "
            "or store gateway.auth.token in the active OpenClaw config."
        )

    return OpenClawClient(
        base_url=resolved_settings.openclaw_base_url,
        gateway_token=gateway_token,
        agent_id=resolved_settings.openclaw_agent_id,
        timeout_ms=resolved_settings.openclaw_timeout_ms,
        transport=transport,
    )


def _resolve_gateway_token(settings: Settings) -> str | None:
    configured = _normalize_gateway_token(settings.openclaw_gateway_token)
    if configured is not None:
        return configured

    inherited = _normalize_gateway_token(os.environ.get("OPENCLAW_GATEWAY_TOKEN"))
    if inherited is not None:
        return inherited

    return _read_gateway_token_from_openclaw_config()


def _normalize_gateway_token(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token or token == _REDACTED_GATEWAY_TOKEN:
        return None
    return token


def _read_gateway_token_from_openclaw_config() -> str | None:
    config_path = os.environ.get("OPENCLAW_CONFIG_PATH", "").strip()
    if config_path:
        path = Path(config_path).expanduser()
    else:
        path = Path.home() / ".openclaw" / "openclaw.json"
    if not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text())
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None
    gateway = payload.get("gateway")
    if not isinstance(gateway, dict):
        return None
    auth = gateway.get("auth")
    if not isinstance(auth, dict):
        return None
    return _normalize_gateway_token(auth.get("token"))


def _coerce_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _extract_output_text(payload: dict[str, Any]) -> str | None:
    output = payload.get("output")
    if not isinstance(output, list):
        return None

    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if "text" in item and isinstance(item["text"], str):
            parts.append(item["text"])
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for content_item in content:
            if not isinstance(content_item, dict):
                continue
            text = content_item.get("text")
            if isinstance(text, str) and text:
                parts.append(text)

    if not parts:
        return None
    return "\n".join(parts)
