from __future__ import annotations

import json
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal, TypedDict
from urllib.parse import urlparse

from app.runtime.openclaw.auth_state import StoredGatewayAuthState
from app.runtime.openclaw.contracts import (
    OpenClawCompatibilityError,
    OpenClawConfigurationError,
)
from app.runtime.openclaw.protocol import (
    REQUIRED_GATEWAY_ROLE,
    REQUIRED_GATEWAY_SCOPES,
    OpenClawConnectChallengeEvent,
    OpenClawHelloAuth,
    OpenClawHelloOkPayload,
)


class OpenClawGatewayTokenAuthPayload(TypedDict):
    token: str


class OpenClawDeviceTokenAuthPayload(TypedDict):
    deviceToken: str


OpenClawConnectAuthPayload = OpenClawGatewayTokenAuthPayload | OpenClawDeviceTokenAuthPayload


class OpenClawConnectClientPayload(TypedDict):
    id: str
    version: str
    platform: str
    mode: Literal["cli", "backend"]


class OpenClawConnectDevicePayload(TypedDict):
    id: str
    publicKey: str
    signature: str
    nonce: str
    signedAt: int


class OpenClawConnectParamsPayload(TypedDict):
    minProtocol: int
    maxProtocol: int
    client: OpenClawConnectClientPayload
    role: Literal["operator"]
    scopes: tuple[str, ...]
    auth: OpenClawConnectAuthPayload
    locale: str
    userAgent: str
    device: OpenClawConnectDevicePayload | None


def build_openclaw_connect_auth_and_scopes(
    *,
    gateway_token: str | None,
    auth_state: StoredGatewayAuthState | None,
    use_cached_device_token: bool,
    gateway_token_override: str | None = None,
) -> tuple[OpenClawConnectAuthPayload, tuple[str, ...]]:
    default_scopes = default_gateway_scopes()
    if use_cached_device_token:
        if auth_state is None or auth_state.primary_token is None:
            raise OpenClawConfigurationError(
                "cached OpenClaw device-token retry requested without a stored token"
            )
        return (
            {"deviceToken": auth_state.primary_token.device_token},
            auth_state.primary_token.scopes or default_scopes,
        )
    shared_gateway_token = normalize_openclaw_secret(gateway_token_override or gateway_token)
    if shared_gateway_token:
        return {"token": shared_gateway_token}, default_scopes
    if auth_state is not None and auth_state.primary_token is not None:
        return (
            {"deviceToken": auth_state.primary_token.device_token},
            auth_state.primary_token.scopes or default_scopes,
        )
    raise OpenClawConfigurationError(
        "OpenClaw connect requires gateway_token or a cached device token"
    )


def build_openclaw_connect_client(
    *,
    base_url: str,
    client_version: str,
) -> tuple[OpenClawConnectClientPayload, str]:
    if is_direct_loopback_openclaw_gateway(base_url):
        return (
            {
                "id": "gateway-client",
                "version": client_version,
                "platform": sys.platform,
                "mode": "backend",
            },
            f"autoclaw-openclaw-backend/{client_version}",
        )
    return (
        {
            "id": "cli",
            "version": client_version,
            "platform": sys.platform,
            "mode": "cli",
        },
        f"openclaw-cli/{client_version}",
    )


def build_openclaw_connect_device(
    *,
    base_url: str,
    challenge: OpenClawConnectChallengeEvent,
) -> OpenClawConnectDevicePayload | None:
    if is_direct_loopback_openclaw_gateway(base_url):
        return None
    raise OpenClawConfigurationError(
        "Non-loopback OpenClaw gateway connections require signed device identity; "
        "AutoClaw does not implement that flow yet"
    )


def autoclaw_client_version() -> str:
    try:
        return version("autoclaw")
    except PackageNotFoundError:
        return "0.0.0"


def default_gateway_scopes() -> tuple[str, ...]:
    return tuple(REQUIRED_GATEWAY_SCOPES)


def require_hello_auth(hello_ok: OpenClawHelloOkPayload) -> OpenClawHelloAuth:
    if hello_ok.auth is None:
        raise OpenClawCompatibilityError("OpenClaw gateway hello-ok.auth is required")
    auth = hello_ok.auth
    if auth.role is None:
        raise OpenClawCompatibilityError("OpenClaw gateway hello-ok.auth.role is required")
    if auth.role != REQUIRED_GATEWAY_ROLE:
        raise OpenClawCompatibilityError(
            f"OpenClaw role mismatch: expected {REQUIRED_GATEWAY_ROLE}, got {auth.role}"
        )
    if not auth.scopes:
        raise OpenClawCompatibilityError("OpenClaw gateway hello-ok.auth.scopes is required")
    return auth


def validate_gateway_policy(hello_ok: OpenClawHelloOkPayload) -> None:
    if hello_ok.policy.tick_interval_ms <= 0:
        raise OpenClawCompatibilityError(
            "OpenClaw hello-ok policy.tickIntervalMs must be greater than zero"
        )
    if hello_ok.policy.max_payload is not None and hello_ok.policy.max_payload <= 0:
        raise OpenClawCompatibilityError(
            "OpenClaw hello-ok policy.maxPayload must be greater than zero when set"
        )
    if hello_ok.policy.max_buffered_bytes is not None and hello_ok.policy.max_buffered_bytes <= 0:
        raise OpenClawCompatibilityError(
            "OpenClaw hello-ok policy.maxBufferedBytes must be greater than zero when set"
        )


def is_direct_loopback_openclaw_gateway(base_url: str) -> bool:
    parsed = urlparse(base_url)
    return (parsed.hostname or "") in {"127.0.0.1", "localhost", "::1"}


def resolve_local_openclaw_gateway_token() -> str | None:
    env_token = normalize_openclaw_secret(os.environ.get("OPENCLAW_GATEWAY_TOKEN"))
    if env_token:
        return env_token
    config_path = Path(
        os.environ.get(
            "OPENCLAW_CONFIG_PATH",
            str(Path.home() / ".openclaw" / "openclaw.json"),
        )
    ).expanduser()
    if not config_path.is_file():
        return None
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    gateway = payload.get("gateway") if isinstance(payload, dict) else None
    auth = gateway.get("auth") if isinstance(gateway, dict) else None
    token = auth.get("token") if isinstance(auth, dict) else None
    return normalize_openclaw_secret(token)


def normalize_openclaw_secret(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    trimmed = raw.strip()
    if not trimmed or trimmed == "__OPENCLAW_REDACTED__":
        return None
    return trimmed


__all__ = [
    "OpenClawConnectAuthPayload",
    "OpenClawConnectClientPayload",
    "OpenClawConnectDevicePayload",
    "OpenClawConnectParamsPayload",
    "autoclaw_client_version",
    "build_openclaw_connect_auth_and_scopes",
    "build_openclaw_connect_client",
    "build_openclaw_connect_device",
    "default_gateway_scopes",
    "is_direct_loopback_openclaw_gateway",
    "normalize_openclaw_secret",
    "require_hello_auth",
    "resolve_local_openclaw_gateway_token",
    "validate_gateway_policy",
]
