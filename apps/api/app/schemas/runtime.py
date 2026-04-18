from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    ResourceScope,
    TaskResourceBindingMode,
    TaskResourceBindingRole,
    TaskStatus,
    WaitReason,
    WorkflowMode,
    WorkspaceRootKind,
    WorkspaceRootMode,
)
from app.schemas.registry import (
    SkillReferenceSeed,
    WorkflowDefaultsSeed,
    WorkflowNodeResourcesSeed,
    WorkflowTaskDefaultsSeed,
)


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)


class WorkspaceRootRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    scope: ResourceScope
    key: str
    title: str
    storage_uri: str
    kind: WorkspaceRootKind
    mode: WorkspaceRootMode
    status: str
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextSpaceRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    scope: ResourceScope
    key: str
    title: str
    storage_uri: str
    source_workspace_root_id: UUID | None = None
    status: str
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ManifestRootRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    task_id: UUID
    key: str
    storage_uri: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskResourceBindingRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    task_id: UUID
    binding_role: TaskResourceBindingRole
    workspace_root_id: UUID | None = None
    context_space_id: UUID | None = None
    manifest_root_id: UUID | None = None
    mode: TaskResourceBindingMode
    read_only: bool | None = None
    required: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
    workspace_root: WorkspaceRootRead | None = None
    context_space: ContextSpaceRead | None = None
    manifest_root: ManifestRootRead | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    input_payload: dict[str, Any]
    resource_bindings: list[TaskResourceBindingRead] = Field(default_factory=list)


class TaskImageRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    image_hash: str
    source_task_id: UUID | None = None
    spec_payload: dict[str, Any] = Field(default_factory=dict)


class TaskComposeRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    task_id: UUID
    task_image_id: UUID | None = None
    status: str
    materialization_root: str
    compose_payload: dict[str, Any] = Field(default_factory=dict)
    task_image: TaskImageRead | None = None


class RuntimeImageRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    image_hash: str
    compiled_plan_node_id: UUID | None = None
    spec_payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeContainerRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    task_id: UUID
    task_compose_id: UUID | None = None
    runtime_image_id: UUID | None = None
    flow_id: UUID
    flow_node_id: UUID
    node_session_id: UUID | None = None
    current_node_attempt_id: UUID | None = None
    current_context_manifest_id: UUID | None = None
    backend_kind: str
    backend_handle: str | None = None
    status: str
    bootstrap_state: str
    container_payload: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    last_seen_at: datetime | None = None
    ended_at: datetime | None = None
    runtime_image: RuntimeImageRead | None = None


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


class NodeSessionSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: NodeSessionStatus
    last_seen_at: datetime | None
    ended_at: datetime | None


class NodeSessionAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_node_id: UUID
    node_attempt_id: UUID | None
    provider_session_key: str
    status: NodeSessionStatus
    last_seen_at: datetime | None
    ended_at: datetime | None


class ContextItemAuditRead(BaseModel):
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
    metadata: dict[str, Any] = Field(default_factory=dict)
    published_by: str


class ContextManifestRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    flow_id: UUID
    flow_node_id: UUID
    node_attempt_id: UUID
    node_session_id: UUID | None = None
    node_session_key: str | None = None
    manifest_no: int
    manifest_payload: dict[str, Any] = Field(default_factory=dict)
    manifest_hash: str
    manifest_root_id: UUID | None = None
    status: ContextManifestStatus
    projected_at: datetime
    acked_at: datetime | None
    ack_checkpoint_id: UUID | None = None


class ContextManifestAuditRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    flow_id: UUID
    flow_node_id: UUID
    node_attempt_id: UUID
    node_session_id: UUID | None
    node_session_key: str | None = None
    manifest_no: int
    manifest_payload: dict[str, Any]
    manifest_hash: str
    manifest_root_id: UUID | None = None
    status: ContextManifestStatus
    projected_at: datetime
    acked_at: datetime | None
    ack_checkpoint_id: UUID | None = None


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
    source_compiled_plan_node_id: UUID | None = None
    parent_flow_node_id: UUID | None = None
    node_key: str
    node_path: str
    state: FlowNodeState
    order_index: int
    status_payload: dict[str, Any] = Field(default_factory=dict)
    effective_payload: dict[str, Any] = Field(default_factory=dict)
    current_attempt: NodeAttemptRead | None = None
    current_session: NodeSessionSummaryRead | None = None
    current_manifest: ContextManifestRead | None = None
    current_wait_reason: WaitReason | None = None
    retryable: bool = False


class FlowEdgeInspectRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_node_key: str
    to_node_key: str
    edge_kind: FlowEdgeKind
    condition_expr: str | None = None
    order_index: int


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
    compiled_plan_id: UUID | None = None
    workflow_version_id: UUID | None = None
    nodes: list[FlowNodeInspectRead] = Field(default_factory=list)
    edges: list[FlowEdgeInspectRead] = Field(default_factory=list)
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
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    resources: WorkflowNodeResourcesSeed = Field(default_factory=WorkflowNodeResourcesSeed)
    skill_refs: list[SkillReferenceSeed] = Field(default_factory=list)


class NodePlanPatchEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    when: str | None = None
    kind: FlowEdgeKind = FlowEdgeKind.CONTROL


class NodePlanPatchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    policy: str | None = None
    defaults: WorkflowDefaultsSeed = Field(default_factory=WorkflowDefaultsSeed)
    task_defaults: WorkflowTaskDefaultsSeed = Field(default_factory=WorkflowTaskDefaultsSeed)
    nodes: list[NodePlanPatchNode]
    edges: list[NodePlanPatchEdge]
    skill_bindings: list[dict[str, Any]] = Field(default_factory=list)
    skill_refs: list[SkillReferenceSeed] = Field(default_factory=list)


class NodePlanRevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requesting_flow_node_id: UUID
    requesting_node_attempt_id: UUID
    reason: str
    patch: NodePlanPatchPayload


class InternalNodePlanRevisionCreate(NodePlanRevisionCreate):
    model_config = ConfigDict(extra="forbid")

    manifest_id: UUID
    manifest_hash: str
    node_session_key: str


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


class ApprovalSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_id: UUID
    node_attempt_id: UUID | None
    flow_node_id: UUID | None
    status: ApprovalStatus
    reason: str


class FlowAuditEventType(StrEnum):
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    CHECKPOINT_RECORDED = "checkpoint_recorded"
    WATCHDOG_BLOCKED = "watchdog_blocked"
    REVISION_REQUESTED = "replan_requested"
    REVISION_ADOPTED = "revision_adopted"
    CONTEXT_MANIFEST_PROJECTED = "context_manifest_projected"
    CONTEXT_MANIFEST_ACKNOWLEDGED = "context_manifest_acknowledged"
    CONTEXT_MANIFEST_EXPIRED = "context_manifest_expired"
    SYNC_READY = "sync_ready"


class FlowAuditEventRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: FlowAuditEventType
    occurred_at: datetime
    flow_id: UUID
    flow_node_id: UUID | None = None
    node_attempt_id: UUID | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class FlowOperatorRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: FlowInspectResponse
    task: TaskRead
    pending_approval_count: int
    projected_manifest_count: int
    approvals: list[ApprovalSummaryRead] = Field(default_factory=list)


class FlowAuditRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: FlowInspectResponse
    task: TaskRead
    revisions: list[FlowRevisionHistoryRead] = Field(default_factory=list)
    replans: list[NodePlanRevisionRead] = Field(default_factory=list)
    nodes: list[FlowNodeRead] = Field(default_factory=list)
    attempts: list[NodeAttemptHistoryRead] = Field(default_factory=list)
    checkpoints: list[CheckpointRead] = Field(default_factory=list)
    approvals: list[ApprovalRead] = Field(default_factory=list)
    sessions: list[NodeSessionAuditRead] = Field(default_factory=list)
    manifests: list[ContextManifestAuditRead] = Field(default_factory=list)
    context_items: list[ContextItemAuditRead] = Field(default_factory=list)
    events: list[FlowAuditEventRead] = Field(default_factory=list)


class FlowWorkerBundleRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: FlowInspectResponse
    task: TaskRead
    compiled_plan: CompiledPlanRead | None = None
    current_node: FlowNodeInspectRead | None = None
    current_attempt: NodeAttemptHistoryRead | None = None
    current_session: NodeSessionAuditRead | None = None
    current_manifest: ContextManifestAuditRead | None = None
    task_compose: TaskComposeRead | None = None
    runtime_container: RuntimeContainerRead | None = None
    recent_checkpoints: list[CheckpointRead] = Field(default_factory=list)
    approvals: list[ApprovalRead] = Field(default_factory=list)
    recent_manifests: list[ContextManifestAuditRead] = Field(default_factory=list)
    context_items: list[ContextItemAuditRead] = Field(default_factory=list)
    events: list[FlowAuditEventRead] = Field(default_factory=list)


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


class FlowWatchdogRecoveryAction(StrEnum):
    NONE = "none"
    WAKE = "wake"
    ESCALATE = "escalate"


class FlowWatchdogRecoveryReason(StrEnum):
    NO_ACTIVE_REVISION = "no-active-revision"
    NO_ELIGIBLE_NODE = "no-eligible-node"
    MULTIPLE_WATCHDOG_BLOCKED_NODES = "multiple-watchdog-blocked-nodes"
    MISSING_OR_REBOUND_SESSION = "missing-or-rebound-session"
    WAKE_BUDGET_EXHAUSTED = "wake-budget-exhausted"
    WAKE_DISPATCHED = "wake-dispatched"
    WAKE_DISPATCH_TIMEOUT = "wake-dispatch-timeout"
    WAKE_DISPATCH_FAILED = "wake-dispatch-failed"


class FlowWatchdogRecoveryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow: FlowInspectResponse
    recovery_action: FlowWatchdogRecoveryAction
    recovery_reason: FlowWatchdogRecoveryReason
    flow_node_id: UUID | None = None
    node_attempt_id: UUID | None = None
    node_session_key: str | None = None
    openclaw_response_id: str | None = None
    openclaw_output: str | None = None
    detail: str | None = None
    operator_next_step: str | None = None


class ContextManifestAckWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_hash: str
    node_session_key: str


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


class InternalCheckpointWrite(CheckpointWrite):
    model_config = ConfigDict(extra="forbid")

    manifest_id: UUID
    manifest_hash: str
    node_session_key: str


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

    @model_validator(mode="after")
    def validate_target_binding(self) -> ApprovalCreate:
        if self.node_attempt_id is None and self.flow_node_id is None:
            raise ValueError("Approval must target a flow node or node attempt")
        return self


class InternalContextItemPublish(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_id: UUID
    flow_node_id: UUID
    node_attempt_id: UUID
    manifest_id: UUID
    manifest_hash: str
    node_session_key: str
    title: str
    content: Any
    scope: ContextItemScope = ContextItemScope.FLOW_SHARED
    kind: ContextItemKind = ContextItemKind.NOTE
    storage_uri: str | None = None
    visibility_policy: dict[str, Any] = Field(default_factory=lambda: {"default": "shared"})
    metadata: dict[str, Any] = Field(default_factory=dict)


class InternalApprovalCreate(ApprovalCreate):
    model_config = ConfigDict(extra="forbid")

    manifest_id: UUID
    manifest_hash: str
    node_session_key: str

    @model_validator(mode="after")
    def validate_internal_target_binding(self) -> InternalApprovalCreate:
        if self.node_attempt_id is None:
            raise ValueError("Internal approval callback must target a node attempt")
        return self


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

    @field_validator("status")
    @classmethod
    def validate_resolution_status(cls, value: ApprovalStatus) -> ApprovalStatus:
        if value not in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.NOT_REQUIRED,
        }:
            raise ValueError("Approval resolution must be approved, rejected, or not_required")
        return value


class CompiledPlanNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_key: str
    parent_node_key: str | None
    mode: WorkflowMode
    order_index: int
    skill_bindings: list[dict[str, Any]] = Field(default_factory=list)
    effective_payload: dict[str, Any] = Field(default_factory=dict)


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


class OpenClawDispatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    flow: FlowInspectResponse
    delivery_status: str
    phase: str
    flow_node_id: UUID
    node_attempt_id: UUID
    node_session_key: str
    openclaw_response_id: str | None
    openclaw_output: str | None
    manifest_id: UUID | None
    manifest_hash: str | None
    next_checkpoint_sequence: int | None
