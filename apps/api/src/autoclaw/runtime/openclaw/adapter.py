"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.adapter as _owner

OpenClawGatewayAdapter = _owner.OpenClawGatewayAdapter
build_openclaw_gateway_adapter = _owner.build_openclaw_gateway_adapter
openclaw_startup_compatibility_required = _owner.openclaw_startup_compatibility_required

__all__ = [
    "OpenClawGatewayAdapter",
    "build_openclaw_gateway_adapter",
    "openclaw_startup_compatibility_required",
]
