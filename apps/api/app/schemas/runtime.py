from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    ApprovalStatus,
    AttemptStatus,
    CheckpointStatus,
    FlowEdgeKind,
    FlowNodeState,
    FlowStatus,
    RunStatus,
    TaskStatus,
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


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    workflow_version_id: UUID
    compiled_plan_id: UUID


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    workflow_version_id: UUID
    compiled_plan_id: UUID
    status: RunStatus
    current_attempt_number: int


class AttemptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    number: int
    retry_of_attempt_id: UUID | None = None


class AttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    number: int
    status: AttemptStatus
    retry_of_attempt_id: UUID | None


class FlowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: UUID
    compiled_plan_id: UUID


class FlowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    compiled_plan_id: UUID
    status: FlowStatus


class FlowNodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_id: UUID
    compiled_plan_node_id: UUID
    node_key: str
    parent_flow_node_id: UUID | None = None
    iteration_index: int = 0
    status_payload: dict[str, Any] = Field(default_factory=dict)


class FlowNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_id: UUID
    compiled_plan_node_id: UUID
    node_key: str
    state: FlowNodeState
    iteration_index: int
    status_payload: dict[str, Any]


class CheckpointWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_id: UUID
    flow_node_id: UUID
    sequence_no: int
    status: CheckpointStatus
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    failure_signature: str | None = None
    recommended_next_action: str | None = None


class CheckpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_id: UUID
    flow_node_id: UUID
    sequence_no: int
    status: CheckpointStatus
    summary: str
    payload: dict[str, Any]
    failure_signature: str | None
    recommended_next_action: str | None


class ApprovalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    reason: str
    attempt_id: UUID | None = None
    flow_node_id: UUID | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    attempt_id: UUID | None
    flow_node_id: UUID | None
    status: ApprovalStatus
    reason: str
    request_payload: dict[str, Any]
    resolution_payload: dict[str, Any]


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


class RunStartFromWorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: TaskCreate
    attempt_number: int | None = None


class RunStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    task_id: UUID
    attempt_id: UUID
    flow_id: UUID
    compiled_plan_id: UUID
    attempt_number: int
    flow_node_count: int
    first_flow_node_id: UUID


class RunInspectAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: int
    status: AttemptStatus


class RunInspectFlowNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_key: str
    state: FlowNodeState
    iteration_index: int


class RunInspectFlowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: FlowStatus
    nodes: list[RunInspectFlowNodeRead] = Field(default_factory=list)


class RunInspectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: RunStatus
    workflow_version_id: UUID
    compiled_plan_id: UUID
    current_attempt_number: int
    attempts: list[RunInspectAttemptRead] = Field(default_factory=list)
    flows: list[RunInspectFlowRead] = Field(default_factory=list)
    node_count: int
