"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.preflight as _owner

openclaw_preflight_report = _owner.openclaw_preflight_report
require_supported_openclaw_host = _owner.require_supported_openclaw_host

__all__ = [
    "openclaw_preflight_report",
    "require_supported_openclaw_host",
]
