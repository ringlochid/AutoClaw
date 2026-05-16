from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.runtime.contract_models.primitives import TaskComposeInput
from app.runtime.contracts import FlowStatus
from app.schemas.runtime.common import RuntimeSchemaText
from app.schemas.runtime.refs import WorkflowManifestRef


class TaskStartRequest(TaskComposeInput):
    """Public task-start contract over the authored task-compose body."""


class TaskStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    task_id: RuntimeSchemaText
    compiled_plan_id: RuntimeSchemaText
    active_flow_revision_id: RuntimeSchemaText
    flow_status: FlowStatus
    workflow_manifest_ref: WorkflowManifestRef


__all__ = ["TaskStartRequest", "TaskStartResponse"]
