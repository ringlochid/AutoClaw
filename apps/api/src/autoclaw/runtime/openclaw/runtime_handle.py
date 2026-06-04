"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.runtime_handle as _owner

OpenClawGatewayRuntimeHandle = _owner.OpenClawGatewayRuntimeHandle
OpenClawRequestDispatchError = _owner.OpenClawRequestDispatchError

__all__ = [
    "OpenClawGatewayRuntimeHandle",
    "OpenClawRequestDispatchError",
]
