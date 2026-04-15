from __future__ import annotations

from collections.abc import Iterable

from app.core.enums import (
    ApprovalStatus,
    ContextManifestStatus,
    FlowNodeState,
    FlowStatus,
    NodeAttemptStatus,
    NodeSessionStatus,
    WaitReason,
)
from app.core.errors import ConflictError
from app.db.models.runtime import (
    Approval,
    ContextManifest,
    Flow,
    FlowNode,
    NodeAttempt,
    NodeCheckpoint,
    NodeSession,
)
from app.runtime.scheduler import all_nodes_done, ordered_nodes
from app.runtime.state import set_flow_status, utcnow_naive

TERMINAL_ATTEMPT_STATUSES = {
    NodeAttemptStatus.SUCCEEDED,
    NodeAttemptStatus.FAILED,
    NodeAttemptStatus.CANCELLED,
    NodeAttemptStatus.ABORTED,
}

ACTIVE_ATTEMPT_STATUSES = {
    NodeAttemptStatus.PENDING,
    NodeAttemptStatus.RUNNING,
    NodeAttemptStatus.BLOCKED,
}

__all__ = [
    "ACTIVE_ATTEMPT_STATUSES",
    "abort_attempt",
    "cancel_attempt",
    "end_node_session",
    "ensure_current_attempt",
    "expire_pending_approvals",
    "idle_node_session",
    "is_waiting_attempt_resumable",
    "latest_attempt",
    "latest_checkpoint",
    "pending_approvals",
    "projected_manifests",
    "refresh_flow_status",
    "supersede_projected_manifests",
    "waiting_block_reason",
]


def _relation_loaded(entity: object, name: str) -> bool:
    return name in getattr(entity, "__dict__", {})


def latest_attempt(flow_node: FlowNode) -> NodeAttempt | None:
    if not _relation_loaded(flow_node, "attempts"):
        return None
    return flow_node.attempts[-1] if flow_node.attempts else None


def latest_checkpoint(node_attempt: NodeAttempt) -> NodeCheckpoint | None:
    if not _relation_loaded(node_attempt, "checkpoints"):
        return None
    return node_attempt.checkpoints[-1] if node_attempt.checkpoints else None


def ensure_current_attempt(
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
    *,
    allowed_statuses: set[NodeAttemptStatus] | None = None,
    require_current_session: bool = False,
    node_session: NodeSession | None = None,
) -> None:
    current_attempt = latest_attempt(flow_node)
    if current_attempt is None or current_attempt.id != node_attempt.id:
        raise ConflictError("Node attempt is no longer current for this flow node")
    if (
        flow.active_flow_revision_id is not None
        and node_attempt.flow_revision_id != flow.active_flow_revision_id
    ):
        raise ConflictError("Node attempt does not belong to the active flow revision")
    if allowed_statuses is not None and node_attempt.status not in allowed_statuses:
        allowed = ", ".join(sorted(status.value for status in allowed_statuses))
        raise ConflictError(
            f"Node attempt is not eligible for this operation; expected one of: {allowed}"
        )
    if node_attempt.status in TERMINAL_ATTEMPT_STATUSES and (
        allowed_statuses is None or node_attempt.status not in allowed_statuses
    ):
        raise ConflictError("Node attempt is already terminal")
    if require_current_session:
        if node_session is None:
            raise ConflictError("Node session is required for this operation")
        if node_session.node_attempt_id != node_attempt.id:
            raise ConflictError("Node session is no longer bound to this node attempt")


def pending_approvals(
    approvals: Iterable[Approval],
    *,
    flow_node_id: object | None = None,
    node_attempt_id: object | None = None,
) -> list[Approval]:
    return [
        approval
        for approval in approvals
        if approval.status == ApprovalStatus.PENDING
        and (
            flow_node_id is None
            or approval.flow_node_id == flow_node_id
            or approval.flow_node_id is None
        )
        and (
            node_attempt_id is None
            or approval.node_attempt_id == node_attempt_id
            or approval.node_attempt_id is None
        )
    ]


def projected_manifests(
    manifests: Iterable[ContextManifest],
    *,
    node_attempt_id: object | None = None,
) -> list[ContextManifest]:
    return [
        manifest
        for manifest in manifests
        if manifest.status == ContextManifestStatus.PROJECTED
        and (node_attempt_id is None or manifest.node_attempt_id == node_attempt_id)
    ]


def waiting_block_reason(
    flow: Flow, flow_node: FlowNode, node_attempt: NodeAttempt | None
) -> WaitReason | None:
    if node_attempt is None:
        return None
    if pending_approvals(
        flow.approvals,
        flow_node_id=flow_node.id,
        node_attempt_id=node_attempt.id,
    ):
        return WaitReason.APPROVAL
    if projected_manifests(flow.context_manifests, node_attempt_id=node_attempt.id):
        return WaitReason.CONTEXT
    checkpoint = latest_checkpoint(node_attempt)
    if checkpoint is not None and checkpoint.wait_reason is not None:
        return checkpoint.wait_reason
    if checkpoint is not None and checkpoint.recommended_next_action == "retry":
        return WaitReason.OPERATOR
    return None


def is_waiting_attempt_resumable(
    flow: Flow, flow_node: FlowNode, node_attempt: NodeAttempt | None
) -> bool:
    if node_attempt is None:
        return False
    if node_attempt.status not in {NodeAttemptStatus.PENDING, NodeAttemptStatus.BLOCKED}:
        return False
    if flow_node.state != FlowNodeState.WAITING:
        return False
    current_attempt = latest_attempt(flow_node)
    if current_attempt is None or current_attempt.id != node_attempt.id:
        return False
    if (
        flow.active_flow_revision_id is not None
        and node_attempt.flow_revision_id != flow.active_flow_revision_id
    ):
        return False
    return waiting_block_reason(flow, flow_node, node_attempt) is None


def refresh_flow_status(flow: Flow) -> FlowStatus:
    if flow.status in {FlowStatus.CANCELLED, FlowStatus.FAILED}:
        return flow.status

    if all_nodes_done(flow):
        set_flow_status(flow, FlowStatus.SUCCEEDED)
        return flow.status

    nodes = ordered_nodes(flow)
    if any(node.state == FlowNodeState.PAUSED for node in nodes):
        set_flow_status(flow, FlowStatus.PAUSED)
        return flow.status

    if pending_approvals(flow.approvals) or projected_manifests(flow.context_manifests):
        set_flow_status(flow, FlowStatus.BLOCKED)
        return flow.status

    if any(node.state == FlowNodeState.RUNNING for node in nodes):
        set_flow_status(flow, FlowStatus.RUNNING)
        return flow.status

    waiting_nodes = [node for node in nodes if node.state == FlowNodeState.WAITING]
    for node in waiting_nodes:
        current_attempt = latest_attempt(node)
        if current_attempt is None:
            continue
        if waiting_block_reason(flow, node, current_attempt) is not None:
            set_flow_status(flow, FlowStatus.BLOCKED)
            return flow.status

    if any(node.state == FlowNodeState.READY for node in nodes):
        set_flow_status(flow, FlowStatus.RUNNING)
        return flow.status

    if any(node.state == FlowNodeState.WAITING for node in nodes):
        set_flow_status(flow, FlowStatus.BLOCKED)
        return flow.status

    set_flow_status(flow, FlowStatus.PENDING)
    return flow.status


def expire_pending_approvals(
    flow: Flow,
    *,
    node_attempt_id: object | None = None,
    flow_node_id: object | None = None,
    reason: str,
) -> None:
    for approval in flow.approvals:
        if approval.status != ApprovalStatus.PENDING:
            continue
        if node_attempt_id is not None and approval.node_attempt_id != node_attempt_id:
            continue
        if flow_node_id is not None and approval.flow_node_id not in {None, flow_node_id}:
            continue
        approval.status = ApprovalStatus.EXPIRED
        approval.resolution_payload = {"reason": reason}


def supersede_projected_manifests(
    flow: Flow,
    *,
    node_attempt_id: object | None = None,
) -> None:
    for manifest in flow.context_manifests:
        if manifest.status != ContextManifestStatus.PROJECTED:
            continue
        if node_attempt_id is not None and manifest.node_attempt_id != node_attempt_id:
            continue
        manifest.status = ContextManifestStatus.SUPERSEDED


def end_node_session(node_session: NodeSession | None) -> None:
    if node_session is None:
        return
    node_session.status = NodeSessionStatus.ENDED
    node_session.ended_at = utcnow_naive()
    node_session.node_attempt_id = None


def idle_node_session(node_session: NodeSession | None) -> None:
    if node_session is None:
        return
    node_session.status = NodeSessionStatus.IDLE
    node_session.last_seen_at = utcnow_naive()


def cancel_attempt(node_attempt: NodeAttempt | None) -> None:
    if node_attempt is None or node_attempt.status in TERMINAL_ATTEMPT_STATUSES:
        return
    node_attempt.status = NodeAttemptStatus.CANCELLED
    node_attempt.finished_at = utcnow_naive()


def abort_attempt(node_attempt: NodeAttempt | None) -> None:
    if node_attempt is None or node_attempt.status in {
        NodeAttemptStatus.CANCELLED,
        NodeAttemptStatus.FAILED,
        NodeAttemptStatus.ABORTED,
    }:
        return
    node_attempt.status = NodeAttemptStatus.ABORTED
    node_attempt.finished_at = utcnow_naive()
