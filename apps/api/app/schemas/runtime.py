from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.runtime.contracts import (
    CheckpointKind,
    CheckpointOutcome,
    DispatchDeliveryStatus,
    EgressBoundary,
    FlowStatus,
    ParentRootToolName,
    PromptSendMode,
)
from app.schemas.workflow_definitions import (
    ChildDefaults,
    ConsumeBuckets,
    CriteriaDeclaration,
    NodeDefinitionInput,
    ProduceBuckets,
)

RuntimeSchemaText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class WorkflowManifestRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class AssignmentFileRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class CheckpointFileRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class ArtifactIndexRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class TransientIndexRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["artifact"] = "artifact"
    slot: RuntimeSchemaText
    version: int = Field(ge=1)
    path: Path
    description: RuntimeSchemaText


class CriteriaRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["criteria"] = "criteria"
    slot: RuntimeSchemaText
    path: Path
    description: RuntimeSchemaText


class DocRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["doc"] = "doc"
    path: Path
    description: RuntimeSchemaText


class WikiRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["wiki"] = "wiki"
    path: Path
    description: RuntimeSchemaText


class TransientRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["transient"] = "transient"
    path: Path
    description: RuntimeSchemaText


class CheckpointConsumeRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["checkpoint"] = "checkpoint"
    path: Path
    description: RuntimeSchemaText


type AssignmentConsumeRef = CheckpointConsumeRef | ArtifactRef | CriteriaRef | DocRef | WikiRef
type OperatorSupportSurfaceRef = (
    WorkflowManifestRef
    | AssignmentFileRef
    | CheckpointFileRef
    | ArtifactIndexRef
    | TransientIndexRef
    | ArtifactRef
    | CriteriaRef
    | DocRef
    | WikiRef
    | TransientRef
)


class AssignmentProduceRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slot: RuntimeSchemaText
    description: RuntimeSchemaText
    file_hint: RuntimeSchemaText | None = None


class AssignmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: RuntimeSchemaText
    instruction: RuntimeSchemaText | None = None
    criteria: tuple[CriteriaRef, ...] = ()
    consumes: tuple[AssignmentConsumeRef, ...] = ()
    produces: tuple[AssignmentProduceRequirement, ...] = ()
    transient_refs: tuple[TransientRef, ...] = ()
    task_memory_search_hints: tuple[RuntimeSchemaText, ...] = ()


class CheckpointHandoffRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: RuntimeSchemaText
    next_step: RuntimeSchemaText
    blockers: tuple[RuntimeSchemaText, ...] = ()
    risks: tuple[RuntimeSchemaText, ...] = ()


class ProducedArtifactClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["artifact"] = "artifact"
    slot: RuntimeSchemaText
    path: Path


class TransientSurfaceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    description: RuntimeSchemaText


class CheckpointWriteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkpoint_kind: CheckpointKind
    outcome: CheckpointOutcome | None = None
    handoff: CheckpointHandoffRead
    produced_artifacts: tuple[ProducedArtifactClaim, ...] = ()
    transient_surfaces: tuple[TransientSurfaceWrite, ...] = ()
    task_memory_search_hints: tuple[RuntimeSchemaText, ...] = ()


class CheckpointWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkpoint: CheckpointWriteBody


class CheckpointRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: RuntimeSchemaText
    checkpoint_id: RuntimeSchemaText
    checkpoint_ref: CheckpointFileRef
    latest_checkpoint_ref: CheckpointFileRef


class BoundaryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boundary: EgressBoundary


class RuntimeFlowRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: RuntimeSchemaText
    task_title: RuntimeSchemaText
    task_summary: RuntimeSchemaText
    workflow_key: RuntimeSchemaText | None = None
    status: FlowStatus
    active_flow_revision_id: RuntimeSchemaText
    workflow_manifest_ref: WorkflowManifestRef
    current_node_key: RuntimeSchemaText | None = None
    active_attempt_id: RuntimeSchemaText | None = None
    updated_at: datetime


class BoundaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted_boundary: EgressBoundary
    flow: RuntimeFlowRead
    latest_checkpoint_ref: CheckpointFileRef | None = None


class AssignmentIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: RuntimeSchemaText
    instruction: RuntimeSchemaText | None = None


class SupplementalSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: RuntimeSchemaText


class SupplementalDurableContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_slots: tuple[SupplementalSlot, ...] = ()
    criteria_slots: tuple[SupplementalSlot, ...] = ()


class AssignChildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_node_key: RuntimeSchemaText
    assignment_intent: AssignmentIntent
    supplemental_durable_context: SupplementalDurableContext | None = None
    transient_surfaces: tuple[TransientSurfaceWrite, ...] = ()
    task_memory_search_hints: tuple[RuntimeSchemaText, ...] = ()


class ChildNodeDraft(NodeDefinitionInput):
    pass


class ChildNodePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: RuntimeSchemaText | None = None
    policy: RuntimeSchemaText | None = None
    description: RuntimeSchemaText | None = None
    consumes: ConsumeBuckets | None = None
    produces: ProduceBuckets | None = None
    criteria: list[CriteriaDeclaration] | None = None
    child_defaults: ChildDefaults | None = None
    children: list[NodeDefinitionInput] | None = None


class AddChildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child: ChildNodeDraft


class UpdateChildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_node_key: RuntimeSchemaText
    patch: ChildNodePatch


class RemoveChildPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child_node_key: RuntimeSchemaText


class ReleaseGreenPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReleaseBlockedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParentToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: ParentRootToolName
    payload: (
        AssignChildPayload
        | AddChildPayload
        | UpdateChildPayload
        | RemoveChildPayload
        | ReleaseGreenPayload
        | ReleaseBlockedPayload
    )
    expected_structural_revision_id: RuntimeSchemaText | None = None


class AssignChildSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: Literal["assign_child"] = "assign_child"
    summary: RuntimeSchemaText | None = None
    target_node_key: RuntimeSchemaText
    target_assignment_key: RuntimeSchemaText
    target_attempt_id: RuntimeSchemaText
    child_assignment_ref: AssignmentFileRef | None = None
    flow: RuntimeFlowRead
    workflow_manifest_ref: WorkflowManifestRef | None = None
    latest_checkpoint_ref: CheckpointFileRef | None = None


class ParentToolMutationSuccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: Literal[
        "add_child",
        "update_child",
        "remove_child",
        "release_green",
        "release_blocked",
    ]
    summary: RuntimeSchemaText | None = None
    target_node_key: RuntimeSchemaText | None = None
    flow: RuntimeFlowRead
    workflow_manifest_ref: WorkflowManifestRef | None = None
    latest_checkpoint_ref: CheckpointFileRef | None = None


type ParentToolSuccess = AssignChildSuccess | ParentToolMutationSuccess


class RuntimeFlowSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: RuntimeSchemaText
    task_title: RuntimeSchemaText
    task_summary: RuntimeSchemaText
    workflow_key: RuntimeSchemaText | None = None
    status: FlowStatus
    active_flow_revision_id: RuntimeSchemaText
    workflow_manifest_ref: WorkflowManifestRef
    current_node_key: RuntimeSchemaText | None = None
    active_attempt_id: RuntimeSchemaText | None = None
    updated_at: datetime


class RuntimeFlowSummaryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    items: tuple[RuntimeFlowSummary, ...]
    next_cursor: RuntimeSchemaText | None = None


class RuntimeFlowPauseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    flow: RuntimeFlowRead


class TopActionableItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: RuntimeSchemaText
    node_key: RuntimeSchemaText | None = None
    current_paths: tuple[OperatorSupportSurfaceRef, ...] = ()
    suggested_action: RuntimeSchemaText | None = None


class OperatorFlowSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    flow: RuntimeFlowRead
    top_actionable_items: tuple[TopActionableItem, ...]
    current_paths: tuple[OperatorSupportSurfaceRef, ...] = ()


class DispatchHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_id: RuntimeSchemaText
    assignment_key: RuntimeSchemaText | None = None
    node_key: RuntimeSchemaText
    send_mode: PromptSendMode
    delivery_status: DispatchDeliveryStatus
    rendered_at: datetime


class CheckpointHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_id: RuntimeSchemaText
    attempt_id: RuntimeSchemaText
    checkpoint_kind: CheckpointKind
    outcome: CheckpointOutcome | None = None
    summary: RuntimeSchemaText
    recorded_at: datetime


class BoundaryHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_key: RuntimeSchemaText
    boundary: EgressBoundary
    occurred_at: datetime


class OperatorFlowTraceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: RuntimeSchemaText
    scope: Literal["current", "whole"] = "current"
    dispatch_history: tuple[DispatchHistoryEntry, ...]
    checkpoint_history: tuple[CheckpointHistoryEntry, ...]
    boundary_history: tuple[BoundaryHistoryEntry, ...]
    current_paths: tuple[OperatorSupportSurfaceRef, ...] = ()
    next_cursor: RuntimeSchemaText | None = None


class RuntimeFlowControlQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_active_flow_revision_id: RuntimeSchemaText


class RuntimeTaskListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    q: RuntimeSchemaText | None = None
    limit: int = Field(default=50, ge=1, le=200)
    cursor: RuntimeSchemaText | None = None
    sort: Literal[
        "updated_at_desc",
        "updated_at_asc",
        "task_title_asc",
        "task_title_desc",
    ] = "updated_at_desc"
    status: Literal[
        "any",
        "pending",
        "running",
        "blocked",
        "paused",
        "succeeded",
        "failed",
        "cancelled",
    ] = "any"


class OperatorFlowTraceQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["current", "whole"] = "current"
    q: RuntimeSchemaText | None = None
    limit: int = Field(default=50, ge=1, le=200)
    cursor: RuntimeSchemaText | None = None
    sort: Literal["occurred_at_desc", "occurred_at_asc"] = "occurred_at_desc"


class ObservabilityFileRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    description: RuntimeSchemaText
