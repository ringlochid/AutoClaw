from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ApprovalStatus, FlowStatus, NodeAttemptStatus
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import Approval, Flow, FlowNode, FlowRevision, NodeAttempt
from app.runtime.control import (
    end_node_session,
    ensure_current_attempt,
    idle_node_session,
    refresh_flow_status,
)
from app.runtime.state import (
    mark_node_attempt_blocked,
    mark_node_attempt_failed,
    set_flow_status,
    utcnow_naive,
)
from app.schemas.runtime import ApprovalCreate, ApprovalResolve


async def create_approval(session: AsyncSession, payload: ApprovalCreate) -> Approval:
    flow = await session.scalar(
        select(Flow)
        .options(
            selectinload(Flow.task),
            selectinload(Flow.approvals),
            selectinload(Flow.context_manifests),
            selectinload(Flow.active_flow_revision).selectinload(FlowRevision.nodes),
        )
        .where(Flow.id == payload.flow_id)
    )
    if flow is None:
        raise NotFoundError(f"No flow found: {payload.flow_id}")

    node_attempt_id = payload.node_attempt_id
    attempt: NodeAttempt | None = None
    if node_attempt_id is not None:
        attempt = await session.scalar(
            select(NodeAttempt)
            .options(
                selectinload(NodeAttempt.flow_node).selectinload(FlowNode.node_session),
                selectinload(NodeAttempt.flow_node).selectinload(FlowNode.attempts),
            )
            .where(NodeAttempt.id == node_attempt_id)
        )
        if attempt is None or attempt.flow_id != payload.flow_id:
            raise NotFoundError(f"No node attempt found: {node_attempt_id}")

    flow_node: FlowNode | None = None
    if payload.flow_node_id is not None:
        flow_node = await session.get(FlowNode, payload.flow_node_id)
        if flow_node is None or flow_node.flow_id != flow.id:
            raise NotFoundError(f"No flow node found: {payload.flow_node_id}")

        if node_attempt_id is None:
            attempt = await session.scalar(
                select(NodeAttempt)
                .options(
                    selectinload(NodeAttempt.flow_node).selectinload(FlowNode.node_session),
                    selectinload(NodeAttempt.flow_node).selectinload(FlowNode.attempts),
                )
                .where(NodeAttempt.flow_node_id == flow_node.id)
                .order_by(NodeAttempt.number.desc())
                .limit(1)
            )
            if attempt is None:
                raise ConflictError("Approval requires an active node attempt")
            node_attempt_id = attempt.id

    if payload.flow_node_id is not None and node_attempt_id is None:
        raise ConflictError("Cannot infer active node attempt for approval")

    if attempt is not None:
        ensure_current_attempt(
            flow,
            attempt.flow_node,
            attempt,
            allowed_statuses={NodeAttemptStatus.RUNNING, NodeAttemptStatus.BLOCKED},
        )

    approval = Approval(
        flow_id=payload.flow_id,
        flow_node_id=payload.flow_node_id,
        node_attempt_id=node_attempt_id,
        status=ApprovalStatus.PENDING,
        reason=payload.reason,
        request_payload=payload.request_payload,
        resolution_payload={},
    )
    flow.approvals.append(approval)

    if node_attempt_id is not None:
        if attempt is None:
            attempt = await session.scalar(
                select(NodeAttempt)
                .options(
                    selectinload(NodeAttempt.flow_node).selectinload(FlowNode.node_session),
                    selectinload(NodeAttempt.flow_node).selectinload(FlowNode.attempts),
                )
                .where(NodeAttempt.id == node_attempt_id)
            )
        if attempt is not None:
            flow_node = attempt.flow_node
            if flow_node is not None:
                mark_node_attempt_blocked(flow, flow_node, attempt)
                idle_node_session(flow_node.node_session)
            elif flow.status != FlowStatus.CANCELLED:
                set_flow_status(flow, FlowStatus.BLOCKED)
    elif flow_node is not None:
        mark_node_attempt_blocked(flow, flow_node)
    elif flow.status != FlowStatus.CANCELLED:
        set_flow_status(flow, FlowStatus.BLOCKED)

    refresh_flow_status(flow)
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
        select(Flow)
        .options(
            selectinload(Flow.task),
            selectinload(Flow.approvals),
            selectinload(Flow.context_manifests),
            selectinload(Flow.active_flow_revision)
            .selectinload(FlowRevision.nodes)
            .selectinload(FlowNode.attempts)
            .selectinload(NodeAttempt.checkpoints),
            selectinload(Flow.active_flow_revision)
            .selectinload(FlowRevision.nodes)
            .selectinload(FlowNode.node_session),
        )
        .where(Flow.id == approval.flow_id)
    )
    if flow is None:
        raise NotFoundError(f"No flow found: {approval.flow_id}")

    if payload.status == ApprovalStatus.APPROVED:
        refresh_flow_status(flow)
    elif payload.status == ApprovalStatus.REJECTED:
        set_flow_status(flow, FlowStatus.FAILED)

        if approval.node_attempt_id is not None:
            attempt = await session.scalar(
                select(NodeAttempt)
                .options(selectinload(NodeAttempt.flow_node).selectinload(FlowNode.node_session))
                .where(NodeAttempt.id == approval.node_attempt_id)
            )
            if attempt is not None and attempt.flow_node is not None:
                mark_node_attempt_failed(attempt.flow_node, attempt)
                end_node_session(attempt.flow_node.node_session)
            elif attempt is not None:
                attempt.status = NodeAttemptStatus.FAILED
                attempt.finished_at = utcnow_naive()
    elif payload.status == ApprovalStatus.NOT_REQUIRED:
        refresh_flow_status(flow)

    await session.flush()
    return approval
