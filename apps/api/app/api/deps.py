import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db_session

API_KEY_HEADER = "X-AutoClaw-API-Key"
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
