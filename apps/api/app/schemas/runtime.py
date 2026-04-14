from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    ApprovalStatus,
    CheckpointStatus,
    ContextItemKind,
    ContextItemScope,
    ContextItemStatus,
    ContextManifestStatus,
    FlowEdgeKind,
    FlowNodeState,
    FlowRevisionStatus,
    FlowStatus,
    NodeAttemptStatus,
    NodePlanRevisionStatus,
    NodeSessionStatus,
    TaskStatus,
    WaitReason,
    WorkflowMode,
)


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    input_payload: dict[str, Any]


class TaskSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str
    status: TaskStatus


class FlowStartFromWorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: TaskCreate


class FlowRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    revision_no: int
    compiled_plan_id: UUID
    status: FlowRevisionStatus


class NodeAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: int
    status: NodeAttemptStatus
    retry_of_node_attempt_id: UUID | None
    failure_signature: str | None


class NodeAttemptHistoryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    flow_revision_id: UUID
    flow_node_id: UUID
    flow_node_key: str
    flow_node_path: str
    number: int
    status: NodeAttemptStatus
    retry_of_node_attempt_id: UUID | None
    failure_signature: str | None
    started_at: datetime
    finished_at: datetime | None


class NodeSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_node_id: UUID
    node_attempt_id: UUID | None
    provider_session_key: str
    status: NodeSessionStatus
    last_seen_at: datetime | None
    ended_at: datetime | None


class ContextItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    flow_id: UUID | None
    flow_node_id: UUID | None
    node_attempt_id: UUID | None
    scope: ContextItemScope
    kind: ContextItemKind
    status: ContextItemStatus
    title: str
    storage_uri: str
    content_hash: str
    published_by: str


class ContextManifestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_id: UUID
    flow_node_id: UUID
    node_attempt_id: UUID
    node_session_id: UUID | None
    manifest_no: int
    manifest_payload: dict[str, Any]
    manifest_hash: str
    status: ContextManifestStatus
    projected_at: datetime
    acked_at: datetime | None


class FlowNodeRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    flow_revision_id: UUID
    source_compiled_plan_node_id: UUID | None
    parent_flow_node_id: UUID | None
    node_key: str
    node_path: str
    state: FlowNodeState
    order_index: int
    status_payload: dict[str, Any]


class FlowNodeInspectRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    node_key: str
    node_path: str
    state: FlowNodeState
    order_index: int
    current_attempt: NodeAttemptRead | None = None
    current_session: NodeSessionRead | None = None
    current_manifest: ContextManifestRead | None = None


class FlowStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_id: UUID
    task_id: UUID
    active_flow_revision_id: UUID
    compiled_plan_id: UUID
    flow_node_count: int
    first_flow_node_id: UUID


class FlowSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    task: TaskSummaryRead
    status: FlowStatus
    execution_no: int
    seed_compiled_plan_id: UUID
    active_flow_revision_id: UUID | None
    node_count: int
    done_node_count: int
    blocked_node_count: int
    pending_approval_count: int
    projected_manifest_count: int
    latest_checkpoint_status: CheckpointStatus | None = None
    latest_checkpoint_summary: str | None = None
    latest_checkpoint_wait_reason: WaitReason | None = None


class FlowInspectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    task_id: UUID
    status: FlowStatus
    execution_no: int
    seed_compiled_plan_id: UUID
    active_flow_revision_id: UUID | None
    active_revision: FlowRevisionRead | None = None
    nodes: list[FlowNodeInspectRead] = Field(default_factory=list)
    node_count: int


class FlowRevisionHistoryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    revision_no: int
    compiled_plan_id: UUID
    workflow_version_id: UUID
    parent_flow_revision_id: UUID | None
    status: FlowRevisionStatus
    reason: str | None
    adopted_from_node_plan_revision_id: UUID | None
    adopted_at: datetime | None


class NodePlanPatchNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role: str
    mode: WorkflowMode
    policy: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodePlanPatchEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    when: str | None = None
    kind: FlowEdgeKind = FlowEdgeKind.CONTROL


class NodePlanPatchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[NodePlanPatchNode]
    edges: list[NodePlanPatchEdge]
    skill_bindings: list[dict[str, Any]] = Field(default_factory=list)


class NodePlanRevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requesting_flow_node_id: UUID
    requesting_node_attempt_id: UUID | None = None
    reason: str
    patch: NodePlanPatchPayload


class NodePlanRevisionRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    flow_id: UUID
    requesting_flow_node_id: UUID
    requesting_node_attempt_id: UUID | None
    base_flow_revision_id: UUID
    candidate_flow_revision_id: UUID | None
    reason: str
    status: NodePlanRevisionStatus
    patch_payload: dict[str, Any]
    error_text: str | None
    validated_at: datetime | None
    adopted_at: datetime | None


class FlowOperatorRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: FlowInspectResponse
    task: TaskRead
    revisions: list[FlowRevisionHistoryRead] = Field(default_factory=list)
    replans: list[NodePlanRevisionRead] = Field(default_factory=list)
    nodes: list[FlowNodeRead] = Field(default_factory=list)
    attempts: list[NodeAttemptHistoryRead] = Field(default_factory=list)
    checkpoints: list[CheckpointRead] = Field(default_factory=list)
    approvals: list[ApprovalRead] = Field(default_factory=list)
    sessions: list[NodeSessionRead] = Field(default_factory=list)
    manifests: list[ContextManifestRead] = Field(default_factory=list)
    context_items: list[ContextItemRead] = Field(default_factory=list)


class FlowNodeRetryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: FlowInspectResponse
    retried_node_attempt_id: UUID


class FlowPauseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: FlowInspectResponse
    paused_node_ids: list[UUID] = Field(default_factory=list)


class FlowWatchdogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: FlowInspectResponse
    stalled_node_attempt_ids: list[UUID] = Field(default_factory=list)
    checkpoint_ids: list[UUID] = Field(default_factory=list)


class CheckpointWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_id: UUID
    flow_node_id: UUID
    node_attempt_id: UUID
    sequence_no: int
    status: CheckpointStatus
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    failure_signature: str | None = None
    recommended_next_action: str | None = None
    wait_reason: WaitReason | None = None


class CheckpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_id: UUID
    flow_node_id: UUID
    node_attempt_id: UUID
    sequence_no: int
    status: CheckpointStatus
    summary: str
    payload: dict[str, Any]
    failure_signature: str | None
    recommended_next_action: str | None
    wait_reason: WaitReason | None


class ApprovalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_id: UUID
    reason: str
    node_attempt_id: UUID | None = None
    flow_node_id: UUID | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_id: UUID
    node_attempt_id: UUID | None
    flow_node_id: UUID | None
    status: ApprovalStatus
    reason: str
    request_payload: dict[str, Any]
    resolution_payload: dict[str, Any]


class ApprovalResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApprovalStatus
    resolution_payload: dict[str, Any] = Field(default_factory=dict)


class CompiledPlanNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_key: str
    parent_node_key: str | None
    mode: WorkflowMode
    order_index: int
    skill_bindings: list[dict[str, Any]] = Field(default_factory=list)


class CompiledPlanEdgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_node_key: str
    to_node_key: str
    edge_kind: FlowEdgeKind
    condition_expr: str | None
    order_index: int


class CompiledPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_version_id: UUID
    compiler_version: str
    plan_hash: str
    source_snapshot: dict[str, Any] = Field(default_factory=dict)
    nodes: list[CompiledPlanNodeRead] = Field(default_factory=list)
    edges: list[CompiledPlanEdgeRead] = Field(default_factory=list)
