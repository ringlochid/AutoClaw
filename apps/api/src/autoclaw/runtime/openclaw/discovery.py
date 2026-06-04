"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.discovery as _owner

DEFAULT_OPENCLAW_CONFIG_PATH = _owner.DEFAULT_OPENCLAW_CONFIG_PATH
OpenClawEffectiveAuthMode = _owner.OpenClawEffectiveAuthMode
OpenClawHostSupportStatus = _owner.OpenClawHostSupportStatus
OpenClawResolvedHostState = _owner.OpenClawResolvedHostState
discover_openclaw_host_state = _owner.discover_openclaw_host_state
is_direct_loopback_openclaw_gateway = _owner.is_direct_loopback_openclaw_gateway
load_openclaw_config_payload = _owner.load_openclaw_config_payload
normalize_openclaw_secret = _owner.normalize_openclaw_secret
require_supported_openclaw_host = _owner.require_supported_openclaw_host
resolve_openclaw_binary_path = _owner.resolve_openclaw_binary_path
resolve_openclaw_config_path = _owner.resolve_openclaw_config_path

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
