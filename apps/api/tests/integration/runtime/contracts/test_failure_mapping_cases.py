from __future__ import annotations

from typing import cast

import pytest
from autoclaw.interfaces.http.contracts.operation_failure import OperationFailureCode
from autoclaw.interfaces.http.errors import runtime_exception_failure
from autoclaw.runtime.errors import (
    boundary_precondition_error,
    budget_exhausted_error,
    illegal_caller_error,
    illegal_state_error,
    missing_required_publication_error,
    missing_resource_error,
    semantic_missing_resource_error,
    stale_assignment_error,
    stale_checkpoint_error,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]

@pytest.mark.parametrize(
    ("exc", "expected_summary"),
    [
        (
            semantic_missing_resource_error("missing artifact provider for slot 'brief'"),
            "missing artifact provider for slot 'brief'",
        ),
        (
            semantic_missing_resource_error("missing current artifact for slot 'brief'"),
            "missing current artifact for slot 'brief'",
        ),
        (
            semantic_missing_resource_error("produced artifact does not exist: /tmp/missing.txt"),
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
    assert failure.is_retryable is False


def test_runtime_exception_failure_maps_missing_required_publication_to_422() -> None:
    summary = "missing required publication for slot 'brief'"

    status_code, failure = runtime_exception_failure(missing_required_publication_error(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_REQUIRED_PUBLICATION
    assert failure.summary == summary
    assert failure.is_retryable is False


def test_runtime_exception_failure_keeps_unknown_target_ids_on_404() -> None:
    status_code, failure = runtime_exception_failure(
        missing_resource_error("unknown task_id 'task-1'")
    )

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
    typed_exc = (
        stale_assignment_error(summary)
        if expected_code == OperationFailureCode.STALE_ASSIGNMENT
        else stale_checkpoint_error(summary)
    )
    status_code, failure = runtime_exception_failure(typed_exc)

    assert status_code == 409
    assert failure.code == expected_code
    assert failure.summary == summary
    assert failure.is_retryable is True
    assert failure.suggested_next_step == expected_next_step


def test_runtime_exception_failure_keeps_missing_required_publication_on_422() -> None:
    summary = "missing required publication for assignment 'assign.task.root.01'"

    status_code, failure = runtime_exception_failure(missing_required_publication_error(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_REQUIRED_PUBLICATION
    assert failure.summary == summary
    assert failure.is_retryable is False


def test_runtime_exception_failure_keeps_non_stale_invalid_requests_on_422() -> None:
    summary = "release_blocked requires the current root basis to be terminal-blocked"

    status_code, failure = runtime_exception_failure(missing_required_publication_error(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.MISSING_REQUIRED_PUBLICATION
    assert failure.summary == summary
    assert failure.is_retryable is False
    assert failure.suggested_next_step == (
        "Publish or republish the missing durable or surfaced release basis first, "
        "then retry the control action or reread the surfaced release inputs."
    )


def test_runtime_exception_failure_maps_budget_exhausted_to_422() -> None:
    summary = "child assignment budget exhausted for this path"

    status_code, failure = runtime_exception_failure(budget_exhausted_error(summary))

    assert status_code == 422
    assert failure.code == OperationFailureCode.BUDGET_EXHAUSTED
    assert failure.summary == summary
    assert failure.is_retryable is False
    assert failure.suggested_next_step == (
        "Surface the latest terminal checkpoint to the relevant parent or root so it can "
        "choose a fresh assignment or another legal path."
    )


def test_runtime_exception_failure_keeps_typed_parent_retry_failure() -> None:
    status_code, failure = runtime_exception_failure(
        illegal_caller_error("parent/root retry is illegal")
    )

    assert status_code == 422
    assert failure.code == OperationFailureCode.ILLEGAL_CALLER
    assert failure.summary == "parent/root retry is illegal"
    assert failure.is_retryable is False


def test_runtime_exception_failure_keeps_typed_yield_release_failure() -> None:
    status_code, failure = runtime_exception_failure(
        boundary_precondition_error(
            "yield is illegal after terminal release basis was committed",
            suggested_next_step=(
                "If this dispatch should stay non-terminal, stage exactly one child "
                "assignment first, publish a progress checkpoint if later readers need "
                "the reasoning, then emit `yield`. If the committed basis is "
                "`release_green` or root `release_blocked`, close with the matching "
                "terminal boundary instead."
            ),
        )
    )

    assert status_code == 422
    assert failure.code == OperationFailureCode.BOUNDARY_PRECONDITION_FAILED
    assert failure.summary == "yield is illegal after terminal release basis was committed"
    assert failure.is_retryable is False
    assert "close with the matching terminal boundary instead" in cast(
        str, failure.suggested_next_step
    )


def test_runtime_exception_failure_keeps_typed_current_semantic_target_continue_failure() -> None:
    status_code, failure = runtime_exception_failure(
        illegal_state_error(
            "current semantic target is incomplete",
            suggested_next_step=(
                "Inspect the current node assignment and attempt currentness, then repair "
                "the incomplete semantic target before continuing this task."
            ),
        )
    )

    assert status_code == 422
    assert failure.code == OperationFailureCode.ILLEGAL_STATE
    assert failure.summary == "current semantic target is incomplete"
    assert failure.is_retryable is False
    assert failure.suggested_next_step == (
        "Inspect the current node assignment and attempt currentness, then repair the "
        "incomplete semantic target before continuing this task."
    )


def test_runtime_exception_failure_normalizes_incomplete_yield_continuation_to_illegal_state() -> (
    None
):
    status_code, failure = runtime_exception_failure(
        missing_resource_error(
            "yield continuation basis is incomplete",
            suggested_next_step=(
                "Reread the staged child assignment and child attempt basis, then repair "
                "or restage a complete child continuation before emitting `yield` again."
            ),
        )
    )

    assert status_code == 422
    assert failure.code == OperationFailureCode.ILLEGAL_STATE
    assert failure.summary == "staged child assignment is incomplete"
    assert failure.is_retryable is False
    assert failure.suggested_next_step == (
        "Inspect the current yielded dispatch and staged child assignment, then repair "
        "or restage a complete child continuation before continuing this task."
    )


def test_runtime_exception_failure_treats_untyped_value_error_as_internal_error() -> None:
    status_code, failure = runtime_exception_failure(ValueError("unexpected runtime failure"))

    assert status_code == 500
    assert failure.code == OperationFailureCode.INTERNAL_ERROR
    assert failure.summary == "unexpected runtime failure"
    assert failure.is_retryable is False


__all__ = [
    "test_runtime_exception_failure_keeps_missing_required_publication_on_422",
    "test_runtime_exception_failure_keeps_non_stale_invalid_requests_on_422",
    "test_runtime_exception_failure_keeps_typed_current_semantic_target_continue_failure",
    "test_runtime_exception_failure_keeps_typed_parent_retry_failure",
    "test_runtime_exception_failure_keeps_typed_yield_release_failure",
    "test_runtime_exception_failure_keeps_unknown_target_ids_on_404",
    "test_runtime_exception_failure_maps_budget_exhausted_to_422",
    "test_runtime_exception_failure_maps_missing_required_publication_to_422",
    "test_runtime_exception_failure_maps_semantic_missing_dependencies_to_422",
    "test_runtime_exception_failure_maps_stale_runtime_basis_to_409",
    "test_runtime_exception_failure_normalizes_incomplete_yield_continuation_to_illegal_state",
    "test_runtime_exception_failure_treats_untyped_value_error_as_internal_error",
]
