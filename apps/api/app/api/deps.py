import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db_session
from app.registry.audit import DefinitionWriteAudit, build_definition_write_audit

API_KEY_HEADER = "X-AutoClaw-API-Key"
AUTOCLAW_ACTOR_HEADER = "X-AutoClaw-Actor"
AUTOCLAW_SOURCE_SESSION_HEADER = "X-AutoClaw-Source-Session"
AUTOCLAW_SOURCE_AGENT_HEADER = "X-AutoClaw-Source-Agent"
AUTOCLAW_SOURCE_NODE_ATTEMPT_HEADER = "X-AutoClaw-Source-Node-Attempt"
AUTOCLAW_REASON_HEADER = "X-AutoClaw-Reason"
api_key_header = APIKeyHeader(
    name=API_KEY_HEADER,
    scheme_name="AutoClawApiKey",
    auto_error=False,
)

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _matches_api_key(provided_key: str | None, *expected_keys: str) -> bool:
    if provided_key is None:
        return False
    return any(secrets.compare_digest(provided_key, expected_key) for expected_key in expected_keys)


async def require_api_key(
    x_autoclaw_api_key: Annotated[str | None, Security(api_key_header)] = None,
) -> None:
    settings = get_settings()
    if not _matches_api_key(
        x_autoclaw_api_key,
        settings.api_key,
        settings.internal_api_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )


async def require_internal_api_key(
    x_autoclaw_api_key: Annotated[str | None, Security(api_key_header)] = None,
) -> None:
    if not _matches_api_key(x_autoclaw_api_key, get_settings().internal_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )


async def get_definition_write_audit(
    x_autoclaw_actor: Annotated[str | None, Header(alias=AUTOCLAW_ACTOR_HEADER)] = None,
    x_autoclaw_source_session: Annotated[
        str | None, Header(alias=AUTOCLAW_SOURCE_SESSION_HEADER)
    ] = None,
    x_autoclaw_source_agent: Annotated[
        str | None, Header(alias=AUTOCLAW_SOURCE_AGENT_HEADER)
    ] = None,
    x_autoclaw_source_node_attempt: Annotated[
        str | None, Header(alias=AUTOCLAW_SOURCE_NODE_ATTEMPT_HEADER)
    ] = None,
    x_autoclaw_reason: Annotated[str | None, Header(alias=AUTOCLAW_REASON_HEADER)] = None,
) -> DefinitionWriteAudit | None:
    return build_definition_write_audit(
        requested_by=x_autoclaw_actor,
        source_session=x_autoclaw_source_session,
        source_agent=x_autoclaw_source_agent,
        source_node_attempt=x_autoclaw_source_node_attempt,
        reason=x_autoclaw_reason,
    )
