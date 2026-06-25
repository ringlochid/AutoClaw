from __future__ import annotations

from enum import StrEnum


class OperationFailureCode(StrEnum):
    INVALID_REQUEST_SHAPE = "invalid_request_shape"
    ILLEGAL_CALLER = "illegal_caller"
    ILLEGAL_TARGET_RELATION = "illegal_target_relation"
    ILLEGAL_STATE = "illegal_state"
    STALE_DISPATCH = "stale_dispatch"
    STALE_FLOW_REVISION = "stale_flow_revision"
    STALE_ASSIGNMENT = "stale_assignment"
    STALE_CHECKPOINT = "stale_checkpoint"
    MISSING_RESOURCE = "missing_resource"
    MISSING_REQUIRED_PUBLICATION = "missing_required_publication"
    CONFLICTING_CONTINUATION = "conflicting_continuation"
    CURSOR_RESET_REQUIRED = "cursor_reset_required"
    BOUNDARY_PRECONDITION_FAILED = "boundary_precondition_failed"
    CAPABILITY_REJECTED = "capability_rejected"
    REMOVED_SURFACE = "removed_surface"
    BUDGET_EXHAUSTED = "budget_exhausted"
    INTERNAL_ERROR = "internal_error"


__all__ = ["OperationFailureCode"]
