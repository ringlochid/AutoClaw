"""Explicit Phase 6 bridge for the legacy dispatch-gateway owner."""

from __future__ import annotations

from app.runtime.control.dispatch import gateway as legacy_gateway

OPENCLAW_GATEWAY_TRANSPORT_FAMILY = legacy_gateway.OPENCLAW_GATEWAY_TRANSPORT_FAMILY
AcceptedGatewayRunCleanupResult = legacy_gateway.AcceptedGatewayRunCleanupResult
GatewayDispatchLaunchError = legacy_gateway.GatewayDispatchLaunchError
GatewayDispatchLaunchOutcome = legacy_gateway.GatewayDispatchLaunchOutcome
abort_gateway_dispatch = legacy_gateway.abort_gateway_dispatch
abort_gateway_run = legacy_gateway.abort_gateway_run
abort_gateway_run_with_fallback = legacy_gateway.abort_gateway_run_with_fallback
cleanup_accepted_gateway_run = legacy_gateway.cleanup_accepted_gateway_run
mint_gateway_session_key = legacy_gateway.mint_gateway_session_key
perform_gateway_dispatch_launch = legacy_gateway.perform_gateway_dispatch_launch
record_gateway_transport_failure = legacy_gateway.record_gateway_transport_failure
record_gateway_wait_terminal = legacy_gateway.record_gateway_wait_terminal
record_gateway_wait_timeout = legacy_gateway.record_gateway_wait_timeout
resolve_gateway_session_key = legacy_gateway.resolve_gateway_session_key
wait_for_gateway_dispatch = legacy_gateway.wait_for_gateway_dispatch
wait_for_gateway_run = legacy_gateway.wait_for_gateway_run
wait_for_gateway_run_with_fallback = legacy_gateway.wait_for_gateway_run_with_fallback

__all__ = [
    "OPENCLAW_GATEWAY_TRANSPORT_FAMILY",
    "AcceptedGatewayRunCleanupResult",
    "GatewayDispatchLaunchError",
    "GatewayDispatchLaunchOutcome",
    "abort_gateway_dispatch",
    "abort_gateway_run",
    "abort_gateway_run_with_fallback",
    "cleanup_accepted_gateway_run",
    "mint_gateway_session_key",
    "perform_gateway_dispatch_launch",
    "record_gateway_transport_failure",
    "record_gateway_wait_terminal",
    "record_gateway_wait_timeout",
    "resolve_gateway_session_key",
    "wait_for_gateway_dispatch",
    "wait_for_gateway_run",
    "wait_for_gateway_run_with_fallback",
]
