from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.compiler import MappingRolePolicyLookup, NormalizedCompiledPlan
from app.schemas.workflow_definitions import NodeKind, WorkflowDefinitionInput

RuntimeText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TaskIdentifier = RuntimeText
SlotIdentifier = RuntimeText


class TaskRootMode(StrEnum):
    ENSURE_TASK_DEFAULT = "ensure_task_default"
    ENSURE_HOST_PATH = "ensure_host_path"
    USE_EXISTING_HOST = "use_existing_host"


class PromptFamily(StrEnum):
    WORKER_DISPATCH = "worker_dispatch_prompt"
    PARENT_ROOT_DISPATCH = "parent_root_dispatch_prompt"


class PromptSendMode(StrEnum):
    FULL_PROMPT = "full_prompt"
    SAME_SESSION_CONTINUE = "same_session_continue"


class FlowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvidenceKind(StrEnum):
    ARTIFACT = "artifact"
    CRITERIA = "criteria"
    DOC = "doc"
    WIKI = "wiki"
    TRANSIENT = "transient"


class NodeRuntimeFileKind(StrEnum):
    MANIFEST = "manifest"
    ASSIGNMENT = "assignment"
    CHECKPOINT = "checkpoint"
    ARTIFACT_INDEX = "artifact_index"
    TRANSIENT_INDEX = "transient_index"


class CheckpointKind(StrEnum):
    PROGRESS = "progress"
    TERMINAL = "terminal"


class EgressBoundary(StrEnum):
    YIELD = "yield"
    GREEN = "green"
    RETRY = "retry"
    BLOCKED = "blocked"


class CheckpointOutcome(StrEnum):
    GREEN = "green"
    RETRY = "retry"
    BLOCKED = "blocked"


class ParentRootToolName(StrEnum):
    ASSIGN_CHILD = "assign_child"
    ADD_CHILD = "add_child"
    UPDATE_CHILD = "update_child"
    REMOVE_CHILD = "remove_child"
    RELEASE_GREEN = "release_green"
    RELEASE_BLOCKED = "release_blocked"


class DispatchDeliveryStatus(StrEnum):
    PREPARED = "prepared"
    ACCEPTED = "accepted"
    PROVIDER_SIGNAL_SEEN = "provider_signal_seen"
    PROVIDER_COMPLETED = "provider_completed"
    PROVIDER_FAILED = "provider_failed"
    TRANSPORT_FAILED = "transport_failed"
    TRANSPORT_AMBIGUOUS = "transport_ambiguous"
    SUPERSEDED = "superseded"


class TaskComposeTaskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: RuntimeText
    title: RuntimeText
    summary: RuntimeText
    instruction: RuntimeText | None = None


class TaskComposeWorkflowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: RuntimeText


class TaskRootBindingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: TaskRootMode = TaskRootMode.ENSURE_TASK_DEFAULT
    host_path: Path | None = None

    @model_validator(mode="after")
    def validate_host_path(self) -> TaskRootBindingInput:
        if self.mode == TaskRootMode.ENSURE_TASK_DEFAULT and self.host_path is not None:
            raise ValueError("host_path is invalid with ensure_task_default")
        if self.mode != TaskRootMode.ENSURE_TASK_DEFAULT and self.host_path is None:
            raise ValueError(f"host_path is required with {self.mode.value}")
        return self


class TaskComposeRootsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace: TaskRootBindingInput | None = None
    context: TaskRootBindingInput | None = None


class TaskComposeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: TaskComposeTaskInput
    workflow: TaskComposeWorkflowInput
    roots: TaskComposeRootsInput | None = None


class TaskRootPaths(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_root: Path
    workspace_path: Path
    context_path: Path
    criteria_path: Path
    wiki_path: Path
    outputs_path: Path
    artifacts_path: Path
    tmp_path: Path
    transfers_path: Path
    runtime_path: Path
    attempts_path: Path
    dispatch_path: Path


class NodeRuntimeFileRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: NodeRuntimeFileKind
    path: Path
    description: RuntimeText


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: EvidenceKind
    slot: SlotIdentifier | None = None
    version: int | None = Field(default=None, ge=1)
    path: Path
    description: RuntimeText

    @model_validator(mode="after")
    def validate_shape(self) -> EvidenceRef:
        if self.kind == EvidenceKind.ARTIFACT:
            if self.slot is None or self.version is None:
                raise ValueError("artifact refs require slot and version")
            return self
        if self.version is not None:
            raise ValueError("only artifact refs may set version")
        if self.kind == EvidenceKind.TRANSIENT and self.slot is not None:
            raise ValueError("transient refs must not set slot")
        return self


type RuntimeContextRef = NodeRuntimeFileRef | EvidenceRef
type AssignmentConsumeRef = NodeRuntimeFileRef | EvidenceRef


class ManifestTaskProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: TaskIdentifier
    task_key: RuntimeText
    title: RuntimeText
    summary: RuntimeText
    instruction: RuntimeText | None = None


class ManifestWorkflowProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_key: RuntimeText
    description: RuntimeText


class ManifestFilesystemRootsProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_path: Path
    context_path: Path
    outputs_path: Path
    tmp_path: Path
    runtime_path: Path


class ManifestNodeConsumeProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: EvidenceKind
    slot: SlotIdentifier
    description: RuntimeText
    required: bool = True

    @model_validator(mode="after")
    def validate_kind(self) -> ManifestNodeConsumeProjection:
        if self.kind not in {EvidenceKind.ARTIFACT, EvidenceKind.CRITERIA}:
            raise ValueError("manifest node consumes support artifact or criteria only")
        return self


class ManifestNodeProduceProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slot: SlotIdentifier
    description: RuntimeText
    file_hint: RuntimeText | None = None


class ManifestNodeCriteriaProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    owner_node_key: RuntimeText
    slot: SlotIdentifier
    description: RuntimeText
    path: Path


class ManifestNodeProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_key: RuntimeText
    parent_node_key: RuntimeText | None = None
    child_node_keys: tuple[RuntimeText, ...] = ()
    node_kind: NodeKind
    role: RuntimeText
    description: RuntimeText
    consumes: tuple[ManifestNodeConsumeProjection, ...] = ()
    produces: tuple[ManifestNodeProduceProjection, ...] = ()
    criteria: tuple[ManifestNodeCriteriaProjection, ...] = ()
    depends_on_node_keys: tuple[RuntimeText, ...] = ()
    depended_on_by_node_keys: tuple[RuntimeText, ...] = ()


class ManifestDependencyProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_node_key: RuntimeText
    consumer_node_key: RuntimeText
    kind: RuntimeText
    slot: SlotIdentifier
    description: RuntimeText


class ManifestCurrentContextProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    current_node_key: RuntimeText
    owner_node_key: RuntimeText
    active_attempt_id: RuntimeText
    active_assignment_path: Path
    latest_checkpoint_path: Path | None = None
    current_relevant_paths: tuple[RuntimeContextRef, ...] = ()


class ManifestProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: int = 1
    active_flow_revision_id: RuntimeText
    generated_at: datetime
    task: ManifestTaskProjection
    workflow: ManifestWorkflowProjection
    filesystem_roots: ManifestFilesystemRootsProjection
    current_context: ManifestCurrentContextProjection
    node_tree: tuple[ManifestNodeProjection, ...]
    dependency_index: tuple[ManifestDependencyProjection, ...]


class ProduceRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slot: SlotIdentifier
    description: RuntimeText
    file_hint: RuntimeText | None = None


class AssignmentProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    assignment_key: RuntimeText
    node_key: RuntimeText
    summary: RuntimeText
    instruction: RuntimeText | None = None
    criteria: tuple[EvidenceRef, ...] = ()
    consumes: tuple[AssignmentConsumeRef, ...] = ()
    produces: tuple[ProduceRequirement, ...] = ()
    transient_refs: tuple[EvidenceRef, ...] = ()
    task_memory_search_hints: tuple[RuntimeText, ...] = ()

    @model_validator(mode="after")
    def validate_refs(self) -> AssignmentProjection:
        if any(ref.kind != EvidenceKind.CRITERIA for ref in self.criteria):
            raise ValueError("assignment criteria must use criteria refs")
        for ref in self.consumes:
            if isinstance(ref, EvidenceRef):
                if ref.kind == EvidenceKind.TRANSIENT:
                    raise ValueError("assignment consumes must not use transient refs")
                continue
            if ref.kind != NodeRuntimeFileKind.CHECKPOINT:
                raise ValueError("assignment consumes support checkpoint runtime refs only")
        if any(ref.kind != EvidenceKind.TRANSIENT for ref in self.transient_refs):
            raise ValueError("assignment transient_refs must use transient refs")
        return self


class CheckpointHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: RuntimeText
    next_step: RuntimeText
    blockers: tuple[RuntimeText, ...] = ()
    risks: tuple[RuntimeText, ...] = ()


class CheckpointProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_kind: CheckpointKind
    outcome: CheckpointOutcome | None = None
    handoff: CheckpointHandoff
    produced_artifacts: tuple[EvidenceRef, ...] = ()
    transient_refs: tuple[EvidenceRef, ...] = ()
    task_memory_search_hints: tuple[RuntimeText, ...] = ()

    @model_validator(mode="after")
    def validate_projection(self) -> CheckpointProjection:
        if self.checkpoint_kind == CheckpointKind.PROGRESS and self.outcome is not None:
            raise ValueError("progress checkpoints must not set outcome")
        if self.checkpoint_kind == CheckpointKind.TERMINAL and self.outcome is None:
            raise ValueError("terminal checkpoints require outcome")
        if any(ref.kind != EvidenceKind.ARTIFACT for ref in self.produced_artifacts):
            raise ValueError("checkpoint produced_artifacts must use artifact refs")
        if any(ref.kind != EvidenceKind.TRANSIENT for ref in self.transient_refs):
            raise ValueError("checkpoint transient_refs must use transient refs")
        return self


class ResolvedNodeContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_key: RuntimeText
    node_kind: NodeKind
    node_description: RuntimeText
    role_key: RuntimeText
    role_revision_no: int = Field(ge=1)
    role_description: RuntimeText
    role_instruction: RuntimeText | None = None
    policy_key: RuntimeText | None = None
    policy_revision_no: int | None = Field(default=None, ge=1)
    policy_description: RuntimeText | None = None
    policy_instruction: RuntimeText | None = None


class PromptRenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_family: PromptFamily
    send_mode: PromptSendMode
    task_id: TaskIdentifier
    current_node: ResolvedNodeContext
    manifest: ManifestProjection
    assignment: AssignmentProjection
    latest_checkpoint: CheckpointProjection | None = None


class RenderedPromptBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_family: PromptFamily
    send_mode: PromptSendMode
    instructions_text: RuntimeText
    input_text: RuntimeText
    full_markdown: RuntimeText
    content_hash: RuntimeText


class PersistedPromptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dispatch_id: RuntimeText
    node_key: RuntimeText
    attempt_id: RuntimeText
    assignment_key: RuntimeText
    prompt_name: PromptFamily
    send_mode: PromptSendMode
    rendered_markdown_path: Path
    content_hash: RuntimeText
    rendered_at: datetime


class RuntimeBootstrapInput(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    task_id: TaskIdentifier
    active_flow_revision_id: RuntimeText
    attempt_id: RuntimeText
    assignment_key: RuntimeText
    dispatch_id: RuntimeText
    task_root: Path
    task_compose: TaskComposeInput
    workflow_definition: WorkflowDefinitionInput
    compiled_plan: NormalizedCompiledPlan
    role_policy_lookup: MappingRolePolicyLookup
    current_node_key: RuntimeText = "root"
    owner_node_key: RuntimeText | None = None
    assignment: AssignmentProjection | None = None
    latest_checkpoint: CheckpointProjection | None = None

    @model_validator(mode="after")
    def validate_workflow_alignment(self) -> RuntimeBootstrapInput:
        if self.task_compose.workflow.key != self.compiled_plan.workflow_key:
            raise ValueError(
                "task compose workflow key "
                f"'{self.task_compose.workflow.key}' does not match compiled plan "
                f"workflow key '{self.compiled_plan.workflow_key}'"
            )
        if self.workflow_definition.id != self.compiled_plan.workflow_key:
            raise ValueError(
                "workflow definition id "
                f"'{self.workflow_definition.id}' does not match compiled plan "
                f"workflow key '{self.compiled_plan.workflow_key}'"
            )
        return self


class RuntimeBootstrapResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    paths: TaskRootPaths
    manifest: ManifestProjection
    assignment: AssignmentProjection
    latest_checkpoint: CheckpointProjection | None = None
    prompt_bundle: RenderedPromptBundle
    prompt_record: PersistedPromptRecord
