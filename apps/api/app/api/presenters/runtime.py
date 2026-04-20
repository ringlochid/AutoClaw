from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import inspect as sa_inspect

from app.core.enums import (
    ApprovalStatus,
    ContextManifestStatus,
    FlowNodeState,
    NodeAttemptStatus,
    NodePlanRevisionStatus,
    WaitReason,
)
from app.db.models.runtime import (
    Approval,
    CompiledPlan,
    ContextItem,
    ContextManifest,
    ContextSpace,
    Flow,
    FlowEdge,
    FlowNode,
    FlowRevision,
    ManifestRoot,
    NodeAttempt,
    NodeCheckpoint,
    NodePlanRevision,
    NodeSession,
    Task,
    TaskCompose,
    TaskResourceBinding,
    WorkspaceRoot,
)
from app.runtime.context_visibility import is_context_item_visible_to_target
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
    FlowEdgeInspectRead,
    FlowInspectResponse,
    FlowNodeInspectRead,
    FlowNodeRead,
    FlowOperatorRead,
    FlowRevisionHistoryRead,
    FlowRevisionRead,
    FlowRuntimeSliceRead,
    FlowStartResponse,
    FlowSummaryRead,
    FlowTimelineSliceRead,
    FlowWorkerBundleRead,
    ManifestRootRead,
    NodeAttemptHistoryRead,
    NodeAttemptRead,
    NodePlanRevisionRead,
    NodeSessionAuditRead,
    NodeSessionSummaryRead,
    TaskComposeRead,
    TaskRead,
    TaskResourceBindingRead,
    TaskSummaryRead,
    WorkspaceRootRead,
)


@dataclass(frozen=True)
class _CurrentRuntimeReadContext:
    node: FlowNodeInspectRead | None
    attempt_id: UUID | None
    flow_node_id: UUID | None
    attempt: NodeAttempt | None
    session: NodeSession | None
    manifest: ContextManifest | None


def _loaded_collection(
    obj: object,
    attribute: str,
) -> list[Any]:
    inspection = sa_inspect(obj)
    assert inspection is not None
    if attribute in inspection.unloaded:
        return list(getattr(obj, "__dict__", {}).get(attribute) or [])
    return list(getattr(obj, attribute))


def _loaded_task_resource_bindings(task: Task) -> list[TaskResourceBinding]:
    return cast(list[TaskResourceBinding], _loaded_collection(task, "resource_bindings"))


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


def to_task_compose_read(task_compose: TaskCompose | None) -> TaskComposeRead | None:
    if task_compose is None:
        return None
    return TaskComposeRead(
        id=task_compose.id,
        task_id=task_compose.task_id,
        workflow_version_id=task_compose.workflow_version_id,
        compiled_plan_id=task_compose.compiled_plan_id,
        entrypoint=task_compose.entrypoint,
        status=task_compose.status,
        metadata=task_compose.metadata_,
        input_payload=task_compose.input_payload,
        context_refs=task_compose.context_refs,
        skill_dependencies=task_compose.skill_dependencies,
        workspace_root_uri=task_compose.workspace_root_uri,
        context_root_uri=task_compose.context_root_uri,
        manifest_root_uri=task_compose.manifest_root_uri,
        materialization_root=task_compose.materialization_root,
        superseded_at=task_compose.superseded_at,
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
        published_at=item.published_at,
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
        task=to_task_read(task),
        task_compose=None,
    )


def _loaded_attempts(flow_node: FlowNode) -> list[NodeAttempt]:
    return cast(list[NodeAttempt], _loaded_collection(flow_node, "attempts"))


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


def _latest_active_manifest(flow_node: FlowNode) -> ContextManifest | None:
    latest_attempt = _latest_attempt(flow_node)
    if latest_attempt is None:
        return None
    manifests: list[ContextManifest] = list(latest_attempt.__dict__.get("context_manifests") or [])
    if not manifests:
        return None
    active_manifests = [
        manifest
        for manifest in manifests
        if manifest.status in {ContextManifestStatus.PROJECTED, ContextManifestStatus.ACKED}
    ]
    if active_manifests:
        return active_manifests[-1]
    return manifests[-1]


def _runtime_activity_rank(
    attempt_status: NodeAttemptStatus | None,
    *,
    has_manifest: bool,
) -> int:
    if attempt_status in {NodeAttemptStatus.RUNNING, NodeAttemptStatus.BLOCKED}:
        return 2
    if has_manifest:
        return 1
    return 0


def _latest_timestamp_or_min(*timestamps: datetime | None) -> datetime:
    visible_timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
    return max(visible_timestamps) if visible_timestamps else datetime.min


def _flow_node_activity_key(flow_node: FlowNode) -> tuple[int, datetime, int]:
    latest_attempt = _latest_attempt(flow_node)
    latest_checkpoint = _latest_checkpoint(flow_node)
    latest_manifest = _latest_active_manifest(flow_node)
    node_session = _flow_node_session(flow_node)

    return (
        _runtime_activity_rank(
            latest_attempt.status if latest_attempt is not None else None,
            has_manifest=latest_manifest is not None,
        ),
        _latest_timestamp_or_min(
            latest_attempt.started_at if latest_attempt is not None else None,
            latest_attempt.finished_at if latest_attempt is not None else None,
            latest_checkpoint.created_at if latest_checkpoint is not None else None,
            latest_manifest.projected_at if latest_manifest is not None else None,
            latest_manifest.acked_at if latest_manifest is not None else None,
            node_session.last_seen_at if node_session is not None else None,
            node_session.ended_at if node_session is not None else None,
        ),
        flow_node.order_index,
    )


def _select_current_runtime_flow_node(flow: Flow) -> FlowNode | None:
    active_nodes = _loaded_revision_nodes(flow.active_flow_revision)
    if not active_nodes:
        return None
    return max(active_nodes, key=_flow_node_activity_key)


def _flow_node_read_activity_key(flow_node: FlowNodeInspectRead) -> tuple[int, datetime, int]:
    current_attempt = flow_node.current_attempt
    current_manifest = flow_node.current_manifest
    current_session = flow_node.current_session

    return (
        _runtime_activity_rank(
            current_attempt.status if current_attempt is not None else None,
            has_manifest=current_manifest is not None,
        ),
        _latest_timestamp_or_min(
            current_manifest.projected_at if current_manifest is not None else None,
            current_manifest.acked_at if current_manifest is not None else None,
            current_session.last_seen_at if current_session is not None else None,
            current_session.ended_at if current_session is not None else None,
        ),
        flow_node.order_index,
    )


def _select_current_runtime_node_read(flow_read: FlowInspectResponse) -> FlowNodeInspectRead | None:
    if not flow_read.nodes:
        return None
    return max(flow_read.nodes, key=_flow_node_read_activity_key)


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
    return cast(list[FlowNode], _loaded_collection(flow_revision, "nodes"))


def _loaded_revision_edges(flow_revision: FlowRevision | None) -> list[FlowEdge]:
    if flow_revision is None:
        return []
    return cast(list[FlowEdge], _loaded_collection(flow_revision, "edges"))


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


def _overlay_flow_read_runtime_state(
    flow_read: FlowInspectResponse,
    snapshot: FlowAuditSnapshot,
) -> FlowInspectResponse:
    latest_attempt_by_node: dict[UUID, NodeAttempt] = {}
    latest_session_by_node: dict[UUID, NodeSession] = {}
    latest_session_by_attempt: dict[UUID, NodeSession] = {}
    latest_manifest_by_attempt: dict[UUID, ContextManifest] = {}

    for attempt in snapshot.attempts:
        latest_attempt_by_node[attempt.flow_node_id] = attempt

    for session in snapshot.sessions:
        latest_session_by_node[session.flow_node_id] = session
        if session.node_attempt_id is not None:
            latest_session_by_attempt[session.node_attempt_id] = session

    for manifest in snapshot.flow.context_manifests:
        latest_manifest = latest_manifest_by_attempt.get(manifest.node_attempt_id)
        if latest_manifest is None or manifest.status in {
            ContextManifestStatus.PROJECTED,
            ContextManifestStatus.ACKED,
        }:
            latest_manifest_by_attempt[manifest.node_attempt_id] = manifest

    for node in flow_read.nodes:
        latest_attempt = latest_attempt_by_node.get(node.id)
        if node.current_attempt is None and latest_attempt is not None:
            node.current_attempt = _to_node_attempt_read(latest_attempt)

        latest_attempt_id = node.current_attempt.id if node.current_attempt is not None else None
        current_session: NodeSession | None = (
            latest_session_by_attempt.get(latest_attempt_id)
            if latest_attempt_id is not None
            else None
        )
        if current_session is None:
            current_session = latest_session_by_node.get(node.id)
        if node.current_session is None and current_session is not None:
            node.current_session = NodeSessionSummaryRead.model_validate(current_session)

        current_manifest: ContextManifest | None = (
            latest_manifest_by_attempt.get(latest_attempt_id)
            if latest_attempt_id is not None
            else None
        )
        if node.current_manifest is None and current_manifest is not None:
            node.current_manifest = to_context_manifest_read(current_manifest)

    return flow_read


def _pending_approvals(flow: Flow) -> list[Approval]:
    return [approval for approval in flow.approvals if approval.status == ApprovalStatus.PENDING]


def _projected_manifests(flow: Flow) -> list[ContextManifest]:
    return [
        manifest
        for manifest in flow.context_manifests
        if manifest.status == ContextManifestStatus.PROJECTED
    ]


def _latest_visible_checkpoint(nodes: list[FlowNode]) -> NodeCheckpoint | None:
    checkpoints: list[NodeCheckpoint] = []
    for node in nodes:
        checkpoint = _latest_checkpoint(node)
        if checkpoint is not None:
            checkpoints.append(checkpoint)
    if not checkpoints:
        return None
    return max(
        checkpoints,
        key=lambda checkpoint: (
            checkpoint.created_at,
            checkpoint.sequence_no,
            str(checkpoint.id),
        ),
    )


def _resolve_current_runtime_read_context(
    snapshot: FlowAuditSnapshot,
    flow_read: FlowInspectResponse,
) -> _CurrentRuntimeReadContext:
    current_node = _select_current_runtime_node_read(flow_read)
    current_attempt_id = (
        current_node.current_attempt.id
        if current_node is not None and current_node.current_attempt is not None
        else None
    )
    current_flow_node_id = current_node.id if current_node is not None else None
    current_attempt = next(
        (attempt for attempt in snapshot.attempts if attempt.id == current_attempt_id),
        None,
    )

    current_session = None
    if current_node is not None and current_node.current_session is not None:
        current_session = next(
            (
                session
                for session in snapshot.sessions
                if session.id == current_node.current_session.id
            ),
            None,
        )
    if current_session is None and current_flow_node_id is not None:
        current_session = next(
            (
                session
                for session in reversed(snapshot.sessions)
                if session.flow_node_id == current_flow_node_id
                and session.node_attempt_id in {None, current_attempt_id}
            ),
            None,
        )

    current_manifest = None
    if current_node is not None and current_node.current_manifest is not None:
        current_manifest = next(
            (
                manifest
                for manifest in snapshot.flow.context_manifests
                if manifest.id == current_node.current_manifest.id
            ),
            None,
        )
    if current_manifest is None and current_attempt_id is not None:
        current_manifest = next(
            (
                manifest
                for manifest in reversed(snapshot.flow.context_manifests)
                if manifest.node_attempt_id == current_attempt_id
                and manifest.status
                in {ContextManifestStatus.PROJECTED, ContextManifestStatus.ACKED}
            ),
            None,
        )

    return _CurrentRuntimeReadContext(
        node=current_node,
        attempt_id=current_attempt_id,
        flow_node_id=current_flow_node_id,
        attempt=current_attempt,
        session=current_session,
        manifest=current_manifest,
    )


def to_flow_summary_read(flow: Flow) -> FlowSummaryRead:
    active_revision = flow.active_flow_revision
    nodes = _loaded_revision_nodes(active_revision)
    latest_checkpoint = _latest_visible_checkpoint(nodes)
    pending_approval_count = len(_pending_approvals(flow))
    projected_manifest_count = len(_projected_manifests(flow))

    return FlowSummaryRead(
        id=flow.id,
        task=to_task_summary_read(flow.task),
        status=flow.status,
        execution_no=flow.execution_no,
        seed_compiled_plan_id=flow.seed_compiled_plan_id,
        active_flow_revision_id=flow.active_flow_revision_id,
        node_count=len(nodes),
        done_node_count=len([node for node in nodes if node.state == FlowNodeState.DONE]),
        blocked_node_count=len(
            [
                node
                for node in nodes
                if node.state in {FlowNodeState.WAITING, FlowNodeState.PAUSED, FlowNodeState.FAILED}
            ]
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


def _patch_changes_launch_binding_payload(patch_payload: dict[str, Any]) -> bool:
    if patch_payload.get("task_defaults"):
        return True
    if patch_payload.get("defaults"):
        return True
    if patch_payload.get("skill_refs") or patch_payload.get("skill_bindings"):
        return True
    for node in patch_payload.get("nodes", []):
        if isinstance(node, dict) and node.get("resources"):
            return True
    return False


def to_node_plan_revision_read(replan: NodePlanRevision) -> NodePlanRevisionRead:
    remint_required = _patch_changes_launch_binding_payload(replan.patch_payload)
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
        task_compose_decision={
            "remint_required": remint_required,
            "reason": ("launch_binding_changed" if remint_required else "structural_replan_only"),
        },
    )


def to_flow_operator_read(flow: Flow) -> FlowOperatorRead:
    pending_approvals = _pending_approvals(flow)
    projected_manifest_count = len(_projected_manifests(flow))
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
                            if "node_session" in manifest.__dict__
                            and manifest.node_session is not None
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
    compiled_plan: CompiledPlan | None = None,
) -> FlowWorkerBundleRead:
    flow_read = _overlay_flow_read_runtime_state(
        to_flow_inspect_response(snapshot.flow),
        snapshot,
    )
    current_node = next(
        (node for node in flow_read.nodes if node.id == current_manifest.flow_node_id), None
    )
    current_attempt = next(
        (
            attempt
            for attempt in snapshot.attempts
            if attempt.id == current_manifest.node_attempt_id
        ),
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
        if is_context_item_visible_to_target(
            item,
            flow_id=snapshot.flow.id,
            flow_node_id=current_manifest.flow_node_id,
            node_attempt_id=current_manifest.node_attempt_id,
        )
    ]
    return FlowWorkerBundleRead(
        flow=flow_read,
        task=to_task_read(snapshot.flow.task),
        compiled_plan=compiled_plan_read,
        current_node=current_node,
        current_attempt=(
            to_node_attempt_history_read(current_attempt) if current_attempt else None
        ),
        current_session=(
            NodeSessionAuditRead.model_validate(current_session)
            if current_session is not None
            else None
        ),
        current_manifest=to_context_manifest_audit_read(current_manifest),
        task_compose=to_task_compose_read(task_compose),
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


def to_flow_runtime_slice_read(
    snapshot: FlowAuditSnapshot,
    *,
    checkpoint_limit: int = 10,
    approval_limit: int = 10,
    manifest_limit: int = 5,
    context_limit: int = 10,
    event_limit: int = 20,
) -> FlowRuntimeSliceRead:
    flow_read = _overlay_flow_read_runtime_state(
        to_flow_inspect_response(snapshot.flow),
        snapshot,
    )
    runtime_context = _resolve_current_runtime_read_context(snapshot, flow_read)

    if runtime_context.attempt_id is not None:
        checkpoint_source = [
            checkpoint
            for checkpoint in snapshot.checkpoints
            if checkpoint.node_attempt_id == runtime_context.attempt_id
        ]
        manifest_source = [
            manifest
            for manifest in snapshot.flow.context_manifests
            if manifest.node_attempt_id == runtime_context.attempt_id
        ]
        visible_context_items = [
            item
            for item in snapshot.context_items
            if is_context_item_visible_to_target(
                item,
                flow_id=snapshot.flow.id,
                flow_node_id=runtime_context.flow_node_id,
                node_attempt_id=runtime_context.attempt_id,
            )
        ]
    else:
        checkpoint_source = snapshot.checkpoints
        manifest_source = snapshot.flow.context_manifests
        visible_context_items = snapshot.context_items

    pending_approvals = _pending_approvals(snapshot.flow)
    approval_source = pending_approvals or list(snapshot.flow.approvals)

    all_events = _to_flow_audit_events(snapshot)
    if runtime_context.attempt_id is not None and runtime_context.flow_node_id is not None:
        event_source = [
            event
            for event in all_events
            if event.node_attempt_id in {None, runtime_context.attempt_id}
            or event.flow_node_id == runtime_context.flow_node_id
        ]
    else:
        event_source = all_events

    return FlowRuntimeSliceRead(
        flow=flow_read,
        task=to_task_read(snapshot.flow.task),
        current_node=runtime_context.node,
        current_attempt=(
            to_node_attempt_history_read(runtime_context.attempt)
            if runtime_context.attempt
            else None
        ),
        current_session=(
            NodeSessionAuditRead.model_validate(runtime_context.session)
            if runtime_context.session is not None
            else None
        ),
        current_manifest=(
            to_context_manifest_audit_read(runtime_context.manifest)
            if runtime_context.manifest is not None
            else None
        ),
        recent_checkpoints=[
            to_checkpoint_read(checkpoint) for checkpoint in checkpoint_source[-checkpoint_limit:]
        ],
        approvals=[to_approval_read(approval) for approval in approval_source[-approval_limit:]],
        recent_manifests=[
            to_context_manifest_audit_read(manifest)
            for manifest in manifest_source[-manifest_limit:]
        ],
        context_items=[
            to_context_item_audit_read(item) for item in visible_context_items[-context_limit:]
        ],
        events=event_source[-event_limit:],
    )


def to_flow_timeline_slice_read(
    snapshot: FlowAuditSnapshot,
    *,
    context_limit: int = 10,
    event_limit: int = 20,
) -> FlowTimelineSliceRead:
    flow_read = _overlay_flow_read_runtime_state(
        to_flow_inspect_response(snapshot.flow),
        snapshot,
    )
    runtime_context = _resolve_current_runtime_read_context(snapshot, flow_read)
    return FlowTimelineSliceRead(
        flow_id=snapshot.flow.id,
        flow_status=snapshot.flow.status,
        current_flow_node_id=runtime_context.flow_node_id,
        current_node_key=(
            runtime_context.node.node_key if runtime_context.node is not None else None
        ),
        current_node_attempt_id=runtime_context.attempt_id,
        events=_to_flow_audit_events(snapshot)[-event_limit:],
        context_items=[
            to_context_item_audit_read(item) for item in snapshot.context_items[-context_limit:]
        ],
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
