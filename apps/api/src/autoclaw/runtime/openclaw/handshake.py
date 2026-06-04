"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.handshake as _owner

OpenClawConnectAuthPayload = _owner.OpenClawConnectAuthPayload
OpenClawConnectClientPayload = _owner.OpenClawConnectClientPayload
OpenClawConnectDevicePayload = _owner.OpenClawConnectDevicePayload
OpenClawConnectParamsPayload = _owner.OpenClawConnectParamsPayload
autoclaw_client_version = _owner.autoclaw_client_version
build_openclaw_connect_auth_and_scopes = _owner.build_openclaw_connect_auth_and_scopes
build_openclaw_connect_client = _owner.build_openclaw_connect_client
build_openclaw_connect_device = _owner.build_openclaw_connect_device
default_gateway_scopes = _owner.default_gateway_scopes
is_direct_loopback_openclaw_gateway = _owner.is_direct_loopback_openclaw_gateway
normalize_openclaw_secret = _owner.normalize_openclaw_secret
require_hello_auth = _owner.require_hello_auth
resolve_local_openclaw_gateway_password = _owner.resolve_local_openclaw_gateway_password
resolve_local_openclaw_gateway_token = _owner.resolve_local_openclaw_gateway_token
validate_gateway_policy = _owner.validate_gateway_policy

__all__ = [
    "OpenClawConnectAuthPayload",
    "OpenClawConnectClientPayload",
    "OpenClawConnectDevicePayload",
    "OpenClawConnectParamsPayload",
    "autoclaw_client_version",
    "build_openclaw_connect_auth_and_scopes",
    "build_openclaw_connect_client",
    "build_openclaw_connect_device",
    "default_gateway_scopes",
    "is_direct_loopback_openclaw_gateway",
    "normalize_openclaw_secret",
    "require_hello_auth",
    "resolve_local_openclaw_gateway_password",
    "resolve_local_openclaw_gateway_token",
    "validate_gateway_policy",
]
