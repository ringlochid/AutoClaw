from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CheckpointStatus, FlowNodeState, FlowStatus, NodeAttemptStatus, WaitReason
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import Flow, NodeCheckpoint
from app.runtime.runner import _set_flow_status, _utcnow_naive, get_flow_with_relations


async def run_flow_watchdog(
    session: AsyncSession,
    *,
    flow_id: UUID,
    stale_after_seconds: int = 300,
) -> tuple[Flow, list[UUID], list[NodeCheckpoint]]:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")
    if flow.status in {FlowStatus.CANCELLED, FlowStatus.FAILED, FlowStatus.SUCCEEDED}:
        raise ConflictError(f"Flow is already terminal: {flow.status.value}")

    threshold = _utcnow_naive() - timedelta(seconds=stale_after_seconds)
    stalled_attempt_ids: list[UUID] = []
    checkpoints: list[NodeCheckpoint] = []

    if flow.active_flow_revision is None:
        return flow, stalled_attempt_ids, checkpoints

    for flow_node in flow.active_flow_revision.nodes:
        latest_attempt = flow_node.attempts[-1] if flow_node.attempts else None
        if latest_attempt is None or latest_attempt.status != NodeAttemptStatus.RUNNING:
            continue

        last_checkpoint_time = (
            latest_attempt.checkpoints[-1].created_at
            if latest_attempt.checkpoints
            else latest_attempt.started_at
        )
        if last_checkpoint_time >= threshold:
            continue

        latest_attempt.status = NodeAttemptStatus.BLOCKED
        flow_node.state = FlowNodeState.WAITING
        checkpoint = NodeCheckpoint(
            flow_id=flow.id,
            flow_node_id=flow_node.id,
            node_attempt_id=latest_attempt.id,
            sequence_no=(latest_attempt.checkpoints[-1].sequence_no + 1)
            if latest_attempt.checkpoints
            else 1,
            status=CheckpointStatus.BLOCKED,
            summary="watchdog stalled attempt",
            payload={"stale_after_seconds": stale_after_seconds},
            recommended_next_action="retry",
            wait_reason=WaitReason.WATCHDOG,
        )
        session.add(checkpoint)
        checkpoints.append(checkpoint)
        stalled_attempt_ids.append(latest_attempt.id)

    if stalled_attempt_ids:
        _set_flow_status(flow, FlowStatus.BLOCKED)

    await session.flush()
    return flow, stalled_attempt_ids, checkpoints
