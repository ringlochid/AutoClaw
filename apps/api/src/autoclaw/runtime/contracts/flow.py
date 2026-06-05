from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autoclaw.runtime.contracts.common import RuntimeSchemaText
from autoclaw.runtime.contracts.primitives import FlowStatus
from autoclaw.runtime.contracts.refs import WorkflowManifestRef


class RuntimeFlowRead(BaseModel):
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
    "RuntimeFlowPauseResponse",
    "RuntimeFlowRead",
    "RuntimeFlowSummary",
    "RuntimeFlowSummaryListResponse",
    "RuntimeTaskListQuery",
]
