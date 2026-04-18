from __future__ import annotations

from app.api.deps import (
    API_KEY_HEADER,
    AUTOCLAW_ACTOR_HEADER,
    AUTOCLAW_REASON_HEADER,
    AUTOCLAW_SOURCE_AGENT_HEADER,
    AUTOCLAW_SOURCE_NODE_ATTEMPT_HEADER,
    AUTOCLAW_SOURCE_SESSION_HEADER,
)
from app.config import get_settings


def public_api_key_headers() -> dict[str, str]:
    return {API_KEY_HEADER: get_settings().api_key}


def operator_api_key_headers() -> dict[str, str]:
    return public_api_key_headers()


def internal_api_key_headers() -> dict[str, str]:
    return {API_KEY_HEADER: get_settings().internal_api_key}


def definition_write_audit_headers(
    *,
    requested_by: str,
    source_session: str | None = None,
    source_agent: str | None = None,
    source_node_attempt: str | None = None,
    reason: str | None = None,
) -> dict[str, str]:
    headers = {AUTOCLAW_ACTOR_HEADER: requested_by}
    if source_session is not None:
        headers[AUTOCLAW_SOURCE_SESSION_HEADER] = source_session
    if source_agent is not None:
        headers[AUTOCLAW_SOURCE_AGENT_HEADER] = source_agent
    if source_node_attempt is not None:
        headers[AUTOCLAW_SOURCE_NODE_ATTEMPT_HEADER] = source_node_attempt
    if reason is not None:
        headers[AUTOCLAW_REASON_HEADER] = reason
    return headers
