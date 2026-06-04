"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.gateway_event_normalization as _owner

normalize_gateway_event_name = _owner.normalize_gateway_event_name
normalize_agent_gateway_event_name = _owner.normalize_agent_gateway_event_name
normalize_lifecycle_end_event_name = _owner.normalize_lifecycle_end_event_name
read_lower_string = _owner.read_lower_string
as_payload_record = _owner.as_payload_record
read_string = _owner.read_string

__all__ = [
    "as_payload_record",
    "normalize_agent_gateway_event_name",
    "normalize_gateway_event_name",
    "normalize_lifecycle_end_event_name",
    "read_lower_string",
    "read_string",
]
