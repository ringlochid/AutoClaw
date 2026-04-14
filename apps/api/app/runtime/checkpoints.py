from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ApprovalStatus,
    CheckpointStatus,
    FlowNodeState,
    FlowStatus,
    NodeAttemptStatus,
)
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import Approval, Flow, FlowRevision, NodeAttempt, NodeCheckpoint
from app.schemas.runtime import CheckpointWrite


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def record_checkpoint(session: AsyncSession, payload: CheckpointWrite) -> NodeCheckpoint:
    stmt = (
        select(NodeAttempt)
        .options(
            selectinload(NodeAttempt.flow_node),
            selectinload(NodeAttempt.flow)
            .selectinload(Flow.active_flow_revision)
            .selectinload(FlowRevision.nodes),
        )
        .where(NodeAttempt.id == payload.node_attempt_id)
    )
    attempt = await session.scalar(stmt)
    if attempt is None:
        raise NotFoundError(f"No node attempt found: {payload.node_attempt_id}")

    if attempt.flow_id != payload.flow_id:
        raise ConflictError("Attempt does not belong to flow")
    if attempt.flow_node_id != payload.flow_node_id:
        raise ConflictError("Attempt does not belong to flow node")

    flow = attempt.flow
    if flow is None:
        raise NotFoundError(f"No flow found: {payload.flow_id}")

    last_seq = await session.scalar(
        select(NodeCheckpoint.sequence_no)
        .where(NodeCheckpoint.node_attempt_id == attempt.id)
        .order_by(NodeCheckpoint.sequence_no.desc())
        .limit(1)
    )

    if last_seq is not None and payload.sequence_no <= int(last_seq):
        raise ConflictError("Sequence number must be greater than previous checkpoint sequence")

    checkpoint = NodeCheckpoint(
        flow_id=payload.flow_id,
        flow_node_id=payload.flow_node_id,
        node_attempt_id=payload.node_attempt_id,
        sequence_no=payload.sequence_no,
        status=payload.status,
        summary=payload.summary,
        payload=payload.payload,
        failure_signature=payload.failure_signature,
        recommended_next_action=payload.recommended_next_action,
        wait_reason=payload.wait_reason,
    )
    session.add(checkpoint)

    if payload.status == CheckpointStatus.GREEN:
        attempt.status = NodeAttemptStatus.SUCCEEDED
        attempt.finished_at = _utcnow_naive()
        attempt.flow_node.state = FlowNodeState.DONE
    elif payload.status == CheckpointStatus.BLOCKED:
        attempt.status = NodeAttemptStatus.BLOCKED
        attempt.flow_node.state = FlowNodeState.WAITING
        flow.status = FlowStatus.BLOCKED
    elif payload.status == CheckpointStatus.RETRY:
        attempt.status = NodeAttemptStatus.FAILED
        attempt.flow_node.state = FlowNodeState.READY
    elif payload.status == CheckpointStatus.NEEDS_APPROVAL:
        attempt.status = NodeAttemptStatus.BLOCKED
        attempt.flow_node.state = FlowNodeState.WAITING
        flow.status = FlowStatus.BLOCKED
        existing_pending_approval = await session.scalar(
            select(Approval.id)
            .where(Approval.node_attempt_id == attempt.id)
            .where(Approval.status == ApprovalStatus.PENDING)
            .limit(1)
        )
        if existing_pending_approval is None:
            session.add(
                Approval(
                    flow_id=flow.id,
                    flow_node_id=attempt.flow_node_id,
                    node_attempt_id=attempt.id,
                    reason=payload.recommended_next_action or payload.summary,
                    request_payload=payload.payload,
                )
            )

    await session.flush()

    # if all active nodes have done status then flow is complete
    if flow.active_flow_revision is not None:
        if all(node.state == FlowNodeState.DONE for node in flow.active_flow_revision.nodes):
            flow.status = FlowStatus.SUCCEEDED

    return checkpoint


async def list_flow_checkpoints(session: AsyncSession, flow_id: UUID) -> list[NodeCheckpoint]:
    flow = await session.get(Flow, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")

    result = await session.scalars(
        select(NodeCheckpoint)
        .where(NodeCheckpoint.flow_id == flow_id)
        .order_by(NodeCheckpoint.created_at.asc(), NodeCheckpoint.sequence_no.asc())
    )
    return list(result.all())
