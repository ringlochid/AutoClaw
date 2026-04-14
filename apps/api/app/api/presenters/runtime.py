from __future__ import annotations

from app.db.models.runtime import (
    Approval,
    CompiledPlan,
    ContextManifest,
    Flow,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodeCheckpoint,
    NodeSession,
    Task,
)
from app.schemas.runtime import (
    ApprovalRead,
    CheckpointRead,
    CompiledPlanEdgeRead,
    CompiledPlanNodeRead,
    CompiledPlanRead,
    ContextManifestRead,
    FlowInspectResponse,
    FlowNodeInspectRead,
    FlowRevisionRead,
    FlowStartResponse,
    NodeAttemptRead,
    NodeSessionRead,
    TaskRead,
)


def to_task_read(task: Task) -> TaskRead:
    return TaskRead.model_validate(task)


def to_checkpoint_read(checkpoint: NodeCheckpoint) -> CheckpointRead:
    return CheckpointRead.model_validate(checkpoint)


def to_approval_read(approval: Approval) -> ApprovalRead:
    return ApprovalRead.model_validate(approval)


def to_context_manifest_read(manifest: ContextManifest) -> ContextManifestRead:
    return ContextManifestRead.model_validate(manifest)


def to_flow_start_response(
    *,
    task: Task,
    flow: Flow,
    flow_revision: FlowRevision,
    flow_nodes: list[FlowNode],
) -> FlowStartResponse:
    first_flow_node = flow_nodes[0]
    return FlowStartResponse(
        flow_id=flow.id,
        task_id=task.id,
        active_flow_revision_id=flow_revision.id,
        compiled_plan_id=flow_revision.compiled_plan_id,
        flow_node_count=len(flow_nodes),
        first_flow_node_id=first_flow_node.id,
    )


def _latest_attempt(flow_node: FlowNode) -> NodeAttempt | None:
    return flow_node.attempts[-1] if flow_node.attempts else None


def _latest_manifest(flow_node: FlowNode) -> ContextManifest | None:
    latest_attempt = _latest_attempt(flow_node)
    if latest_attempt is None or not latest_attempt.context_manifests:
        return None
    return latest_attempt.context_manifests[-1]


def _to_node_attempt_read(node_attempt: NodeAttempt | None) -> NodeAttemptRead | None:
    if node_attempt is None:
        return None
    return NodeAttemptRead.model_validate(node_attempt)


def _to_node_session_read(node_session: NodeSession | None) -> NodeSessionRead | None:
    if node_session is None:
        return None
    return NodeSessionRead.model_validate(node_session)


def to_flow_inspect_response(flow: Flow) -> FlowInspectResponse:
    active_revision = flow.active_flow_revision
    nodes: list[FlowNodeInspectRead] = []

    if active_revision is not None:
        for flow_node in active_revision.nodes:
            current_attempt = _latest_attempt(flow_node)
            current_manifest = _latest_manifest(flow_node)
            nodes.append(
                FlowNodeInspectRead(
                    id=flow_node.id,
                    node_key=flow_node.node_key,
                    node_path=flow_node.node_path,
                    state=flow_node.state,
                    order_index=flow_node.order_index,
                    current_attempt=_to_node_attempt_read(current_attempt),
                    current_session=_to_node_session_read(flow_node.node_session),
                    current_manifest=(
                        ContextManifestRead.model_validate(current_manifest)
                        if current_manifest is not None
                        else None
                    ),
                )
            )

    return FlowInspectResponse(
        id=flow.id,
        task_id=flow.task_id,
        status=flow.status,
        execution_no=flow.execution_no,
        seed_compiled_plan_id=flow.seed_compiled_plan_id,
        active_flow_revision_id=flow.active_flow_revision_id,
        active_revision=(
            FlowRevisionRead.model_validate(active_revision)
            if active_revision is not None
            else None
        ),
        nodes=nodes,
        node_count=len(nodes),
    )


def to_compiled_plan_read(compiled_plan: CompiledPlan) -> CompiledPlanRead:
    nodes = [CompiledPlanNodeRead.model_validate(node) for node in compiled_plan.nodes]
    edges = [CompiledPlanEdgeRead.model_validate(edge) for edge in compiled_plan.edges]

    return CompiledPlanRead(
        id=compiled_plan.id,
        workflow_version_id=compiled_plan.workflow_version_id,
        compiler_version=compiled_plan.compiler_version,
        plan_hash=compiled_plan.plan_hash,
        source_snapshot=compiled_plan.source_snapshot,
        nodes=nodes,
        edges=edges,
    )
