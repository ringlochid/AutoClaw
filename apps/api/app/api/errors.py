from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError

from app.schemas.operation_failure import OperationFailure, OperationFailureCode


def operation_failure(
    *,
    code: OperationFailureCode,
    summary: str,
    retryable: bool,
    field_path: str | None = None,
    suggested_next_step: str | None = None,
) -> OperationFailure:
    return OperationFailure(
        code=code,
        summary=summary,
        retryable=retryable,
        field_path=field_path,
        suggested_next_step=suggested_next_step,
    )


def raise_operation_failure(
    *,
    status_code: int,
    code: OperationFailureCode,
    summary: str,
    retryable: bool,
    field_path: str | None = None,
    suggested_next_step: str | None = None,
) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail=operation_failure(
            code=code,
            summary=summary,
            retryable=retryable,
            field_path=field_path,
            suggested_next_step=suggested_next_step,
        ).model_dump(mode="json"),
    )


def request_validation_failure(exc: RequestValidationError) -> OperationFailure:
    first_error = exc.errors()[0] if exc.errors() else {}
    loc = first_error.get("loc", ())
    field_path = ".".join(str(part) for part in loc if part != "body") or None
    return operation_failure(
        code=OperationFailureCode.INVALID_REQUEST_SHAPE,
        summary="request shape does not match the canonical runtime surface",
        retryable=False,
        field_path=field_path,
        suggested_next_step=(
            "Reread the canonical request shape and resend the request with only the live "
            "required fields."
        ),
    )


def _runtime_failure(
    *,
    status_code: int,
    code: OperationFailureCode,
    summary: str,
    retryable: bool,
    suggested_next_step: str | None,
) -> tuple[int, OperationFailure]:
    return status_code, operation_failure(
        code=code,
        summary=summary,
        retryable=retryable,
        suggested_next_step=suggested_next_step,
    )


def runtime_exception_failure(exc: Exception) -> tuple[int, OperationFailure]:
    summary = str(exc)
    if summary.startswith("cursor must "):
        return _runtime_failure(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=OperationFailureCode.INVALID_REQUEST_SHAPE,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Reread the current query parameter contract and resend the request with a "
                "non-negative integer cursor."
            ),
        )
    if summary == "invalid callback session key":
        return _runtime_failure(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=OperationFailureCode.ILLEGAL_CALLER,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Reread the current live callback binding and resend the request with the "
                "bound X-Autoclaw-Session-Key for the open dispatch."
            ),
        )
    if summary == "stale callback session key":
        return _runtime_failure(
            status_code=status.HTTP_409_CONFLICT,
            code=OperationFailureCode.STALE_DISPATCH,
            summary=summary,
            retryable=True,
            suggested_next_step=(
                "Reread the current dispatch context and callback binding, then retry only "
                "if this node is still the current caller for an open dispatch."
            ),
        )
    if summary == "inactive callback session key":
        return _runtime_failure(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=OperationFailureCode.ILLEGAL_STATE,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Reread the current runtime status and dispatch context, then use the "
                "operator lane to resume or inspect the task before sending more callback "
                "writes."
            ),
        )
    if "stale structural revision" in summary or "stale active flow revision" in summary:
        return _runtime_failure(
            status_code=status.HTTP_409_CONFLICT,
            code=OperationFailureCode.STALE_FLOW_REVISION,
            summary=summary,
            retryable=True,
            suggested_next_step=(
                "Reread the regenerated workflow manifest and current structural revision, "
                "then rebuild the request against that newer structure."
            ),
        )
    if "worker nodes cannot" in summary or "root-only" in summary:
        return _runtime_failure(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=OperationFailureCode.ILLEGAL_CALLER,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Reread the current dispatch context and use only the tools or boundaries "
                "legal for this node and this open dispatch."
            ),
        )
    if "direct child" in summary or "target must be" in summary:
        return _runtime_failure(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=OperationFailureCode.ILLEGAL_TARGET_RELATION,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Reread the current workflow manifest and direct-child set, then target "
                "only a current direct child or choose a different legal action."
            ),
        )
    if "staged child assignment" in summary:
        return _runtime_failure(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=OperationFailureCode.CONFLICTING_CONTINUATION,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Publish a progress checkpoint if later readers need the reasoning, then "
                "close with the matching boundary instead of staging another outcome."
            ),
        )
    if (
        summary.startswith("missing required publication")
        or summary.startswith("missing required published artifact")
        or summary.endswith("requires current surfaced evidence")
    ):
        return _runtime_failure(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=OperationFailureCode.MISSING_REQUIRED_PUBLICATION,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Publish or republish the missing durable or surfaced release basis first, "
                "then retry the control action or reread the surfaced release inputs."
            ),
        )
    if (
        summary.startswith("yield requires")
        or "terminal boundaries require" in summary
        or "boundary does not match" in summary
        or summary.startswith("green requires")
        or summary.startswith("blocked requires")
    ):
        return _runtime_failure(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=OperationFailureCode.BOUNDARY_PRECONDITION_FAILED,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Reread the current checkpoint, release basis, and staged continuation "
                "state, then publish or commit the missing prerequisite before retrying "
                "the boundary."
            ),
        )
    if (
        summary.startswith("missing current artifact")
        or summary.startswith("missing criteria provider")
        or summary.startswith("missing supplemental artifact")
        or summary.startswith("missing supplemental criteria")
    ):
        return _runtime_failure(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=OperationFailureCode.MISSING_RESOURCE,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Reread the current manifest, assignment, and surfaced refs, then stage or "
                "publish the missing dependency basis before retrying this request."
            ),
        )
    if summary.startswith("missing parent node"):
        return _runtime_failure(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=OperationFailureCode.ILLEGAL_TARGET_RELATION,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Reread the current workflow manifest and target only the current node or, "
                "for root, an existing descendant parent."
            ),
        )
    if (
        isinstance(exc, FileNotFoundError)
        or summary == "task has no dispatch history"
        or summary.startswith("unknown ")
        or summary.startswith("missing ")
    ):
        return _runtime_failure(
            status_code=status.HTTP_404_NOT_FOUND,
            code=OperationFailureCode.MISSING_RESOURCE,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Verify the task, flow, or dispatch id and reread the current runtime "
                "surface before retrying this request."
            ),
        )
    if isinstance(exc, ValueError):
        return _runtime_failure(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=OperationFailureCode.ILLEGAL_STATE,
            summary=summary,
            retryable=False,
            suggested_next_step=(
                "Reread the current manifest, assignment, checkpoint, and surfaced refs, "
                "then choose a tool or boundary that matches the current state."
            ),
        )
    return _runtime_failure(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=OperationFailureCode.INTERNAL_ERROR,
        summary=summary,
        retryable=False,
        suggested_next_step=(
            "Do not invent new runtime truth locally; surface the failure for operator or "
            "controller recovery and reread current runtime state before retrying."
        ),
    )


def raise_runtime_exception(exc: Exception) -> NoReturn:
    status_code, failure = runtime_exception_failure(exc)
    raise HTTPException(
        status_code=status_code,
        detail=failure.model_dump(mode="json"),
    ) from exc
