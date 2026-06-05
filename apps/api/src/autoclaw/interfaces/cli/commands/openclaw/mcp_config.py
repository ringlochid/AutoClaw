from __future__ import annotations

from pathlib import Path

from autoclaw.config import load_settings
from autoclaw.integrations.openclaw.gateway.discovery import OpenClawHostSupportStatus
from autoclaw.integrations.openclaw.gateway.host_setup import (
    build_autoclaw_mcp_servers,
    set_openclaw_mcp_servers,
)
from autoclaw.integrations.openclaw.gateway.preflight import openclaw_preflight_report
from autoclaw.interfaces.cli.support import command_env


def reconcile_openclaw_mcp_server_config(config_path: Path) -> tuple[str, ...]:
    with command_env(config_path=config_path):
        settings = load_settings()
        host_state = openclaw_preflight_report(settings.openclaw)
    if (
        not host_state.binary_found
        or host_state.support_status != OpenClawHostSupportStatus.SUPPORTED
    ):
        raise RuntimeError(host_state.reason or "unsupported OpenClaw host state")
    desired_servers = build_autoclaw_mcp_servers(settings)
    return set_openclaw_mcp_servers(host_state, servers=desired_servers)


__all__ = ["reconcile_openclaw_mcp_server_config"]
