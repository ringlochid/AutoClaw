from __future__ import annotations

import pytest
from app.api.errors import runtime_exception_failure
from app.schemas.operation_failure import OperationFailureCode


@pytest.mark.parametrize(
    ("exc", "expected_summary"),
    [
        (
            ValueError("missing artifact provider for slot 'brief'"),
            "missing artifact provider for slot 'brief'",
        ),
        (
            ValueError("missing current artifact for slot 'brief'"),
            "missing current artifact for slot 'brief'",
        ),
        (
            FileNotFoundError("produced artifact does not exist: /tmp/missing.txt"),
            "produced artifact does not exist: /tmp/missing.txt",
        ),
    ],
)
def test_runtime_exception_failure_maps_semantic_missing_dependencies_to_422(
    exc: Exception,
    expected_summary: str,
) -> None:
    status_code, failure = runtime_exception_failure(exc)

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_RESOURCE
    assert failure.summary == expected_summary
    assert failure.retryable is False


def test_runtime_exception_failure_maps_missing_required_publication_to_422() -> None:
    summary = "missing required publication for slot 'brief'"

    status_code, failure = runtime_exception_failure(ValueError(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_REQUIRED_PUBLICATION
    assert failure.summary == summary
    assert failure.retryable is False


def test_runtime_exception_failure_keeps_unknown_target_ids_on_404() -> None:
    status_code, failure = runtime_exception_failure(ValueError("unknown task_id 'task-1'"))

    assert status_code == 404
    assert failure.code == OperationFailureCode.MISSING_RESOURCE
    assert failure.summary == "unknown task_id 'task-1'"


@pytest.mark.parametrize(
    ("summary", "expected_code", "expected_next_step"),
    [
        (
            "green release precondition is stale",
            OperationFailureCode.STALE_ASSIGNMENT,
            "Reread the current assignment projection and resend the request only if the "
            "same assignment is still current.",
        ),
        (
            "blocked release precondition is stale",
            OperationFailureCode.STALE_ASSIGNMENT,
            "Reread the current assignment projection and resend the request only if the "
            "same assignment is still current.",
        ),
        (
            (
                "release_green requires current surfaced evidence: "
                "missing current artifact for slot 'brief'"
            ),
            OperationFailureCode.STALE_CHECKPOINT,
            "Reread the latest relevant checkpoint and current surfaced refs, then decide "
            "again from that newer handover.",
        ),
        (
            (
                "release_blocked requires current checkpoint evidence: "
                "current checkpoint projection files are missing"
            ),
            OperationFailureCode.STALE_CHECKPOINT,
            "Reread the latest relevant checkpoint and current surfaced refs, then decide "
            "again from that newer handover.",
        ),
    ],
)
def test_runtime_exception_failure_maps_stale_runtime_basis_to_409(
    summary: str,
    expected_code: OperationFailureCode,
    expected_next_step: str,
) -> None:
    status_code, failure = runtime_exception_failure(ValueError(summary))

    assert status_code == 409
    assert failure.code == expected_code
    assert failure.summary == summary
    assert failure.retryable is True
    assert failure.suggested_next_step == expected_next_step


def test_runtime_exception_failure_keeps_missing_required_publication_on_422() -> None:
    summary = "missing required publication for assignment 'assign.task.root.01'"

    status_code, failure = runtime_exception_failure(ValueError(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_REQUIRED_PUBLICATION
    assert failure.summary == summary
    assert failure.retryable is False


def test_runtime_exception_failure_keeps_non_stale_invalid_requests_on_422() -> None:
    summary = "release_blocked requires the current root basis to be terminal-blocked"

    status_code, failure = runtime_exception_failure(ValueError(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_REQUIRED_PUBLICATION
    assert failure.summary == summary
    assert failure.retryable is False
    assert failure.suggested_next_step == (
        "Publish the blocked checkpoint and any required blocked-basis evidence first, "
        "then retry release_blocked."
    )


def test_runtime_exception_failure_maps_budget_exhausted_to_422() -> None:
    summary = "child assignment budget exhausted for this path"

    status_code, failure = runtime_exception_failure(ValueError(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.BUDGET_EXHAUSTED
    assert failure.summary == summary
    assert failure.retryable is False
    assert failure.suggested_next_step == (
        "Surface the latest terminal checkpoint to the relevant parent or root so it can "
        "choose a fresh assignment or another legal path."
    )


__all__ = [
    "test_runtime_exception_failure_keeps_missing_required_publication_on_422",
    "test_runtime_exception_failure_keeps_non_stale_invalid_requests_on_422",
    "test_runtime_exception_failure_keeps_unknown_target_ids_on_404",
    "test_runtime_exception_failure_maps_budget_exhausted_to_422",
    "test_runtime_exception_failure_maps_missing_required_publication_to_422",
    "test_runtime_exception_failure_maps_semantic_missing_dependencies_to_422",
    "test_runtime_exception_failure_maps_stale_runtime_basis_to_409",
]
