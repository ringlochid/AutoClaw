"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.session_keys as _owner

AgentScopedSessionKeyParts = _owner.AgentScopedSessionKeyParts
normalize_agent_launch_input = _owner.normalize_agent_launch_input
normalize_openclaw_agent_id = _owner.normalize_openclaw_agent_id
normalize_transport_session_key = _owner.normalize_transport_session_key
parse_agent_scoped_openclaw_session_key = _owner.parse_agent_scoped_openclaw_session_key

__all__ = [
    "AgentScopedSessionKeyParts",
    "normalize_agent_launch_input",
    "normalize_openclaw_agent_id",
    "normalize_transport_session_key",
    "parse_agent_scoped_openclaw_session_key",
]
