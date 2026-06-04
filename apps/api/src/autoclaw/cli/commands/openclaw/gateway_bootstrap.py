from __future__ import annotations

from pathlib import Path
from typing import Any

from autoclaw.cli.commands.bootstrap import update_config_sections
from autoclaw.cli.support import command_env
from autoclaw.cli.terminal.prompts import text
from autoclaw.config import load_settings
from autoclaw.runtime.openclaw.discovery import OpenClawResolvedHostState
from autoclaw.runtime.openclaw.host_setup import (
    gateway_bootstrap_needed,
    host_base_url_from_config,
    patch_openclaw_gateway_settings,
    resolved_gateway_bootstrap_values,
)
from autoclaw.runtime.openclaw.preflight import openclaw_preflight_report


def bootstrap_openclaw_gateway_access(
    *,
    config_path: Path,
    is_non_interactive: bool,
    gateway_token: str | None = None,
    gateway_port: int | None = None,
    openclaw_base_url: str | None = None,
) -> OpenClawResolvedHostState:
    with command_env(config_path=config_path, openclaw_base_url=openclaw_base_url):
        settings = load_settings()
        host_state = openclaw_preflight_report(settings.openclaw)
    if not gateway_bootstrap_needed(host_state):
        return host_state

    if is_non_interactive:
        if gateway_token is None and not settings.openclaw.gateway_token:
            raise RuntimeError(
                "OpenClaw gateway token is required for non-interactive gateway bootstrap"
            )
        resolved_token, resolved_port = resolved_gateway_bootstrap_values(
            settings=settings,
            host_state=host_state,
            gateway_token=gateway_token or settings.openclaw.gateway_token,
            gateway_port=gateway_port,
        )
    else:
        resolved_token, resolved_port = _interactive_gateway_bootstrap_values(
            settings=settings,
            host_state=host_state,
        )

    patch_openclaw_gateway_settings(
        host_state,
        gateway_port=resolved_port,
        gateway_token=resolved_token,
    )
    update_config_sections(
        config_path,
        section_updates={
            "openclaw": {
                "base_url": f"http://127.0.0.1:{resolved_port}",
                "gateway_token": resolved_token,
                "config_path": host_state.config_path,
                "binary_path": host_state.binary_path,
            }
        },
    )
    with command_env(config_path=config_path):
        refreshed_settings = load_settings()
        return openclaw_preflight_report(refreshed_settings.openclaw)


def build_effective_openclaw_base_url(gateway_port: int | None) -> str | None:
    if gateway_port is None:
        return None
    return f"http://127.0.0.1:{gateway_port}"


def persist_openclaw_base_url(
    config_path: Path,
    *,
    openclaw_base_url: str | None,
) -> None:
    if openclaw_base_url is None:
        return
    update_config_sections(
        config_path,
        section_updates={"openclaw": {"base_url": openclaw_base_url}},
    )


def _resolve_gateway_port_from_url(base_url: str) -> int | None:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
    except ValueError:
        return None
    return parsed.port


def _interactive_gateway_bootstrap_values(
    *,
    settings: Any,
    host_state: OpenClawResolvedHostState,
) -> tuple[str, int]:
    default_port = (
        _resolve_gateway_port_from_url(settings.openclaw.base_url)
        or _resolve_gateway_port_from_url(host_base_url_from_config(host_state) or "")
        or 18789
    )
    gateway_port = int(
        text(
            "OpenClaw gateway port",
            default_value=str(default_port),
            hint="AutoClaw can patch the local OpenClaw gateway config to token-auth on loopback.",
        )
    )
    gateway_token = text(
        "OpenClaw gateway token",
        default_value=settings.openclaw.gateway_token or None,
        is_sensitive=True,
    )
    return gateway_token, gateway_port


__all__ = [
    "bootstrap_openclaw_gateway_access",
    "build_effective_openclaw_base_url",
    "persist_openclaw_base_url",
]
