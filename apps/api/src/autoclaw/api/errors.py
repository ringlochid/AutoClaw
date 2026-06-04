from __future__ import annotations

from typing import NoReturn, cast

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

import autoclaw.api.runtime_exception_mapping as runtime_exception_mapping
from autoclaw.schemas.operation_failure import OperationFailure, OperationFailureCode

_RETRYABILITY_FLAG_UNSET = object()


def raise_operation_failure(
    *,
    status_code: int,
    code: OperationFailureCode,
    summary: str,
    is_retryable: bool | None = None,
    field_path: str | None = None,
    suggested_next_step: str | None = None,
    **compat_kwargs: object,
) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail=operation_failure(
            code=code,
            summary=summary,
            is_retryable=is_retryable,
            field_path=field_path,
            suggested_next_step=suggested_next_step,
            **compat_kwargs,
        ).model_dump(mode="json"),
    )


def request_validation_failure(exc: RequestValidationError) -> OperationFailure:
    first_error = exc.errors()[0] if exc.errors() else {}
    loc = first_error.get("loc", ())
    field_path = ".".join(str(part) for part in loc if part != "body") or None
    return operation_failure(
        code=OperationFailureCode.INVALID_REQUEST_SHAPE,
        summary="request shape does not match the canonical runtime surface",
        is_retryable=False,
        field_path=field_path,
        suggested_next_step=(
            "Reread the canonical request shape and resend the request with only the live "
            "required fields."
        ),
    )


def runtime_exception_failure(exc: Exception) -> tuple[int, OperationFailure]:
    return runtime_exception_mapping.runtime_exception_failure(exc)


def raise_runtime_exception(exc: Exception) -> NoReturn:
    runtime_exception_mapping.raise_runtime_exception(exc)


def operation_failure(
    *,
    code: OperationFailureCode,
    summary: str,
    is_retryable: bool | None = None,
    field_path: str | None = None,
    suggested_next_step: str | None = None,
    **compat_kwargs: object,
) -> OperationFailure:
    return OperationFailure.model_validate(
        {
            "code": code,
            "summary": summary,
            "retryable": _resolve_retryability(
                is_retryable=is_retryable,
                compat_kwargs=compat_kwargs,
            ),
            "field_path": field_path,
            "suggested_next_step": suggested_next_step,
        }
    )


def _resolve_retryability(
    *,
    is_retryable: bool | None,
    compat_kwargs: dict[str, object],
) -> bool:
    legacy_retryable = compat_kwargs.pop("retryable", _RETRYABILITY_FLAG_UNSET)
    if compat_kwargs:
        unexpected_arguments = ", ".join(sorted(compat_kwargs))
        raise TypeError(
            f"operation_failure() got unexpected keyword argument(s): {unexpected_arguments}"
        )
    if legacy_retryable is _RETRYABILITY_FLAG_UNSET:
        if is_retryable is None:
            raise TypeError("operation_failure() missing required keyword argument: 'is_retryable'")
        return is_retryable
    if is_retryable is not None:
        raise TypeError("operation_failure() received both 'is_retryable' and legacy 'retryable'")
    return cast(bool, legacy_retryable)
