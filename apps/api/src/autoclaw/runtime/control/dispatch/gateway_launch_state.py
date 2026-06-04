"""Explicit Phase 6 bridge for the legacy gateway-launch-state owner."""

from __future__ import annotations

from app.runtime.control.dispatch import gateway_launch_state as legacy_gateway_launch_state

GatewayDispatchContext = legacy_gateway_launch_state.GatewayDispatchContext
record_gateway_dispatch_acceptance = legacy_gateway_launch_state.record_gateway_dispatch_acceptance
record_gateway_dispatch_launch_failure = (
    legacy_gateway_launch_state.record_gateway_dispatch_launch_failure
)
record_gateway_dispatch_post_acceptance_failure = (
    legacy_gateway_launch_state.record_gateway_dispatch_post_acceptance_failure
)
record_gateway_dispatch_post_send_failure = (
    legacy_gateway_launch_state.record_gateway_dispatch_post_send_failure
)

__all__ = [
    "GatewayDispatchContext",
    "record_gateway_dispatch_acceptance",
    "record_gateway_dispatch_launch_failure",
    "record_gateway_dispatch_post_acceptance_failure",
    "record_gateway_dispatch_post_send_failure",
]
