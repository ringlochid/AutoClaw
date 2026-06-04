"""Explicit Phase 6 bridge for the legacy gateway-observability owner."""

from __future__ import annotations

from app.runtime.control.dispatch import gateway_observability as legacy_gateway_observability

OPENCLAW_GATEWAY_TRANSPORT_FAMILY = legacy_gateway_observability.OPENCLAW_GATEWAY_TRANSPORT_FAMILY
append_gateway_event = legacy_gateway_observability.append_gateway_event
record_gateway_transport_failure = legacy_gateway_observability.record_gateway_transport_failure
record_gateway_wait_terminal = legacy_gateway_observability.record_gateway_wait_terminal
record_gateway_wait_timeout = legacy_gateway_observability.record_gateway_wait_timeout

__all__ = [
    "OPENCLAW_GATEWAY_TRANSPORT_FAMILY",
    "append_gateway_event",
    "record_gateway_transport_failure",
    "record_gateway_wait_terminal",
    "record_gateway_wait_timeout",
]
