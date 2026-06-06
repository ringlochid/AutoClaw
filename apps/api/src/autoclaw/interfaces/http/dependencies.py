from __future__ import annotations

from typing import Annotated

from fastapi import Header, status

from autoclaw.config import get_settings
from autoclaw.interfaces.http.errors import raise_operation_failure
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode


def require_api_key(
    api_key: Annotated[str | None, Header(alias="X-AutoClaw-API-Key")] = None,
) -> None:
    _require_exact_api_key(provided_key=api_key, expected_key=get_settings().api_key)


def require_internal_api_key(
    api_key: Annotated[str | None, Header(alias="X-AutoClaw-API-Key")] = None,
) -> None:
    _require_exact_api_key(provided_key=api_key, expected_key=get_settings().internal_api_key)


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
            is_retryable=False,
            suggested_next_step="Provide the configured X-AutoClaw-API-Key header.",
        )
