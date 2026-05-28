from __future__ import annotations

import os

from app.config import OpenClawSettings
from app.runtime.openclaw.discovery import (
    load_openclaw_config_payload,
    normalize_openclaw_secret,
    resolve_openclaw_config_path,
)


def _config_auth_value(config: OpenClawSettings | None, key: str) -> str | None:
    if config is None:
        config_path = resolve_openclaw_config_path(OpenClawSettings())
    else:
        config_path = resolve_openclaw_config_path(config)
    payload = load_openclaw_config_payload(config_path)
    if payload is None:
        return None
    gateway = payload.get("gateway") if isinstance(payload, dict) else None
    auth = gateway.get("auth") if isinstance(gateway, dict) else None
    if not isinstance(auth, dict):
        return None
    raw = auth.get(key)
    if isinstance(raw, dict):
        return None
    return normalize_openclaw_secret(raw)


def resolve_local_openclaw_gateway_token(config: OpenClawSettings | None = None) -> str | None:
    env_token = normalize_openclaw_secret(os.environ.get("OPENCLAW_GATEWAY_TOKEN"))
    if env_token:
        return env_token
    if config is not None:
        explicit = normalize_openclaw_secret(config.gateway_token)
        if explicit:
            return explicit
    return _config_auth_value(config, "token")


def resolve_local_openclaw_gateway_password(config: OpenClawSettings | None = None) -> str | None:
    env_password = normalize_openclaw_secret(os.environ.get("OPENCLAW_GATEWAY_PASSWORD"))
    if env_password:
        return env_password
    if config is not None:
        explicit = normalize_openclaw_secret(config.gateway_password)
        if explicit:
            return explicit
    return _config_auth_value(config, "password")


__all__ = [
    "resolve_local_openclaw_gateway_password",
    "resolve_local_openclaw_gateway_token",
]
