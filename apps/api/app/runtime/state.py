from __future__ import annotations

from datetime import UTC, datetime

from app.core.enums import FlowNodeState, FlowStatus, NodeAttemptStatus, TaskStatus
from app.db.models.runtime import Flow, FlowNode, NodeAttempt


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def set_flow_status(flow: Flow, status: FlowStatus) -> None:
    flow.status = status
    if status == FlowStatus.PENDING:
        flow.task.status = TaskStatus.PENDING
    elif status == FlowStatus.RUNNING:
        flow.task.status = TaskStatus.RUNNING
    elif status in {FlowStatus.BLOCKED, FlowStatus.PAUSED}:
        flow.task.status = TaskStatus.BLOCKED
    elif status == FlowStatus.FAILED:
        flow.task.status = TaskStatus.FAILED
    elif status == FlowStatus.SUCCEEDED:
        flow.task.status = TaskStatus.SUCCEEDED
    elif status == FlowStatus.CANCELLED:
        flow.task.status = TaskStatus.CANCELLED


def mark_node_attempt_running(
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
) -> None:
    node_attempt.status = NodeAttemptStatus.RUNNING
    flow_node.state = FlowNodeState.RUNNING
    set_flow_status(flow, FlowStatus.RUNNING)


def mark_node_attempt_blocked(
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt | None = None,
) -> None:
    if node_attempt is not None:
        node_attempt.status = NodeAttemptStatus.BLOCKED
    flow_node.state = FlowNodeState.WAITING
    if flow.status != FlowStatus.CANCELLED:
        set_flow_status(flow, FlowStatus.BLOCKED)


def mark_node_attempt_succeeded(
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
) -> None:
    node_attempt.status = NodeAttemptStatus.SUCCEEDED
    node_attempt.finished_at = utcnow_naive()
    flow_node.state = FlowNodeState.DONE


def mark_node_attempt_failed(
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
) -> None:
    node_attempt.status = NodeAttemptStatus.FAILED
    node_attempt.finished_at = utcnow_naive()
    flow_node.state = FlowNodeState.FAILED
