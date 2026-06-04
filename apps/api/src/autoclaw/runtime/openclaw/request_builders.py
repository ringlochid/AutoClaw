"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.request_builders as _owner

build_gateway_auth_state = _owner.build_gateway_auth_state
build_openclaw_abort_request = _owner.build_openclaw_abort_request
build_openclaw_agent_request = _owner.build_openclaw_agent_request
build_openclaw_compatibility_report = _owner.build_openclaw_compatibility_report
build_openclaw_connect_request = _owner.build_openclaw_connect_request
build_openclaw_wait_request = _owner.build_openclaw_wait_request
next_openclaw_request_id = _owner.next_openclaw_request_id
serialize_openclaw_gateway_request = _owner.serialize_openclaw_gateway_request

__all__ = [
    "build_gateway_auth_state",
    "build_openclaw_abort_request",
    "build_openclaw_agent_request",
    "build_openclaw_compatibility_report",
    "build_openclaw_connect_request",
    "build_openclaw_wait_request",
    "next_openclaw_request_id",
    "serialize_openclaw_gateway_request",
]
