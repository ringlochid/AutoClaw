"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.auth_state as _owner

StoredDeviceToken = _owner.StoredDeviceToken
StoredGatewayAuthState = _owner.StoredGatewayAuthState
load_gateway_auth_state = _owner.load_gateway_auth_state
save_gateway_auth_state = _owner.save_gateway_auth_state

__all__ = [
    "StoredDeviceToken",
    "StoredGatewayAuthState",
    "load_gateway_auth_state",
    "save_gateway_auth_state",
]
