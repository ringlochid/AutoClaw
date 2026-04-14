from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ApprovalStatus, FlowNodeState, FlowStatus, NodeAttemptStatus, TaskStatus
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import Approval, Flow, FlowNode, NodeAttempt
from app.schemas.runtime import ApprovalCreate, ApprovalResolve


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def create_approval(session: AsyncSession, payload: ApprovalCreate) -> Approval:
    flow = await session.get(Flow, payload.flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {payload.flow_id}")

    node_attempt_id = payload.node_attempt_id
    if node_attempt_id is not None:
        attempt = await session.get(NodeAttempt, node_attempt_id)
        if attempt is None or attempt.flow_id != payload.flow_id:
            raise NotFoundError(f"No node attempt found: {node_attempt_id}")

    flow_node: FlowNode | None = None
    if payload.flow_node_id is not None:
        flow_node = await session.get(FlowNode, payload.flow_node_id)
        if flow_node is None or flow_node.flow_id != flow.id:
            raise NotFoundError(f"No flow node found: {payload.flow_node_id}")

        if node_attempt_id is None:
            latest_attempt = await session.scalar(
                select(NodeAttempt)
                .where(NodeAttempt.flow_node_id == flow_node.id)
                .order_by(NodeAttempt.number.desc())
                .limit(1)
            )
            if latest_attempt is None:
                raise ConflictError("Approval requires an active node attempt")
            node_attempt_id = latest_attempt.id

    if payload.flow_node_id is not None and node_attempt_id is None:
        raise ConflictError("Cannot infer active node attempt for approval")

    approval = Approval(
        flow_id=payload.flow_id,
        flow_node_id=payload.flow_node_id,
        node_attempt_id=node_attempt_id,
        status=ApprovalStatus.PENDING,
        reason=payload.reason,
        request_payload=payload.request_payload,
        resolution_payload={},
    )
    session.add(approval)

    if node_attempt_id is not None:
        attempt = await session.get(NodeAttempt, node_attempt_id)
        if attempt is not None:
            attempt.status = NodeAttemptStatus.BLOCKED
            flow_node = attempt.flow_node

    if flow_node is not None:
        flow_node.state = FlowNodeState.WAITING

    if flow.status != FlowStatus.CANCELLED:
        flow.status = FlowStatus.BLOCKED

    await session.flush()
    return approval


async def get_approval(session: AsyncSession, approval_id: UUID) -> Approval | None:
    return await session.get(Approval, approval_id)


async def resolve_approval(
    session: AsyncSession, approval_id: UUID, payload: ApprovalResolve
) -> Approval:
    approval = await session.get(Approval, approval_id)
    if approval is None:
        raise NotFoundError(f"No approval found: {approval_id}")
    if approval.status in {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.EXPIRED,
    }:
        raise ConflictError(f"Approval already resolved: {approval.id}")

    approval.status = payload.status
    approval.resolution_payload = payload.resolution_payload

    if approval.flow_id is None:
        await session.flush()
        return approval

    flow = await session.scalar(
        select(Flow).options(selectinload(Flow.task)).where(Flow.id == approval.flow_id)
    )
    if flow is None:
        raise NotFoundError(f"No flow found: {approval.flow_id}")

    if payload.status == ApprovalStatus.APPROVED:
        # Keep flow moving. It will progress on next continue() call.
        if flow.status == FlowStatus.BLOCKED:
            flow.status = FlowStatus.RUNNING
    elif payload.status == ApprovalStatus.REJECTED:
        flow.status = FlowStatus.FAILED
        flow.task.status = TaskStatus.FAILED

        if approval.node_attempt_id is not None:
            attempt = await session.scalar(
                select(NodeAttempt)
                .options(selectinload(NodeAttempt.flow_node))
                .where(NodeAttempt.id == approval.node_attempt_id)
            )
            if attempt is not None:
                attempt.status = NodeAttemptStatus.FAILED
                attempt.finished_at = _utcnow_naive()
                if attempt.flow_node is not None:
                    attempt.flow_node.state = FlowNodeState.FAILED
    elif payload.status == ApprovalStatus.NOT_REQUIRED:
        if flow.status == FlowStatus.BLOCKED:
            flow.status = FlowStatus.RUNNING

    await session.flush()
    return approval
