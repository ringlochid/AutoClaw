from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from autoclaw.schemas.runtime.common import RuntimeSchemaText
from autoclaw.schemas.runtime.contracts import (
    CheckpointKind,
    CheckpointOutcome,
    DispatchDeliveryStatus,
    EgressBoundary,
)
from autoclaw.schemas.runtime.flow import RuntimeFlowRead
from autoclaw.schemas.runtime.refs import (
    ArtifactIndexRef,
    ArtifactRef,
    AssignmentFileRef,
    CheckpointFileRef,
    CriteriaRef,
    DocRef,
    OperatorSupportSurfaceRef,
    SupportRuntimeFileRef,
    TransientIndexRef,
    TransientRef,
    WikiRef,
    WorkflowManifestRef,
)

type OperatorSupportSurfaceCarrier = (
    OperatorSupportSurfaceRef
    | WorkflowManifestRef
    | AssignmentFileRef
    | CheckpointFileRef
    | ArtifactIndexRef
    | TransientIndexRef
    | SupportRuntimeFileRef
    | ArtifactRef
    | CriteriaRef
    | DocRef
    | WikiRef
    | TransientRef
)


type OperatorCurrentPaths = Annotated[
    tuple[OperatorSupportSurfaceRef, ...],
    BeforeValidator(lambda current_paths: _normalize_current_paths(current_paths)),
]


class TopActionableItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    summary: RuntimeSchemaText
    node_key: RuntimeSchemaText | None = None
    current_paths: OperatorCurrentPaths = ()
    suggested_action: RuntimeSchemaText | None = None


class OperatorFlowSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    flow: RuntimeFlowRead
    top_actionable_items: tuple[TopActionableItem, ...]
    current_paths: OperatorCurrentPaths = ()


class DispatchHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    attempt_id: RuntimeSchemaText
    assignment_key: RuntimeSchemaText | None = None
    node_key: RuntimeSchemaText
    delivery_status: DispatchDeliveryStatus
    rendered_at: datetime


class CheckpointHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    checkpoint_id: RuntimeSchemaText
    attempt_id: RuntimeSchemaText
    checkpoint_kind: CheckpointKind
    outcome: CheckpointOutcome | None = None
    summary: RuntimeSchemaText
    recorded_at: datetime


class BoundaryHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    node_key: RuntimeSchemaText
    boundary: EgressBoundary
    occurred_at: datetime


class OperatorFlowTraceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    task_id: RuntimeSchemaText
    scope: Literal["current", "whole"] = "current"
    dispatch_history: tuple[DispatchHistoryEntry, ...]
    checkpoint_history: tuple[CheckpointHistoryEntry, ...]
    boundary_history: tuple[BoundaryHistoryEntry, ...]
    current_paths: OperatorCurrentPaths = ()
    next_cursor: RuntimeSchemaText | None = None


class OperatorFlowTraceQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: Literal["current", "whole"] = "current"
    q: RuntimeSchemaText | None = None
    limit: int = Field(default=50, ge=1, le=200)
    cursor: RuntimeSchemaText | None = None
    sort: Literal["occurred_at_desc", "occurred_at_asc"] = "occurred_at_desc"


def _normalize_current_paths(
    current_paths: Any,
) -> tuple[OperatorSupportSurfaceRef, ...]:
    if current_paths in (None, ()):
        return ()
    return tuple(OperatorSupportSurfaceRef.model_validate(path) for path in current_paths)


__all__ = [
    "BoundaryHistoryEntry",
    "CheckpointHistoryEntry",
    "DispatchHistoryEntry",
    "OperatorFlowSnapshotResponse",
    "OperatorFlowTraceQuery",
    "OperatorFlowTraceResponse",
    "TopActionableItem",
]
