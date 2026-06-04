"""Explicit Phase 6 bridge for the legacy runtime-control failure owner."""

from __future__ import annotations

from app.runtime.control import failures as legacy_failures

BOUNDARY_PRECONDITION_NEXT_STEP = legacy_failures.BOUNDARY_PRECONDITION_NEXT_STEP
BUDGET_EXHAUSTED_NEXT_STEP = legacy_failures.BUDGET_EXHAUSTED_NEXT_STEP
CONFLICTING_CONTINUATION_NEXT_STEP = legacy_failures.CONFLICTING_CONTINUATION_NEXT_STEP
ILLEGAL_CALLER_NEXT_STEP = legacy_failures.ILLEGAL_CALLER_NEXT_STEP
ILLEGAL_STATE_NEXT_STEP = legacy_failures.ILLEGAL_STATE_NEXT_STEP
ILLEGAL_TARGET_RELATION_NEXT_STEP = legacy_failures.ILLEGAL_TARGET_RELATION_NEXT_STEP
INVALID_REQUEST_SHAPE_NEXT_STEP = legacy_failures.INVALID_REQUEST_SHAPE_NEXT_STEP
MISSING_REQUIRED_PUBLICATION_NEXT_STEP = legacy_failures.MISSING_REQUIRED_PUBLICATION_NEXT_STEP
MISSING_RESOURCE_NEXT_STEP = legacy_failures.MISSING_RESOURCE_NEXT_STEP
SEMANTIC_MISSING_RESOURCE_NEXT_STEP = legacy_failures.SEMANTIC_MISSING_RESOURCE_NEXT_STEP
STALE_ASSIGNMENT_NEXT_STEP = legacy_failures.STALE_ASSIGNMENT_NEXT_STEP
STALE_CHECKPOINT_NEXT_STEP = legacy_failures.STALE_CHECKPOINT_NEXT_STEP
STALE_DISPATCH_NEXT_STEP = legacy_failures.STALE_DISPATCH_NEXT_STEP
STALE_FLOW_REVISION_NEXT_STEP = legacy_failures.STALE_FLOW_REVISION_NEXT_STEP
RuntimeOperationError = legacy_failures.RuntimeOperationError
boundary_precondition_error = legacy_failures.boundary_precondition_error
budget_exhausted_error = legacy_failures.budget_exhausted_error
conflicting_continuation_error = legacy_failures.conflicting_continuation_error
illegal_caller_error = legacy_failures.illegal_caller_error
illegal_state_error = legacy_failures.illegal_state_error
illegal_target_relation_error = legacy_failures.illegal_target_relation_error
invalid_request_shape_error = legacy_failures.invalid_request_shape_error
missing_required_publication_error = legacy_failures.missing_required_publication_error
missing_resource_error = legacy_failures.missing_resource_error
semantic_missing_resource_error = legacy_failures.semantic_missing_resource_error
stale_assignment_error = legacy_failures.stale_assignment_error
stale_checkpoint_error = legacy_failures.stale_checkpoint_error
stale_dispatch_error = legacy_failures.stale_dispatch_error
stale_flow_revision_error = legacy_failures.stale_flow_revision_error

__all__ = [
    "BOUNDARY_PRECONDITION_NEXT_STEP",
    "BUDGET_EXHAUSTED_NEXT_STEP",
    "CONFLICTING_CONTINUATION_NEXT_STEP",
    "ILLEGAL_CALLER_NEXT_STEP",
    "ILLEGAL_STATE_NEXT_STEP",
    "ILLEGAL_TARGET_RELATION_NEXT_STEP",
    "INVALID_REQUEST_SHAPE_NEXT_STEP",
    "MISSING_REQUIRED_PUBLICATION_NEXT_STEP",
    "MISSING_RESOURCE_NEXT_STEP",
    "SEMANTIC_MISSING_RESOURCE_NEXT_STEP",
    "STALE_ASSIGNMENT_NEXT_STEP",
    "STALE_CHECKPOINT_NEXT_STEP",
    "STALE_DISPATCH_NEXT_STEP",
    "STALE_FLOW_REVISION_NEXT_STEP",
    "RuntimeOperationError",
    "boundary_precondition_error",
    "budget_exhausted_error",
    "conflicting_continuation_error",
    "illegal_caller_error",
    "illegal_state_error",
    "illegal_target_relation_error",
    "invalid_request_shape_error",
    "missing_required_publication_error",
    "missing_resource_error",
    "semantic_missing_resource_error",
    "stale_assignment_error",
    "stale_checkpoint_error",
    "stale_dispatch_error",
    "stale_flow_revision_error",
]
