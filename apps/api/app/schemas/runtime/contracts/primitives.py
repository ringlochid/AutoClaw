from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

RuntimeText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TaskIdentifier = RuntimeText
SlotIdentifier = RuntimeText


class TaskRootMode(StrEnum):
    ENSURE_TASK_DEFAULT = "ensure_task_default"
    ENSURE_HOST_PATH = "ensure_host_path"
    USE_EXISTING_HOST = "use_existing_host"


class FlowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
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
        if self.kind == EvidenceKind.CRITERIA:
            if self.slot is None:
                raise ValueError("criteria refs require slot")
            if self.version is not None:
                raise ValueError("criteria refs must not set version")
            return self
        if self.version is not None:
            raise ValueError("only artifact refs may set version")
        if self.kind == EvidenceKind.TRANSIENT and self.slot is not None:
            raise ValueError("transient refs must not set slot")
        return self


type RuntimeContextRef = NodeRuntimeFileRef | EvidenceRef
type AssignmentConsumeRef = NodeRuntimeFileRef | EvidenceRef


__all__ = [
    "AssignmentConsumeRef",
    "CheckpointKind",
    "CheckpointOutcome",
    "DispatchDeliveryStatus",
    "EgressBoundary",
    "EvidenceKind",
    "EvidenceRef",
    "FlowStatus",
    "NodeRuntimeFileKind",
    "NodeRuntimeFileRef",
    "ParentRootToolName",
    "RuntimeContextRef",
    "RuntimeText",
    "SlotIdentifier",
    "TaskComposeInput",
    "TaskComposeRootsInput",
    "TaskComposeTaskInput",
    "TaskComposeWorkflowInput",
    "TaskIdentifier",
    "TaskRootBindingInput",
    "TaskRootMode",
    "TaskRootPaths",
]
