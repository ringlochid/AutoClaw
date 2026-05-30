from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from pydantic import ConfigDict

from app.config import OpenClawSettings
from app.runtime.openclaw.contracts import OpenClawConfigurationError, gateway_ws_url_from_base_url
from app.runtime.openclaw.protocol import OpenClawProtocolModel

DEFAULT_OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"


class OpenClawHostSupportStatus(str):
    SUPPORTED = "supported"
    BLOCKED = "blocked"


class OpenClawEffectiveAuthMode(str):
    TOKEN = "token"
    PASSWORD = "password"
    NONE = "none"


class OpenClawResolvedHostState(OpenClawProtocolModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    binary_path: str | None = None
    binary_found: bool
    config_path: str
    config_exists: bool
    base_url: str
    ws_url: str
    loopback: bool
    auth_mode: str | None = None
    effective_auth: str | None = None
    token_available: bool = False
    password_available: bool = False
    unresolved_secret_ref_fields: tuple[str, ...] = ()
    support_status: str
    reason: str | None = None


def normalize_openclaw_secret(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    trimmed = raw.strip()
    if not trimmed or trimmed == "__OPENCLAW_REDACTED__":
        return None
    return trimmed


def is_direct_loopback_openclaw_gateway(base_url: str) -> bool:
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    return (parsed.hostname or "") in {"127.0.0.1", "localhost", "::1"}


def resolve_openclaw_binary_path(config: OpenClawSettings) -> Path | None:
    explicit = normalize_openclaw_secret(getattr(config, "binary_path", ""))
    if explicit:
        path = Path(explicit).expanduser().resolve()
        return path if path.exists() else None
    discovered = shutil.which("openclaw")
    if discovered is None:
        return None
    return Path(discovered).expanduser().resolve()


def resolve_openclaw_config_path(config: OpenClawSettings) -> Path:
    explicit = normalize_openclaw_secret(getattr(config, "config_path", ""))
    if explicit:
        return Path(explicit).expanduser().resolve()
    env_override = normalize_openclaw_secret(os.environ.get("OPENCLAW_CONFIG_PATH"))
    if env_override:
        return Path(env_override).expanduser().resolve()
    return DEFAULT_OPENCLAW_CONFIG_PATH.expanduser().resolve()


def load_openclaw_config_payload(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_optional_string(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    stripped = raw.strip()
    return stripped or None


def _secret_value_from_config(
    auth_payload: dict[str, Any] | None,
    key: str,
) -> tuple[str | None, bool]:
    if not isinstance(auth_payload, dict):
        return None, False
    raw = auth_payload.get(key)
    if isinstance(raw, dict):
        return None, True
    return normalize_openclaw_secret(raw), False


def _base_url_from_openclaw_config(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    gateway_payload = payload.get("gateway")
    if not isinstance(gateway_payload, dict):
        return None
    raw_port = gateway_payload.get("port")
    if not isinstance(raw_port, int):
        return None
    return f"http://127.0.0.1:{raw_port}"


def discover_openclaw_host_state(config: OpenClawSettings) -> OpenClawResolvedHostState:
    config_path = resolve_openclaw_config_path(config)
    config_payload = load_openclaw_config_payload(config_path)
    gateway_payload = (
        config_payload.get("gateway")
        if isinstance(config_payload, dict) and isinstance(config_payload.get("gateway"), dict)
        else None
    )
    auth_payload = (
        gateway_payload.get("auth")
        if isinstance(gateway_payload, dict) and isinstance(gateway_payload.get("auth"), dict)
        else None
    )
    auth_mode = _normalize_optional_string(auth_payload.get("mode")) if auth_payload else None
    explicit_token = normalize_openclaw_secret(config.gateway_token)
    explicit_password = normalize_openclaw_secret(getattr(config, "gateway_password", ""))
    config_token, token_ref_unresolved = _secret_value_from_config(auth_payload, "token")
    config_password, password_ref_unresolved = _secret_value_from_config(auth_payload, "password")
    token_available = explicit_token is not None or config_token is not None
    password_available = explicit_password is not None or config_password is not None
    unresolved_fields = tuple(
        field
        for field, unresolved in (
            ("gateway.auth.token", token_ref_unresolved),
            ("gateway.auth.password", password_ref_unresolved),
        )
        if unresolved
    )

    base_url = (
        normalize_openclaw_secret(config.base_url)
        or _base_url_from_openclaw_config(config_payload)
        or "http://127.0.0.1:18789"
    )
    ws_url = gateway_ws_url_from_base_url(base_url)
    loopback = is_direct_loopback_openclaw_gateway(base_url)
    binary_path = resolve_openclaw_binary_path(config)

    support_status = OpenClawHostSupportStatus.SUPPORTED
    reason: str | None = None
    effective_auth: str | None = None

    if binary_path is None:
        support_status = OpenClawHostSupportStatus.BLOCKED
        reason = "OPENCLAW_BINARY_NOT_FOUND"
    elif not loopback:
        support_status = OpenClawHostSupportStatus.BLOCKED
        reason = "NON_LOOPBACK_GATEWAY_UNSUPPORTED"
    elif auth_mode == "trusted-proxy":
        support_status = OpenClawHostSupportStatus.BLOCKED
        reason = "TRUSTED_PROXY_AUTH_UNSUPPORTED"
    elif auth_mode == "none":
        effective_auth = OpenClawEffectiveAuthMode.NONE
    elif auth_mode == "token":
        if unresolved_fields and not token_available:
            support_status = OpenClawHostSupportStatus.BLOCKED
            reason = "UNRESOLVED_GATEWAY_TOKEN"
        elif not token_available:
            support_status = OpenClawHostSupportStatus.BLOCKED
            reason = "MISSING_GATEWAY_TOKEN"
        else:
            effective_auth = OpenClawEffectiveAuthMode.TOKEN
    elif auth_mode == "password":
        if unresolved_fields and not password_available:
            support_status = OpenClawHostSupportStatus.BLOCKED
            reason = "UNRESOLVED_GATEWAY_PASSWORD"
        elif not password_available:
            support_status = OpenClawHostSupportStatus.BLOCKED
            reason = "MISSING_GATEWAY_PASSWORD"
        else:
            effective_auth = OpenClawEffectiveAuthMode.PASSWORD
    else:
        if token_available and password_available:
            support_status = OpenClawHostSupportStatus.BLOCKED
            reason = "AMBIGUOUS_GATEWAY_AUTH_MODE"
        elif unresolved_fields and not token_available and not password_available:
            support_status = OpenClawHostSupportStatus.BLOCKED
            reason = "UNRESOLVED_GATEWAY_SECRET_REF"
        elif token_available:
            effective_auth = OpenClawEffectiveAuthMode.TOKEN
        elif password_available:
            effective_auth = OpenClawEffectiveAuthMode.PASSWORD
        else:
            support_status = OpenClawHostSupportStatus.BLOCKED
            reason = "NO_SUPPORTED_GATEWAY_AUTH"

    return OpenClawResolvedHostState(
        binary_path=str(binary_path) if binary_path is not None else None,
        binary_found=binary_path is not None,
        config_path=str(config_path),
        config_exists=config_path.is_file(),
        base_url=base_url,
        ws_url=ws_url,
        loopback=loopback,
        auth_mode=auth_mode,
        effective_auth=effective_auth,
        token_available=token_available,
        password_available=password_available,
        unresolved_secret_ref_fields=unresolved_fields,
        support_status=support_status,
        reason=reason,
    )


def require_supported_openclaw_host(state: OpenClawResolvedHostState) -> None:
    if not state.binary_found:
        raise OpenClawConfigurationError(
            "OpenClaw binary could not be resolved from PATH or config"
        )
    if state.support_status != OpenClawHostSupportStatus.SUPPORTED:
        raise OpenClawConfigurationError(
            f"OpenClaw host shape is unsupported for AutoClaw: {state.reason or 'unknown'}"
        )


__all__ = [
    "DEFAULT_OPENCLAW_CONFIG_PATH",
    "OpenClawEffectiveAuthMode",
    "OpenClawHostSupportStatus",
    "OpenClawResolvedHostState",
    "discover_openclaw_host_state",
    "is_direct_loopback_openclaw_gateway",
    "load_openclaw_config_payload",
    "normalize_openclaw_secret",
    "require_supported_openclaw_host",
    "resolve_openclaw_binary_path",
    "resolve_openclaw_config_path",
]
