from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autoclaw.runtime.contracts.common import RuntimeSchemaText
from autoclaw.runtime.contracts.primitives import FlowStatus
from autoclaw.runtime.contracts.refs import WorkflowManifestRef

type RuntimeFlowWaitingCause = Literal["human_request", "command_run"]
type RuntimeFlowPauseReason = Literal[
    "paused_by_operator",
    "runtime_recovery_exhausted",
    "runtime_transition_failed",
]


class RuntimeFlowRead(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    task_id: RuntimeSchemaText
    task_title: RuntimeSchemaText
    task_summary: RuntimeSchemaText
    workflow_key: RuntimeSchemaText | None = None
    status: FlowStatus
    active_flow_revision_id: RuntimeSchemaText
    control_revision: int = Field(ge=0)
    workflow_manifest_ref: WorkflowManifestRef
    current_node_key: RuntimeSchemaText | None = None
    active_assignment_id: RuntimeSchemaText | None = None
    active_attempt_id: RuntimeSchemaText | None = None
    current_dispatch_id: RuntimeSchemaText | None = None
    waiting_cause: RuntimeFlowWaitingCause | None = None
    pause_reason: RuntimeFlowPauseReason | None = None
    updated_at: datetime


class RuntimeFlowSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

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
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    items: tuple[RuntimeFlowSummary, ...]
    next_cursor: RuntimeSchemaText | None = None


class RuntimeFlowPauseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    flow: RuntimeFlowRead


class RuntimeFlowControlQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_active_flow_revision_id: RuntimeSchemaText
    expected_control_revision: int = Field(ge=0)


class RuntimeTaskListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

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
        "cancelled",
    ] = "any"


__all__ = [
    "RuntimeFlowControlQuery",
    "RuntimeFlowPauseReason",
    "RuntimeFlowPauseResponse",
    "RuntimeFlowRead",
    "RuntimeFlowSummary",
    "RuntimeFlowSummaryListResponse",
    "RuntimeFlowWaitingCause",
    "RuntimeTaskListQuery",
]
