from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


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
    BOUNDARY_PRECONDITION_FAILED = "boundary_precondition_failed"
    REMOVED_SURFACE = "removed_surface"
    INTERNAL_ERROR = "internal_error"


class OperationFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: Literal[False] = False
    code: OperationFailureCode
    summary: str
    retryable: bool
    field_path: str | None = None
    suggested_next_step: str | None = None
