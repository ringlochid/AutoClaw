"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.transport as _owner

receive_connect_challenge = _owner.receive_connect_challenge
receive_frame = _owner.receive_frame

__all__ = [
    "receive_connect_challenge",
    "receive_frame",
]
