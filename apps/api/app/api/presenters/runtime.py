from __future__ import annotations

from app.db.models.runtime import (
    Approval,
    CompiledPlan,
    ContextItem,
    ContextManifest,
    Flow,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodeCheckpoint,
    NodePlanRevision,
    NodeSession,
    Task,
)
from app.runtime.read_models import FlowOperatorSnapshot
from app.schemas.runtime import (
    ApprovalRead,
    CheckpointRead,
    CompiledPlanEdgeRead,
    CompiledPlanNodeRead,
    CompiledPlanRead,
    ContextItemRead,
    ContextManifestRead,
    FlowInspectResponse,
    FlowNodeInspectRead,
    FlowNodeRead,
    FlowOperatorRead,
    FlowRevisionHistoryRead,
    FlowRevisionRead,
    FlowStartResponse,
    FlowSummaryRead,
    NodeAttemptHistoryRead,
    NodeAttemptRead,
    NodePlanRevisionRead,
    NodeSessionRead,
    TaskRead,
    TaskSummaryRead,
)


def to_task_read(task: Task) -> TaskRead:
    return TaskRead.model_validate(task)


def to_task_summary_read(task: Task) -> TaskSummaryRead:
    return TaskSummaryRead(
        id=task.id,
        title=task.title,
        status=task.status,
    )


def to_checkpoint_read(checkpoint: NodeCheckpoint) -> CheckpointRead:
    return CheckpointRead.model_validate(checkpoint)


def to_approval_read(approval: Approval) -> ApprovalRead:
    return ApprovalRead.model_validate(approval)


def to_context_item_read(item: ContextItem) -> ContextItemRead:
    return ContextItemRead.model_validate(item)


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


def _latest_checkpoint(flow_node: FlowNode) -> NodeCheckpoint | None:
    latest_attempt = _latest_attempt(flow_node)
    if latest_attempt is None or not latest_attempt.checkpoints:
        return None
    return latest_attempt.checkpoints[-1]


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


def to_flow_summary_read(flow: Flow) -> FlowSummaryRead:
    active_revision = flow.active_flow_revision
    nodes = list(active_revision.nodes) if active_revision is not None else []
    latest_checkpoint = next(
        (
            checkpoint
            for checkpoint in reversed(
                [_latest_checkpoint(node) for node in nodes if _latest_checkpoint(node) is not None]
            )
            if checkpoint is not None
        ),
        None,
    )
    pending_approval_count = len(
        [approval for approval in flow.approvals if approval.status.value == "pending"]
    )
    projected_manifest_count = len(
        [manifest for manifest in flow.context_manifests if manifest.status.value == "projected"]
    )

    return FlowSummaryRead(
        id=flow.id,
        task=to_task_summary_read(flow.task),
        status=flow.status,
        execution_no=flow.execution_no,
        seed_compiled_plan_id=flow.seed_compiled_plan_id,
        active_flow_revision_id=flow.active_flow_revision_id,
        node_count=len(nodes),
        done_node_count=len([node for node in nodes if node.state.value == "done"]),
        blocked_node_count=len(
            [node for node in nodes if node.state.value in {"waiting", "paused", "failed"}]
        ),
        pending_approval_count=pending_approval_count,
        projected_manifest_count=projected_manifest_count,
        latest_checkpoint_status=(
            latest_checkpoint.status if latest_checkpoint is not None else None
        ),
        latest_checkpoint_summary=(
            latest_checkpoint.summary if latest_checkpoint is not None else None
        ),
        latest_checkpoint_wait_reason=(
            latest_checkpoint.wait_reason if latest_checkpoint is not None else None
        ),
    )


def to_flow_node_read(flow_node: FlowNode) -> FlowNodeRead:
    return FlowNodeRead(
        id=flow_node.id,
        flow_revision_id=flow_node.flow_revision_id,
        source_compiled_plan_node_id=flow_node.source_compiled_plan_node_id,
        parent_flow_node_id=flow_node.parent_flow_node_id,
        node_key=flow_node.node_key,
        node_path=flow_node.node_path,
        state=flow_node.state,
        order_index=flow_node.order_index,
        status_payload=flow_node.status_payload,
    )


def to_flow_revision_history_read(flow_revision: FlowRevision) -> FlowRevisionHistoryRead:
    return FlowRevisionHistoryRead(
        id=flow_revision.id,
        revision_no=flow_revision.revision_no,
        compiled_plan_id=flow_revision.compiled_plan_id,
        workflow_version_id=flow_revision.compiled_plan.workflow_version_id,
        parent_flow_revision_id=flow_revision.parent_flow_revision_id,
        status=flow_revision.status,
        reason=flow_revision.reason,
        adopted_from_node_plan_revision_id=flow_revision.adopted_from_node_plan_revision_id,
        adopted_at=flow_revision.adopted_at,
    )


def to_node_attempt_history_read(node_attempt: NodeAttempt) -> NodeAttemptHistoryRead:
    return NodeAttemptHistoryRead(
        id=node_attempt.id,
        flow_revision_id=node_attempt.flow_revision_id,
        flow_node_id=node_attempt.flow_node_id,
        flow_node_key=node_attempt.flow_node.node_key,
        flow_node_path=node_attempt.flow_node.node_path,
        number=node_attempt.number,
        status=node_attempt.status,
        retry_of_node_attempt_id=node_attempt.retry_of_node_attempt_id,
        failure_signature=node_attempt.failure_signature,
        started_at=node_attempt.started_at,
        finished_at=node_attempt.finished_at,
    )


def to_node_plan_revision_read(replan: NodePlanRevision) -> NodePlanRevisionRead:
    return NodePlanRevisionRead(
        id=replan.id,
        flow_id=replan.flow_id,
        requesting_flow_node_id=replan.requesting_flow_node_id,
        requesting_node_attempt_id=replan.requesting_node_attempt_id,
        base_flow_revision_id=replan.base_flow_revision_id,
        candidate_flow_revision_id=replan.candidate_flow_revision_id,
        reason=replan.reason,
        status=replan.status,
        patch_payload=replan.patch_payload,
        error_text=replan.error_text,
        validated_at=replan.validated_at,
        adopted_at=replan.adopted_at,
    )


def to_flow_operator_read(snapshot: FlowOperatorSnapshot) -> FlowOperatorRead:
    return FlowOperatorRead(
        flow=to_flow_inspect_response(snapshot.flow),
        task=to_task_read(snapshot.flow.task),
        revisions=[
            to_flow_revision_history_read(flow_revision)
            for flow_revision in snapshot.flow.flow_revisions
        ],
        replans=[
            to_node_plan_revision_read(replan) for replan in snapshot.flow.node_plan_revisions
        ],
        nodes=[
            to_flow_node_read(flow_node)
            for flow_revision in snapshot.flow.flow_revisions
            for flow_node in flow_revision.nodes
        ],
        attempts=[to_node_attempt_history_read(attempt) for attempt in snapshot.attempts],
        checkpoints=[to_checkpoint_read(checkpoint) for checkpoint in snapshot.checkpoints],
        approvals=[to_approval_read(approval) for approval in snapshot.flow.approvals],
        sessions=[NodeSessionRead.model_validate(session) for session in snapshot.sessions],
        manifests=[
            to_context_manifest_read(manifest) for manifest in snapshot.flow.context_manifests
        ],
        context_items=[to_context_item_read(item) for item in snapshot.context_items],
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
