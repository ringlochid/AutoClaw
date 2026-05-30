from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Literal, TypedDict

from app.config import OpenClawSettings
from app.runtime.openclaw.auth_resolution import (
    resolve_local_openclaw_gateway_password,
    resolve_local_openclaw_gateway_token,
)
from app.runtime.openclaw.auth_state import StoredGatewayAuthState
from app.runtime.openclaw.contracts import (
    OpenClawCompatibilityError,
    OpenClawConfigurationError,
)
from app.runtime.openclaw.discovery import (
    OpenClawEffectiveAuthMode,
    discover_openclaw_host_state,
    is_direct_loopback_openclaw_gateway,
    normalize_openclaw_secret,
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


class OpenClawGatewayPasswordAuthPayload(TypedDict):
    password: str


class OpenClawDeviceTokenAuthPayload(TypedDict):
    deviceToken: str


OpenClawConnectAuthPayload = (
    OpenClawGatewayTokenAuthPayload
    | OpenClawGatewayPasswordAuthPayload
    | OpenClawDeviceTokenAuthPayload
)


class OpenClawConnectClientPayload(TypedDict):
    id: str
    version: str
    platform: str
    mode: Literal["cli", "webchat"]


class OpenClawConnectDevicePayload(TypedDict):
    id: str
    publicKey: str
    signature: str
    nonce: str
    signedAt: int


class OpenClawConnectParamsPayload(TypedDict, total=False):
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
    config: OpenClawSettings,
    auth_state: StoredGatewayAuthState | None,
    use_cached_device_token: bool,
    gateway_token_override: str | None = None,
) -> tuple[OpenClawConnectAuthPayload | None, tuple[str, ...]]:
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

    if gateway_token_override:
        return {"token": gateway_token_override}, default_scopes

    host_state = discover_openclaw_host_state(config)
    if host_state.effective_auth == OpenClawEffectiveAuthMode.TOKEN:
        resolved_token = resolve_local_openclaw_gateway_token(config)
        if resolved_token is None:
            raise OpenClawConfigurationError(
                "OpenClaw token auth is selected but no token is available"
            )
        return {"token": resolved_token}, default_scopes
    if host_state.effective_auth == OpenClawEffectiveAuthMode.PASSWORD:
        resolved_password = resolve_local_openclaw_gateway_password(config)
        if resolved_password is None:
            raise OpenClawConfigurationError(
                "OpenClaw password auth is selected but no password is available"
            )
        return {"password": resolved_password}, default_scopes
    if host_state.effective_auth == OpenClawEffectiveAuthMode.NONE:
        if not host_state.loopback:
            raise OpenClawConfigurationError(
                "OpenClaw no-auth mode is supported only for loopback gateways"
            )
        return None, default_scopes
    if auth_state is not None and auth_state.primary_token is not None:
        return (
            {"deviceToken": auth_state.primary_token.device_token},
            auth_state.primary_token.scopes or default_scopes,
        )
    raise OpenClawConfigurationError(
        "OpenClaw connect requires supported loopback auth or a cached device token"
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
                "mode": "webchat",
            },
            f"autoclaw-openclaw-webchat/{client_version}",
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
    del challenge
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
    "resolve_local_openclaw_gateway_password",
    "resolve_local_openclaw_gateway_token",
    "validate_gateway_policy",
]
