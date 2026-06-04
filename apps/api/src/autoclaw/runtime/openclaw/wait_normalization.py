"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.wait_normalization as _owner

normalize_gateway_wait_status = _owner.normalize_gateway_wait_status

__all__ = [
    "normalize_gateway_wait_status",
]
