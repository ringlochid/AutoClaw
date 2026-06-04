"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.auth_resolution as _owner

resolve_local_openclaw_gateway_password = _owner.resolve_local_openclaw_gateway_password
resolve_local_openclaw_gateway_token = _owner.resolve_local_openclaw_gateway_token

__all__ = [
    "resolve_local_openclaw_gateway_password",
    "resolve_local_openclaw_gateway_token",
]
