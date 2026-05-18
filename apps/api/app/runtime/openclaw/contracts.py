from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse

from pydantic import Field

from app.runtime.contract_models.prompt import PromptFamily, PromptTransportRequest
from app.runtime.openclaw.protocol import OpenClawGatewayError, OpenClawProtocolModel


class OpenClawWaitStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


class OpenClawObservedEvent(OpenClawProtocolModel):
    event: str
    payload: dict[str, object]
    seq: int | None = None
    state_version: int | dict[str, object] | None = Field(
        default=None,
        alias="stateVersion",
    )


class OpenClawCompatibilityReport(OpenClawProtocolModel):
    ws_url: str
    protocol_version: int
    role: str
    scopes: tuple[str, ...]
    available_methods: tuple[str, ...]
    available_events: tuple[str, ...]
    tick_interval_ms: int
    max_payload: int | None = None
    max_buffered_bytes: int | None = None
    issued_device_token: str | None = None
    retry_used_cached_device_token: bool = False


class OpenClawLaunchRequest(OpenClawProtocolModel):
    task_id: str
    dispatch_id: str
    assignment_key: str
    attempt_id: str
    node_key: str
    session_key: str
    prompt_name: PromptFamily
    transport_request: PromptTransportRequest
    idempotency_key: str


class OpenClawLaunchResult(OpenClawProtocolModel):
    session_key: str
    run_id: str
    accepted_at: datetime
    compatibility: OpenClawCompatibilityReport
    observed_events: tuple[OpenClawObservedEvent, ...] = ()


class OpenClawWaitRequest(OpenClawProtocolModel):
    run_id: str
    timeout_ms: int | None = None


class OpenClawWaitResult(OpenClawProtocolModel):
    status: OpenClawWaitStatus
    started_at: datetime
    ended_at: datetime
    error: OpenClawGatewayError | None = None
    gateway_status: str | None = None
    stop_reason: str | None = None
    liveness_state: str | None = None
    aborted: bool | None = None
    yielded: bool | None = None
    observed_events: tuple[OpenClawObservedEvent, ...] = ()


class OpenClawAbortRequest(OpenClawProtocolModel):
    session_key: str
    run_id: str | None = None


class OpenClawAbortResult(OpenClawProtocolModel):
    accepted: bool
    session_key: str
    run_id: str | None = None
    compatibility: OpenClawCompatibilityReport
    observed_events: tuple[OpenClawObservedEvent, ...] = ()


class OpenClawAdapterError(RuntimeError):
    """Base error for the OpenClaw gateway adapter."""


class OpenClawConfigurationError(OpenClawAdapterError):
    """Configuration is missing or inconsistent."""


class OpenClawProtocolError(OpenClawAdapterError):
    """Gateway frames do not match the pinned protocol contract."""


class OpenClawCompatibilityError(OpenClawAdapterError):
    """Gateway capability or policy checks failed."""


class OpenClawAuthError(OpenClawAdapterError):
    """Gateway authentication failed."""


class OpenClawTransportError(OpenClawAdapterError):
    """WebSocket transport failed."""


def gateway_ws_url_from_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise OpenClawConfigurationError(
            "OpenClaw base_url must include a scheme and host, for example http://127.0.0.1:18789"
        )
    if parsed.scheme == "http":
        scheme = "ws"
    elif parsed.scheme == "https":
        scheme = "wss"
    elif parsed.scheme in {"ws", "wss"}:
        scheme = parsed.scheme
    else:
        raise OpenClawConfigurationError(f"Unsupported OpenClaw base_url scheme '{parsed.scheme}'")
    path = parsed.path or ""
    return parsed._replace(scheme=scheme, path=path, params="", query="", fragment="").geturl()


__all__ = [
    "OpenClawAbortRequest",
    "OpenClawAbortResult",
    "OpenClawAdapterError",
    "OpenClawAuthError",
    "OpenClawCompatibilityError",
    "OpenClawCompatibilityReport",
    "OpenClawConfigurationError",
    "OpenClawLaunchRequest",
    "OpenClawLaunchResult",
    "OpenClawObservedEvent",
    "OpenClawProtocolError",
    "OpenClawTransportError",
    "OpenClawWaitRequest",
    "OpenClawWaitResult",
    "OpenClawWaitStatus",
    "gateway_ws_url_from_base_url",
]
