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
        timeout_seconds = timeout_ms / 1000
        stream_idle_timeout_seconds = max(timeout_seconds, 300.0)
        self.timeout = httpx.Timeout(
            stream_idle_timeout_seconds,
            connect=timeout_seconds,
            write=timeout_seconds,
            pool=timeout_seconds,
            read=stream_idle_timeout_seconds,
        )
        self.transport = transport

    async def create_response(self, request: OpenClawRequest) -> OpenClawResponse:
        headers = {
            "Authorization": f"Bearer {self.gateway_token}",
            "Accept": "text/event-stream",
            "x-openclaw-session-key": request.session_key,
            "x-openclaw-agent-id": self.agent_id,
        }
        payload: dict[str, Any] = {
            "model": f"openclaw/{self.agent_id}",
            "input": request.input,
            "stream": True,
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
                async with client.stream(
                    "POST",
                    "/v1/responses",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        error_text = await response.aread()
                        raise OpenClawRequestError(
                            response.status_code,
                            error_text.decode(errors="replace"),
                        )

                    content_type = response.headers.get("content-type", "")
                    if "text/event-stream" in content_type.lower():
                        return await _read_sse_response(response)

                    raw_bytes = await response.aread()
        except httpx.TimeoutException as exc:
            raise OpenClawTimeoutError("OpenClaw request timed out") from exc
        except httpx.HTTPError as exc:
            raise OpenClawIntegrationError(f"OpenClaw HTTP transport failed: {exc}") from exc

        try:
            raw = json.loads(raw_bytes.decode())
        except ValueError as exc:
            raise OpenClawIntegrationError(
                f"OpenClaw returned non-JSON response: {raw_bytes[:200].decode(errors='replace')}"
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


async def _read_sse_response(response: httpx.Response) -> OpenClawResponse:
    event_name: str | None = None
    data_lines: list[str] = []
    response_id: str | None = None
    accumulated_text = ""
    terminal_response: dict[str, Any] | None = None
    failure_message: str | None = None

    def flush_event() -> None:
        nonlocal event_name, data_lines, response_id
        nonlocal accumulated_text, terminal_response, failure_message

        if not data_lines:
            event_name = None
            return

        data = "\n".join(data_lines)
        data_lines = []
        if data == "[DONE]":
            event_name = None
            return

        parsed: dict[str, Any] | str
        try:
            loaded = json.loads(data)
            parsed = loaded if isinstance(loaded, dict) else data
        except ValueError:
            parsed = data

        resolved_event = event_name
        if resolved_event is None and isinstance(parsed, dict):
            resolved_event = _coerce_str(parsed.get("type"))

        if isinstance(parsed, dict):
            response_payload = parsed.get("response")
            if isinstance(response_payload, dict):
                response_id = _coerce_str(response_payload.get("id")) or response_id
                if resolved_event in {"response.completed", "response.failed"}:
                    terminal_response = response_payload
                    if resolved_event == "response.failed":
                        error = response_payload.get("error")
                        if isinstance(error, dict):
                            failure_message = _coerce_str(error.get("message"))

            if resolved_event == "response.output_text.delta":
                delta = _coerce_str(parsed.get("delta"))
                if delta:
                    accumulated_text += delta
            elif resolved_event == "response.output_text.done":
                text = _coerce_str(parsed.get("text"))
                if text and not accumulated_text:
                    accumulated_text = text

        event_name = None

    async for line in response.aiter_lines():
        if line == "":
            flush_event()
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip() or None
            continue
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].lstrip())

    flush_event()

    if terminal_response is None:
        raise OpenClawIntegrationError(
            "OpenClaw streaming response ended without a terminal "
            "response.completed/response.failed event"
        )

    final_text = accumulated_text or _extract_output_text(terminal_response)
    final_status = _coerce_str(terminal_response.get("status"))
    if final_status == "failed":
        raise OpenClawIntegrationError(failure_message or "OpenClaw streaming response failed")

    return OpenClawResponse(
        response_id=response_id or _coerce_str(terminal_response.get("id")),
        output_text=final_text,
        raw=terminal_response,
    )


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
