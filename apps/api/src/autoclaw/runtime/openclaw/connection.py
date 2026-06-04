"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.connection as _owner

ClientConnection = _owner.ClientConnection
connect = _owner.connect
connect_and_handshake = _owner.connect_and_handshake
open_gateway_connection = _owner.open_gateway_connection

__all__ = [
    "ClientConnection",
    "connect",
    "connect_and_handshake",
    "open_gateway_connection",
]
