from __future__ import annotations

from dataclasses import dataclass

from app.runtime.openclaw.contracts import (
    OpenClawAgentLaunchInput,
    OpenClawConfigurationError,
)


@dataclass(frozen=True)
class AgentScopedSessionKeyParts:
    original: str
    agent_id: str
    remainder: str


def normalize_agent_launch_input(
    launch_input: OpenClawAgentLaunchInput,
    agent_id: str | None,
) -> OpenClawAgentLaunchInput:
    return launch_input.model_copy(
        update={
            "session_key": normalize_transport_session_key(
                launch_input.session_key,
                agent_id,
            )
        }
    )


def normalize_transport_session_key(
    session_key: str,
    agent_id: str | None,
) -> str:
    parsed = parse_agent_scoped_openclaw_session_key(session_key)
    if parsed is not None:
        return f"agent:{normalize_openclaw_agent_id(parsed.agent_id)}:{parsed.remainder.lower()}"
    normalized = session_key.strip()
    if not normalized:
        raise OpenClawConfigurationError("OpenClaw session key must not be empty")
    return f"agent:{normalize_openclaw_agent_id(agent_id)}:{normalized.lower()}"


def normalize_openclaw_agent_id(agent_id: str | None) -> str:
    normalized = (agent_id or "main").strip().lower()
    return normalized or "main"


def parse_agent_scoped_openclaw_session_key(
    session_key: str,
) -> AgentScopedSessionKeyParts | None:
    normalized = session_key.strip()
    if not normalized:
        raise OpenClawConfigurationError("OpenClaw session key must not be empty")
    prefix, separator, remainder = normalized.partition(":")
    if prefix.lower() != "agent" or not separator:
        return None
    agent_id, separator, tail = remainder.partition(":")
    if not separator or not agent_id.strip() or not tail.strip():
        raise OpenClawConfigurationError(
            f"Malformed agent-scoped OpenClaw session key '{session_key}'"
        )
    return AgentScopedSessionKeyParts(
        original=normalized,
        agent_id=agent_id.strip(),
        remainder=tail.strip(),
    )


__all__ = [
    "AgentScopedSessionKeyParts",
    "normalize_agent_launch_input",
    "normalize_openclaw_agent_id",
    "normalize_transport_session_key",
    "parse_agent_scoped_openclaw_session_key",
]
