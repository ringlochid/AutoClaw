from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import FlowModel, TaskModel
from autoclaw.runtime.contracts import FlowStatus, RuntimeFlowRead, WorkflowManifestRef
from autoclaw.runtime.dispatch.authority import NodeOperationAuthority
from autoclaw.runtime.errors import missing_resource_error
from autoclaw.runtime.flow.reads import normalized_pause_reason, normalized_waiting_cause


async def runtime_flow_read(
    session: AsyncSession,
    authority: NodeOperationAuthority,
) -> RuntimeFlowRead:
    task = await session.get(TaskModel, authority.task_id)
    flow = await session.get(FlowModel, authority.flow_id)
    if task is None or flow is None or flow.active_flow_revision_id is None:
        raise missing_resource_error("current task or flow disappeared")
    status = _public_flow_status(flow)
    current_node_key = authority.node_key if flow.current_dispatch_id is not None else None
    active_attempt_id = authority.attempt_id if flow.current_dispatch_id is not None else None
    return RuntimeFlowRead(
        task_id=task.task_id,
        task_title=task.title,
        task_summary=task.summary,
        workflow_key=task.workflow_key,
        status=status,
        active_flow_revision_id=flow.active_flow_revision_id,
        control_revision=flow.control_revision,
        workflow_manifest_ref=WorkflowManifestRef(
            path=Path("_runtime/workflow-manifest.md"),
            description="Current workflow manifest projection.",
        ),
        current_node_key=current_node_key,
        active_assignment_id=(
            authority.assignment_id if flow.current_dispatch_id is not None else None
        ),
        active_attempt_id=active_attempt_id,
        current_dispatch_id=flow.current_dispatch_id,
        waiting_cause=normalized_waiting_cause(flow.waiting_cause),
        pause_reason=normalized_pause_reason(flow.pause_reason),
        updated_at=flow.updated_at,
    )


def _public_flow_status(flow: FlowModel) -> FlowStatus:
    if flow.status == "completed":
        return FlowStatus.SUCCEEDED if flow.terminal_outcome == "green" else FlowStatus.BLOCKED
    return FlowStatus(flow.status)


__all__ = ["runtime_flow_read"]
