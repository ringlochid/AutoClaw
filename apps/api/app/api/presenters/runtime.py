from __future__ import annotations

from uuid import UUID

from sqlalchemy import inspect as sa_inspect

from app.core.enums import ApprovalStatus, NodePlanRevisionStatus, WaitReason
from app.db.models.runtime import (
    Approval,
    CompiledPlan,
    ContextItem,
    ContextManifest,
    ContextSpace,
    Flow,
    FlowNode,
    FlowRevision,
    ManifestRoot,
    NodeAttempt,
    NodeCheckpoint,
    NodePlanRevision,
    NodeSession,
    RuntimeContainer,
    RuntimeImage,
    Task,
    TaskCompose,
    TaskImage,
    TaskResourceBinding,
    WorkspaceRoot,
)
from app.runtime.control import (
    current_wait_reason as runtime_current_wait_reason,
)
from app.runtime.control import (
    is_operator_retryable,
)
from app.runtime.read_models import FlowAuditSnapshot
from app.schemas.runtime import (
    ApprovalRead,
    ApprovalSummaryRead,
    CheckpointRead,
    CompiledPlanEdgeRead,
    CompiledPlanNodeRead,
    CompiledPlanRead,
    ContextItemAuditRead,
    ContextManifestAuditRead,
    ContextManifestRead,
    ContextSpaceRead,
    FlowAuditEventRead,
    FlowAuditEventType,
    FlowAuditRead,
    FlowWorkerBundleRead,
    FlowEdgeInspectRead,
    FlowInspectResponse,
    FlowNodeInspectRead,
    FlowNodeRead,
    FlowOperatorRead,
    FlowRevisionHistoryRead,
    FlowRevisionRead,
    FlowStartResponse,
    FlowSummaryRead,
    ManifestRootRead,
    NodeAttemptHistoryRead,
    NodeAttemptRead,
    NodePlanRevisionRead,
    NodeSessionAuditRead,
    NodeSessionSummaryRead,
    RuntimeContainerRead,
    RuntimeImageRead,
    TaskComposeRead,
    TaskImageRead,
    TaskRead,
    TaskResourceBindingRead,
    TaskSummaryRead,
    WorkspaceRootRead,
)


def _loaded_task_resource_bindings(task: Task) -> list[TaskResourceBinding]:
    inspection = sa_inspect(task)
    if "resource_bindings" in inspection.unloaded:
        return []
    return list(task.resource_bindings)


def _workspace_root_read(workspace_root: WorkspaceRoot | None) -> WorkspaceRootRead | None:
    if workspace_root is None:
        return None
    return WorkspaceRootRead(
        id=workspace_root.id,
        scope=workspace_root.scope,
        key=workspace_root.key,
        title=workspace_root.title,
        storage_uri=workspace_root.storage_uri,
        kind=workspace_root.kind,
        mode=workspace_root.mode,
        status=workspace_root.status,
        content_hash=workspace_root.content_hash,
        metadata=workspace_root.metadata_,
    )


def _context_space_read(context_space: ContextSpace | None) -> ContextSpaceRead | None:
    if context_space is None:
        return None
    return ContextSpaceRead(
        id=context_space.id,
        scope=context_space.scope,
        key=context_space.key,
        title=context_space.title,
        storage_uri=context_space.storage_uri,
        source_workspace_root_id=context_space.source_workspace_root_id,
        status=context_space.status,
        content_hash=context_space.content_hash,
        metadata=context_space.metadata_,
    )


def _manifest_root_read(manifest_root: ManifestRoot | None) -> ManifestRootRead | None:
    if manifest_root is None:
        return None
    return ManifestRootRead(
        id=manifest_root.id,
        task_id=manifest_root.task_id,
        key=manifest_root.key,
        storage_uri=manifest_root.storage_uri,
        status=manifest_root.status,
        metadata=manifest_root.metadata_,
    )


def _task_resource_binding_read(binding: TaskResourceBinding) -> TaskResourceBindingRead:
    inspection = sa_inspect(binding)
    workspace_root = None if "workspace_root" in inspection.unloaded else binding.workspace_root
    context_space = None if "context_space" in inspection.unloaded else binding.context_space
    manifest_root = None if "manifest_root" in inspection.unloaded else binding.manifest_root
    return TaskResourceBindingRead(
        id=binding.id,
        task_id=binding.task_id,
        binding_role=binding.binding_role,
        workspace_root_id=binding.workspace_root_id,
        context_space_id=binding.context_space_id,
        manifest_root_id=binding.manifest_root_id,
        mode=binding.mode,
        read_only=binding.read_only,
        required=binding.required,
        metadata=binding.metadata_,
        workspace_root=_workspace_root_read(workspace_root),
        context_space=_context_space_read(context_space),
        manifest_root=_manifest_root_read(manifest_root),
    )


def to_task_read(task: Task) -> TaskRead:
    return TaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        input_payload=task.input_payload,
        resource_bindings=[
            _task_resource_binding_read(binding) for binding in _loaded_task_resource_bindings(task)
        ],
    )


def to_task_image_read(task_image: TaskImage | None) -> TaskImageRead | None:
    if task_image is None:
        return None
    return TaskImageRead(
        id=task_image.id,
        image_hash=task_image.image_hash,
        source_task_id=task_image.source_task_id,
        spec_payload=task_image.spec_payload,
    )


def to_task_compose_read(task_compose: TaskCompose | None) -> TaskComposeRead | None:
    if task_compose is None:
        return None
    return TaskComposeRead(
        id=task_compose.id,
        task_id=task_compose.task_id,
        task_image_id=task_compose.task_image_id,
        status=task_compose.status,
        materialization_root=task_compose.materialization_root,
        compose_payload=task_compose.compose_payload,
        task_image=to_task_image_read(task_compose.task_image),
    )


def to_runtime_image_read(runtime_image: RuntimeImage | None) -> RuntimeImageRead | None:
    if runtime_image is None:
        return None
    return RuntimeImageRead(
        id=runtime_image.id,
        image_hash=runtime_image.image_hash,
        compiled_plan_node_id=runtime_image.compiled_plan_node_id,
        spec_payload=runtime_image.spec_payload,
    )


def to_runtime_container_read(runtime_container: RuntimeContainer | None) -> RuntimeContainerRead | None:
    if runtime_container is None:
        return None
    return RuntimeContainerRead(
        id=runtime_container.id,
        task_id=runtime_container.task_id,
        task_compose_id=runtime_container.task_compose_id,
        runtime_image_id=runtime_container.runtime_image_id,
        flow_id=runtime_container.flow_id,
        flow_node_id=runtime_container.flow_node_id,
        node_session_id=runtime_container.node_session_id,
        current_node_attempt_id=runtime_container.current_node_attempt_id,
        current_context_manifest_id=runtime_container.current_context_manifest_id,
        backend_kind=runtime_container.backend_kind,
        backend_handle=runtime_container.backend_handle,
        status=runtime_container.status,
        bootstrap_state=runtime_container.bootstrap_state,
        container_payload=runtime_container.container_payload,
        started_at=runtime_container.started_at,
        last_seen_at=runtime_container.last_seen_at,
        ended_at=runtime_container.ended_at,
        runtime_image=to_runtime_image_read(runtime_container.runtime_image),
    )


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


def to_context_item_audit_read(item: ContextItem) -> ContextItemAuditRead:
    return ContextItemAuditRead(
        id=item.id,
        task_id=item.task_id,
        flow_id=item.flow_id,
        flow_node_id=item.flow_node_id,
        node_attempt_id=item.node_attempt_id,
        scope=item.scope,
        kind=item.kind,
        status=item.status,
        title=item.title,
        storage_uri=item.storage_uri,
        content_hash=item.content_hash,
        metadata=item.metadata_,
        published_by=item.published_by,
    )


def _context_manifest_payload(manifest: ContextManifest) -> dict[str, object]:
    node_session = manifest.node_session if "node_session" in manifest.__dict__ else None
    return {
        "id": manifest.id,
        "flow_id": manifest.flow_id,
        "flow_node_id": manifest.flow_node_id,
        "node_attempt_id": manifest.node_attempt_id,
        "node_session_id": manifest.node_session_id,
        "node_session_key": (
            node_session.provider_session_key if node_session is not None else None
        ),
        "manifest_no": manifest.manifest_no,
        "manifest_payload": manifest.manifest_payload,
        "manifest_hash": manifest.manifest_hash,
        "manifest_root_id": manifest.manifest_root_id,
        "status": manifest.status,
        "projected_at": manifest.projected_at,
        "acked_at": manifest.acked_at,
        "ack_checkpoint_id": manifest.ack_checkpoint_id,
    }


def to_context_manifest_read(manifest: ContextManifest) -> ContextManifestRead:
    return ContextManifestRead.model_validate(_context_manifest_payload(manifest))


def to_context_manifest_audit_read(manifest: ContextManifest) -> ContextManifestAuditRead:
    return ContextManifestAuditRead.model_validate(_context_manifest_payload(manifest))


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


def _loaded_attempts(flow_node: FlowNode) -> list[NodeAttempt]:
    inspection = sa_inspect(flow_node)
    if "attempts" in inspection.unloaded:
        return list(flow_node.__dict__.get("attempts") or [])
    return list(flow_node.attempts)


def _latest_attempt(flow_node: FlowNode) -> NodeAttempt | None:
    attempts = _loaded_attempts(flow_node)
    return attempts[-1] if attempts else None


def _latest_checkpoint(flow_node: FlowNode) -> NodeCheckpoint | None:
    latest_attempt = _latest_attempt(flow_node)
    if latest_attempt is None:
        return None
    checkpoints: list[NodeCheckpoint] = list(latest_attempt.__dict__.get("checkpoints") or [])
    visible = [checkpoint for checkpoint in checkpoints if checkpoint.sequence_no > 0]
    if not visible:
        return None
    return visible[-1]


def _latest_manifest(flow_node: FlowNode) -> ContextManifest | None:
    latest_attempt = _latest_attempt(flow_node)
    if latest_attempt is None:
        return None
    manifests: list[ContextManifest] = list(latest_attempt.__dict__.get("context_manifests") or [])
    if not manifests:
        return None
    return manifests[-1]


def _current_wait_reason(flow: Flow, flow_node: FlowNode) -> WaitReason | None:
    inspection = sa_inspect(flow_node)
    if "attempts" in inspection.unloaded or "incoming_edges" in inspection.unloaded:
        return None
    return runtime_current_wait_reason(flow, flow_node)


def _node_retryable(flow: Flow, flow_node: FlowNode) -> bool:
    inspection = sa_inspect(flow_node)
    if "attempts" in inspection.unloaded:
        return False
    return is_operator_retryable(flow, flow_node)


def _flow_node_effective_payload(flow_node: FlowNode) -> dict[str, object]:
    inspection = sa_inspect(flow_node)
    if "source_compiled_plan_node" in inspection.unloaded:
        return {}
    source_node = flow_node.source_compiled_plan_node
    return source_node.effective_payload if source_node is not None else {}


def _flow_node_session(flow_node: FlowNode) -> NodeSession | None:
    inspection = sa_inspect(flow_node)
    if "node_session" in inspection.unloaded:
        return None
    return flow_node.node_session


def _loaded_revision_nodes(flow_revision: FlowRevision | None) -> list[FlowNode]:
    if flow_revision is None:
        return []
    inspection = sa_inspect(flow_revision)
    if "nodes" in inspection.unloaded:
        return list(flow_revision.__dict__.get("nodes") or [])
    return list(flow_revision.nodes)


def _loaded_revision_edges(flow_revision: FlowRevision | None) -> list:
    if flow_revision is None:
        return []
    inspection = sa_inspect(flow_revision)
    if "edges" in inspection.unloaded:
        return list(flow_revision.__dict__.get("edges") or [])
    return list(flow_revision.edges)


def _workflow_version_id(flow_revision: FlowRevision | None) -> UUID | None:
    if flow_revision is None:
        return None
    inspection = sa_inspect(flow_revision)
    if "compiled_plan" in inspection.unloaded:
        return None
    workflow_version_id = flow_revision.compiled_plan.workflow_version_id
    return workflow_version_id if isinstance(workflow_version_id, UUID) else None


def _to_node_attempt_read(node_attempt: NodeAttempt | None) -> NodeAttemptRead | None:
    if node_attempt is None:
        return None
    return NodeAttemptRead.model_validate(node_attempt)


def _to_node_session_read(node_session: NodeSession | None) -> NodeSessionSummaryRead | None:
    if node_session is None:
        return None
    return NodeSessionSummaryRead.model_validate(node_session)


def to_flow_inspect_response(flow: Flow) -> FlowInspectResponse:
    active_revision = flow.active_flow_revision
    nodes: list[FlowNodeInspectRead] = []

    if active_revision is not None:
        for flow_node in _loaded_revision_nodes(active_revision):
            current_attempt = _latest_attempt(flow_node)
            current_manifest = _latest_manifest(flow_node)
            nodes.append(
                FlowNodeInspectRead(
                    id=flow_node.id,
                    source_compiled_plan_node_id=flow_node.source_compiled_plan_node_id,
                    parent_flow_node_id=flow_node.parent_flow_node_id,
                    node_key=flow_node.node_key,
                    node_path=flow_node.node_path,
                    state=flow_node.state,
                    order_index=flow_node.order_index,
                    status_payload=flow_node.status_payload,
                    effective_payload=_flow_node_effective_payload(flow_node),
                    current_attempt=_to_node_attempt_read(current_attempt),
                    current_session=_to_node_session_read(_flow_node_session(flow_node)),
                    current_manifest=(
                        to_context_manifest_read(current_manifest)
                        if current_manifest is not None
                        else None
                    ),
                    current_wait_reason=_current_wait_reason(flow, flow_node),
                    retryable=_node_retryable(flow, flow_node),
                )
            )

    edges = [
        FlowEdgeInspectRead(
            from_node_key=edge.from_flow_node.node_key,
            to_node_key=edge.to_flow_node.node_key,
            edge_kind=edge.edge_kind,
            condition_expr=edge.condition_expr,
            order_index=index,
        )
        for index, edge in enumerate(_loaded_revision_edges(active_revision))
        if "from_flow_node" not in sa_inspect(edge).unloaded
        and "to_flow_node" not in sa_inspect(edge).unloaded
    ]

    compiled_plan_id = active_revision.compiled_plan_id if active_revision is not None else None
    workflow_version_id = _workflow_version_id(active_revision)

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
        compiled_plan_id=compiled_plan_id,
        workflow_version_id=workflow_version_id,
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
    )


def to_flow_summary_read(flow: Flow) -> FlowSummaryRead:
    active_revision = flow.active_flow_revision
    nodes = _loaded_revision_nodes(active_revision)
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
    workflow_version_id = _workflow_version_id(flow_revision)
    if workflow_version_id is None:
        raise ValueError("flow revision history requires compiled plan workflow version")

    return FlowRevisionHistoryRead(
        id=flow_revision.id,
        revision_no=flow_revision.revision_no,
        compiled_plan_id=flow_revision.compiled_plan_id,
        workflow_version_id=workflow_version_id,
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


def to_flow_operator_read(flow: Flow) -> FlowOperatorRead:
    pending_approvals = [
        approval for approval in flow.approvals if approval.status.value == "pending"
    ]
    projected_manifest_count = len(
        [manifest for manifest in flow.context_manifests if manifest.status.value == "projected"]
    )
    return FlowOperatorRead(
        flow=to_flow_inspect_response(flow),
        task=to_task_read(flow.task),
        pending_approval_count=len(pending_approvals),
        projected_manifest_count=projected_manifest_count,
        approvals=[ApprovalSummaryRead.model_validate(approval) for approval in pending_approvals],
    )


def _to_flow_audit_events(snapshot: FlowAuditSnapshot) -> list[FlowAuditEventRead]:
    flow = snapshot.flow
    events: list[FlowAuditEventRead] = []

    for checkpoint in snapshot.checkpoints:
        events.append(
            FlowAuditEventRead(
                type=FlowAuditEventType.CHECKPOINT_RECORDED,
                occurred_at=checkpoint.created_at,
                flow_id=flow.id,
                flow_node_id=checkpoint.flow_node_id,
                node_attempt_id=checkpoint.node_attempt_id,
                data={"checkpoint_id": str(checkpoint.id), "status": checkpoint.status.value},
            )
        )

    for approval in snapshot.flow.approvals:
        events.append(
            FlowAuditEventRead(
                type=FlowAuditEventType.APPROVAL_REQUESTED,
                occurred_at=approval.created_at,
                flow_id=flow.id,
                flow_node_id=approval.flow_node_id,
                node_attempt_id=approval.node_attempt_id,
                data={"approval_id": str(approval.id), "reason": approval.reason},
            )
        )
        if approval.status != ApprovalStatus.PENDING:
            events.append(
                FlowAuditEventRead(
                    type=FlowAuditEventType.APPROVAL_RESOLVED,
                    occurred_at=approval.updated_at,
                    flow_id=flow.id,
                    flow_node_id=approval.flow_node_id,
                    node_attempt_id=approval.node_attempt_id,
                    data={
                        "approval_id": str(approval.id),
                        "status": approval.status.value,
                    },
                )
            )

    for manifest in snapshot.flow.context_manifests:
        events.append(
            FlowAuditEventRead(
                type=FlowAuditEventType.CONTEXT_MANIFEST_PROJECTED,
                occurred_at=manifest.projected_at,
                flow_id=flow.id,
                flow_node_id=manifest.flow_node_id,
                node_attempt_id=manifest.node_attempt_id,
                data={
                    "manifest_id": str(manifest.id),
                    "status": manifest.status.value,
                    "manifest_hash": manifest.manifest_hash,
                    "node_session_key": (
                        manifest.node_session.provider_session_key
                        if "node_session" in manifest.__dict__ and manifest.node_session is not None
                        else None
                    ),
                },
            )
        )
        if manifest.acked_at is not None:
            events.append(
                FlowAuditEventRead(
                    type=FlowAuditEventType.CONTEXT_MANIFEST_ACKNOWLEDGED,
                    occurred_at=manifest.acked_at,
                    flow_id=flow.id,
                    flow_node_id=manifest.flow_node_id,
                    node_attempt_id=manifest.node_attempt_id,
                    data={
                        "manifest_id": str(manifest.id),
                        "manifest_hash": manifest.manifest_hash,
                        "ack_checkpoint_id": (
                            str(manifest.ack_checkpoint_id)
                            if manifest.ack_checkpoint_id is not None
                            else None
                        ),
                        "node_session_key": (
                            manifest.node_session.provider_session_key
                            if "node_session" in manifest.__dict__ and manifest.node_session is not None
                            else None
                        ),
                    },
                )
            )

    for replan in snapshot.flow.node_plan_revisions:
        events.append(
            FlowAuditEventRead(
                type=FlowAuditEventType.REVISION_REQUESTED,
                occurred_at=replan.created_at,
                flow_id=flow.id,
                flow_node_id=replan.requesting_flow_node_id,
                node_attempt_id=replan.requesting_node_attempt_id,
                data={"replan_id": str(replan.id), "status": replan.status.value},
            )
        )
        if replan.status == NodePlanRevisionStatus.ADOPTED and replan.adopted_at is not None:
            events.append(
                FlowAuditEventRead(
                    type=FlowAuditEventType.REVISION_ADOPTED,
                    occurred_at=replan.adopted_at,
                    flow_id=flow.id,
                    flow_node_id=replan.requesting_flow_node_id,
                    node_attempt_id=replan.requesting_node_attempt_id,
                    data={"replan_id": str(replan.id)},
                )
            )

    events.sort(key=lambda event: event.occurred_at)
    return events


def to_flow_audit_read(snapshot: FlowAuditSnapshot) -> FlowAuditRead:
    return FlowAuditRead(
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
            for flow_node in _loaded_revision_nodes(flow_revision)
        ],
        attempts=[to_node_attempt_history_read(attempt) for attempt in snapshot.attempts],
        checkpoints=[to_checkpoint_read(checkpoint) for checkpoint in snapshot.checkpoints],
        approvals=[to_approval_read(approval) for approval in snapshot.flow.approvals],
        sessions=[NodeSessionAuditRead.model_validate(session) for session in snapshot.sessions],
        manifests=[
            to_context_manifest_audit_read(manifest) for manifest in snapshot.flow.context_manifests
        ],
        context_items=[to_context_item_audit_read(item) for item in snapshot.context_items],
        events=_to_flow_audit_events(snapshot),
    )


def to_flow_worker_bundle_read(
    snapshot: FlowAuditSnapshot,
    *,
    current_manifest: ContextManifest,
    task_compose: TaskCompose | None,
    runtime_container: RuntimeContainer | None,
    compiled_plan: CompiledPlan | None = None,
) -> FlowWorkerBundleRead:
    flow_read = to_flow_inspect_response(snapshot.flow)
    current_node = next((node for node in flow_read.nodes if node.id == current_manifest.flow_node_id), None)
    current_attempt = next(
        (attempt for attempt in snapshot.attempts if attempt.id == current_manifest.node_attempt_id),
        None,
    )
    current_session = current_manifest.node_session
    compiled_plan_read = to_compiled_plan_read(compiled_plan) if compiled_plan is not None else None
    relevant_manifests = [
        manifest
        for manifest in snapshot.flow.context_manifests
        if manifest.node_attempt_id == current_manifest.node_attempt_id
    ]
    relevant_events = [
        event
        for event in _to_flow_audit_events(snapshot)
        if event.node_attempt_id in {None, current_manifest.node_attempt_id}
        or event.flow_node_id == current_manifest.flow_node_id
    ]
    relevant_context_items = [
        item
        for item in snapshot.context_items
        if item.flow_id in {None, snapshot.flow.id}
        and (
            item.node_attempt_id in {None, current_manifest.node_attempt_id}
            or item.scope.value in {"task_shared", "flow_shared"}
        )
    ]
    return FlowWorkerBundleRead(
        flow=flow_read,
        task=to_task_read(snapshot.flow.task),
        compiled_plan=compiled_plan_read,
        current_node=current_node,
        current_attempt=(to_node_attempt_history_read(current_attempt) if current_attempt else None),
        current_session=(
            NodeSessionAuditRead.model_validate(current_session) if current_session is not None else None
        ),
        current_manifest=to_context_manifest_audit_read(current_manifest),
        task_compose=to_task_compose_read(task_compose),
        runtime_container=to_runtime_container_read(runtime_container),
        recent_checkpoints=[
            to_checkpoint_read(checkpoint)
            for checkpoint in snapshot.checkpoints
            if checkpoint.node_attempt_id == current_manifest.node_attempt_id
        ][-10:],
        approvals=[
            to_approval_read(approval)
            for approval in snapshot.flow.approvals
            if approval.node_attempt_id in {None, current_manifest.node_attempt_id}
        ],
        recent_manifests=[
            to_context_manifest_audit_read(manifest) for manifest in relevant_manifests[-5:]
        ],
        context_items=[to_context_item_audit_read(item) for item in relevant_context_items[-10:]],
        events=relevant_events[-20:],
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
