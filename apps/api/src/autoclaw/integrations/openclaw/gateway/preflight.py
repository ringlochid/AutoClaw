from __future__ import annotations

from autoclaw.config import OpenClawSettings
from autoclaw.integrations.openclaw.gateway.contracts import OpenClawConfigurationError
from autoclaw.integrations.openclaw.gateway.discovery import (
    OpenClawResolvedHostState,
    discover_openclaw_host_state,
)


def require_supported_openclaw_host(config: OpenClawSettings) -> OpenClawResolvedHostState:
    host_state = openclaw_preflight_report(config)
    if not host_state.binary_found:
        raise OpenClawConfigurationError(
            "OpenClaw binary could not be resolved from PATH or config"
        )
    if host_state.support_status != "supported":
        raise OpenClawConfigurationError(
            f"OpenClaw host shape is unsupported for AutoClaw: {host_state.reason or 'unknown'}"
        )
    return host_state


def openclaw_preflight_report(config: OpenClawSettings) -> OpenClawResolvedHostState:
    return discover_openclaw_host_state(config)


__all__ = ["openclaw_preflight_report", "require_supported_openclaw_host"]
