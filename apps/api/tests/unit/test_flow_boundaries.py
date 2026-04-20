from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.enums import (
    CheckpointStatus,
    ContextManifestStatus,
    FlowNodeState,
    FlowRevisionStatus,
    FlowStatus,
    NodeAttemptStatus,
    WaitReason,
)
from app.db.models.runtime import (
    ContextManifest,
    Flow,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodeCheckpoint,
)
from app.runtime.control import flow_boundary_snapshot


def _dt(hour: int, minute: int) -> datetime:
    return datetime(2026, 4, 20, hour, minute, tzinfo=UTC).replace(tzinfo=None)


def _base_flow() -> tuple[Flow, FlowRevision, FlowNode, NodeAttempt]:
    flow = Flow(
        id=uuid4(),
        task_id=uuid4(),
        status=FlowStatus.RUNNING,
        execution_no=1,
        seed_compiled_plan_id=uuid4(),
    )
    revision = FlowRevision(
        id=uuid4(),
        flow_id=flow.id,
        revision_no=1,
        compiled_plan_id=uuid4(),
        status=FlowRevisionStatus.ACTIVE,
        reason="test",
        source_patch_payload={},
    )
    node = FlowNode(
        id=uuid4(),
        flow_id=flow.id,
        flow_revision_id=revision.id,
        node_key="root",
        node_path="root",
        state=FlowNodeState.WAITING,
        order_index=0,
        status_payload={},
    )
    attempt = NodeAttempt(
        id=uuid4(),
        flow_id=flow.id,
        flow_revision_id=revision.id,
        flow_node_id=node.id,
        number=1,
        status=NodeAttemptStatus.BLOCKED,
        started_at=_dt(10, 0),
    )
    node.attempts = [attempt]
    revision.nodes = [node]
    flow.active_flow_revision = revision
    flow.active_flow_revision_id = revision.id
    flow.approvals = []
    flow.context_manifests = []
    return flow, revision, node, attempt


def test_flow_boundary_snapshot_prefers_projected_manifests() -> None:
    flow, _revision, node, attempt = _base_flow()
    flow.context_manifests = [
        ContextManifest(
            id=uuid4(),
            flow_id=flow.id,
            flow_node_id=node.id,
            node_attempt_id=attempt.id,
            node_session_id=uuid4(),
            manifest_no=1,
            manifest_payload={},
            manifest_hash="manifest-hash",
            status=ContextManifestStatus.PROJECTED,
            projected_at=_dt(10, 5),
        )
    ]

    snapshot = flow_boundary_snapshot(flow)

    assert snapshot.boundary_reason() == "projected-manifests"
    assert str(snapshot.conflict_error()) == "Flow is waiting on projected manifests"


def test_flow_boundary_snapshot_reports_watchdog_block() -> None:
    flow, _revision, node, attempt = _base_flow()
    attempt.checkpoints = [
        NodeCheckpoint(
            id=uuid4(),
            flow_id=flow.id,
            flow_node_id=node.id,
            node_attempt_id=attempt.id,
            sequence_no=1,
            status=CheckpointStatus.BLOCKED,
            summary="watchdog block",
            payload={},
            wait_reason=WaitReason.WATCHDOG,
            created_at=_dt(10, 10),
        )
    ]

    snapshot = flow_boundary_snapshot(flow)

    assert snapshot.boundary_reason() == "watchdog"
    assert str(snapshot.conflict_error()) == "Flow is waiting on watchdog recovery"


def test_flow_boundary_snapshot_tracks_paused_and_ready_counts() -> None:
    flow, revision, node, attempt = _base_flow()
    node.state = FlowNodeState.PAUSED
    ready_node = FlowNode(
        id=uuid4(),
        flow_id=flow.id,
        flow_revision_id=revision.id,
        node_key="root.discovery",
        node_path="root.discovery",
        state=FlowNodeState.READY,
        order_index=1,
        status_payload={},
    )
    revision.nodes = [node, ready_node]
    node.attempts = [attempt]

    snapshot = flow_boundary_snapshot(flow)

    assert snapshot.has_paused_node is True
    assert snapshot.ready_node_count == 1
