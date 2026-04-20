from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.api.presenters.runtime import to_flow_summary_read
from app.core.enums import (
    CheckpointStatus,
    FlowNodeState,
    FlowRevisionStatus,
    FlowStatus,
    NodeAttemptStatus,
    TaskStatus,
)
from app.db.models.runtime import Flow, FlowNode, FlowRevision, NodeAttempt, NodeCheckpoint, Task


def _dt(hour: int, minute: int) -> datetime:
    return datetime(2026, 4, 20, hour, minute, tzinfo=UTC).replace(tzinfo=None)


def test_flow_summary_uses_latest_visible_checkpoint_by_time_not_node_order() -> None:
    task = Task(
        id=uuid4(),
        title="Presenter test",
        description="Presenter test",
        status=TaskStatus.PENDING,
        input_payload={},
    )
    flow = Flow(
        id=uuid4(),
        task_id=task.id,
        status=FlowStatus.RUNNING,
        execution_no=1,
        seed_compiled_plan_id=uuid4(),
    )
    flow.task = task
    flow.approvals = []
    flow.context_manifests = []

    revision = FlowRevision(
        id=uuid4(),
        flow_id=flow.id,
        revision_no=1,
        compiled_plan_id=uuid4(),
        status=FlowRevisionStatus.ACTIVE,
        reason="test",
        source_patch_payload={},
    )
    flow.active_flow_revision = revision
    flow.active_flow_revision_id = revision.id

    root_node = FlowNode(
        id=uuid4(),
        flow_id=flow.id,
        flow_revision_id=revision.id,
        node_key="root",
        node_path="root",
        state=FlowNodeState.DONE,
        order_index=0,
        status_payload={},
    )
    later_node = FlowNode(
        id=uuid4(),
        flow_id=flow.id,
        flow_revision_id=revision.id,
        node_key="root.discovery",
        node_path="root.discovery",
        state=FlowNodeState.DONE,
        order_index=1,
        status_payload={},
    )

    root_attempt = NodeAttempt(
        id=uuid4(),
        flow_id=flow.id,
        flow_revision_id=revision.id,
        flow_node_id=root_node.id,
        number=1,
        status=NodeAttemptStatus.SUCCEEDED,
        started_at=_dt(10, 0),
    )
    later_attempt = NodeAttempt(
        id=uuid4(),
        flow_id=flow.id,
        flow_revision_id=revision.id,
        flow_node_id=later_node.id,
        number=1,
        status=NodeAttemptStatus.SUCCEEDED,
        started_at=_dt(9, 0),
    )

    newer_checkpoint = NodeCheckpoint(
        id=uuid4(),
        flow_id=flow.id,
        flow_node_id=root_node.id,
        node_attempt_id=root_attempt.id,
        sequence_no=1,
        status=CheckpointStatus.GREEN,
        summary="newer checkpoint on earlier node",
        payload={},
        created_at=_dt(10, 30),
    )
    older_checkpoint = NodeCheckpoint(
        id=uuid4(),
        flow_id=flow.id,
        flow_node_id=later_node.id,
        node_attempt_id=later_attempt.id,
        sequence_no=1,
        status=CheckpointStatus.GREEN,
        summary="older checkpoint on later node",
        payload={},
        created_at=_dt(9, 30),
    )

    root_attempt.checkpoints = [newer_checkpoint]
    later_attempt.checkpoints = [older_checkpoint]
    root_node.attempts = [root_attempt]
    later_node.attempts = [later_attempt]
    revision.nodes = [root_node, later_node]

    summary = to_flow_summary_read(flow)

    assert summary.latest_checkpoint_summary == "newer checkpoint on earlier node"
