from __future__ import annotations

from typing import Annotated

from fastapi import Header, status

from app.api.errors import raise_operation_failure
from app.config import get_settings
from app.schemas.operation_failure import OperationFailureCode


def _require_exact_api_key(
    *,
    provided_key: str | None,
    expected_key: str,
) -> None:
    if provided_key != expected_key:
        raise_operation_failure(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=OperationFailureCode.ILLEGAL_CALLER,
            summary="missing or invalid API key",
            retryable=False,
            suggested_next_step="Provide the configured X-AutoClaw-API-Key header.",
        )


def require_api_key(
    api_key: Annotated[str | None, Header(alias="X-AutoClaw-API-Key")] = None,
) -> None:
    _require_exact_api_key(provided_key=api_key, expected_key=get_settings().api_key)


def require_internal_api_key(
    api_key: Annotated[str | None, Header(alias="X-AutoClaw-API-Key")] = None,
) -> None:
    _require_exact_api_key(provided_key=api_key, expected_key=get_settings().internal_api_key)
