from __future__ import annotations

from typing import Annotated

from fastapi import Header, status
from fastapi.exceptions import RequestValidationError

from autoclaw.config import get_settings
from autoclaw.interfaces.http.errors import raise_operation_failure
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode

_CONTROL_ACTOR_REF_HEADER_NAME = "X-AutoClaw-Actor-Ref"
_CONTROL_ACTOR_REF_MAX_LENGTH = 255


def require_api_key(
    api_key: Annotated[str | None, Header(alias="X-AutoClaw-API-Key")] = None,
) -> None:
    _require_exact_api_key(provided_key=api_key, expected_key=get_settings().api_key)


def read_control_actor_ref(
    actor_ref: Annotated[str | None, Header(alias=_CONTROL_ACTOR_REF_HEADER_NAME)] = None,
) -> str | None:
    normalized_actor_ref = _normalize_optional_header(actor_ref)
    _validate_control_actor_ref_length(normalized_actor_ref)
    return normalized_actor_ref


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


def _normalize_optional_header(header_value: str | None) -> str | None:
    normalized_value = None if header_value is None else header_value.strip()
    return normalized_value or None


def _validate_control_actor_ref_length(actor_ref: str | None) -> None:
    # Validate the trimmed value so the HTTP cap matches the persisted VARCHAR(255) fields.
    if actor_ref is None or len(actor_ref) <= _CONTROL_ACTOR_REF_MAX_LENGTH:
        return
    raise RequestValidationError(
        [
            {
                "type": "string_too_long",
                "loc": ("header", _CONTROL_ACTOR_REF_HEADER_NAME),
                "msg": (
                    "String should have at most "
                    f"{_CONTROL_ACTOR_REF_MAX_LENGTH} characters after trimming whitespace"
                ),
                "input": actor_ref,
                "ctx": {"max_length": _CONTROL_ACTOR_REF_MAX_LENGTH},
            }
        ]
    )
