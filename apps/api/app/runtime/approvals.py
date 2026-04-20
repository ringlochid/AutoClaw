from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ApprovalStatus,
    FlowStatus,
    NodeAttemptStatus,
)
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import Approval, Flow, FlowNode, FlowRevision, NodeAttempt
from app.runtime.callback_bindings import (
    extract_callback_binding,
    validate_attempt_execution_binding,
)
from app.runtime.control import (
    end_node_session,
    ensure_current_attempt,
    ensure_flow_not_terminal,
    expire_pending_approvals,
    idle_node_session,
    latest_attempt,
    lock_flow,
    refresh_flow_status,
    supersede_projected_manifests,
)
from app.runtime.state import (
    mark_node_attempt_blocked,
    mark_node_attempt_failed,
    set_flow_status,
    utcnow_naive,
)
from app.schemas.runtime import ApprovalCreate, ApprovalResolve

_RESOLVED_APPROVAL_STATUSES = {
    ApprovalStatus.APPROVED,
    ApprovalStatus.REJECTED,
    ApprovalStatus.NOT_REQUIRED,
    ApprovalStatus.EXPIRED,
}

_TERMINAL_ATTEMPT_STATUSES = {
    NodeAttemptStatus.SUCCEEDED,
    NodeAttemptStatus.FAILED,
    NodeAttemptStatus.CANCELLED,
    NodeAttemptStatus.ABORTED,
}


def _flow_create_approval_options() -> list[Any]:
    return [
        selectinload(Flow.task),
        selectinload(Flow.approvals),
        selectinload(Flow.context_manifests),
        selectinload(Flow.active_flow_revision).selectinload(FlowRevision.nodes),
    ]


def _flow_resolve_approval_options() -> list[Any]:
    return [
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
    ]


def _node_attempt_options() -> list[Any]:
    return [
        selectinload(NodeAttempt.flow_node).selectinload(FlowNode.node_session),
        selectinload(NodeAttempt.flow_node).selectinload(FlowNode.attempts),
    ]


async def _load_node_attempt(
    session: AsyncSession,
    *,
    node_attempt_id: UUID,
) -> NodeAttempt | None:
    return cast(
        NodeAttempt | None,
        await session.scalar(
            select(NodeAttempt)
            .options(*_node_attempt_options())
            .where(NodeAttempt.id == node_attempt_id)
        ),
    )


async def _load_latest_node_attempt_for_flow_node(
    session: AsyncSession,
    *,
    flow_node_id: UUID,
) -> NodeAttempt | None:
    return cast(
        NodeAttempt | None,
        await session.scalar(
            select(NodeAttempt)
            .options(*_node_attempt_options())
            .where(NodeAttempt.flow_node_id == flow_node_id)
            .order_by(NodeAttempt.number.desc())
            .limit(1)
        ),
    )


def _resolve_create_approval_target(
    *,
    flow: Flow,
    payload: ApprovalCreate,
    flow_node: FlowNode | None,
    attempt: NodeAttempt | None,
) -> tuple[FlowNode | None, NodeAttempt | None, UUID | None]:
    node_attempt_id = payload.node_attempt_id

    if flow_node is not None and attempt is not None and attempt.flow_node_id != flow_node.id:
        raise ConflictError("Approval flow node does not match the provided node attempt")

    if payload.flow_node_id is not None and node_attempt_id is None:
        if attempt is None:
            raise ConflictError("Approval requires an active node attempt")
        node_attempt_id = attempt.id

    if payload.flow_node_id is not None and node_attempt_id is None:
        raise ConflictError("Cannot infer active node attempt for approval")

    if attempt is not None:
        callback_binding = extract_callback_binding(
            payload,
            required=False,
            operation="Approval callback",
        )
        validate_attempt_execution_binding(
            flow,
            attempt.flow_node,
            attempt,
            callback_binding=callback_binding,
            allowed_attempt_statuses={NodeAttemptStatus.RUNNING, NodeAttemptStatus.BLOCKED},
        )

    return flow_node, attempt, node_attempt_id


def _apply_pending_approval_block(
    flow: Flow,
    *,
    flow_node: FlowNode | None,
    attempt: NodeAttempt | None,
) -> None:
    if attempt is not None:
        resolved_flow_node = flow_node or attempt.flow_node
        if resolved_flow_node is not None:
            mark_node_attempt_blocked(flow, resolved_flow_node, attempt)
            idle_node_session(resolved_flow_node.node_session)
        elif flow.status != FlowStatus.CANCELLED:
            set_flow_status(flow, FlowStatus.BLOCKED)
        return

    if flow_node is not None:
        mark_node_attempt_blocked(flow, flow_node)
    elif flow.status != FlowStatus.CANCELLED:
        set_flow_status(flow, FlowStatus.BLOCKED)


def _fail_open_attempts_for_rejected_approval(
    flow: Flow,
    *,
    attempt: NodeAttempt | None,
) -> None:
    if attempt is not None and attempt.flow_node is not None:
        mark_node_attempt_failed(attempt.flow_node, attempt)
        end_node_session(attempt.flow_node.node_session)
        return

    if attempt is not None:
        attempt.status = NodeAttemptStatus.FAILED
        attempt.finished_at = utcnow_naive()
        return

    if flow.active_flow_revision is None:
        return

    for flow_node in flow.active_flow_revision.nodes:
        current_attempt = latest_attempt(flow_node)
        if current_attempt is None or current_attempt.status in _TERMINAL_ATTEMPT_STATUSES:
            continue
        mark_node_attempt_failed(flow_node, current_attempt)
        end_node_session(flow_node.node_session)


async def create_approval(session: AsyncSession, payload: ApprovalCreate) -> Approval:
    await lock_flow(session, payload.flow_id)
    flow = await session.scalar(
        select(Flow).options(*_flow_create_approval_options()).where(Flow.id == payload.flow_id)
    )
    if flow is None:
        raise NotFoundError(f"No flow found: {payload.flow_id}")

    ensure_flow_not_terminal(flow)

    attempt = None
    if payload.node_attempt_id is not None:
        attempt = await _load_node_attempt(session, node_attempt_id=payload.node_attempt_id)
        if attempt is None or attempt.flow_id != payload.flow_id:
            raise NotFoundError(f"No node attempt found: {payload.node_attempt_id}")

    flow_node: FlowNode | None = None
    if payload.flow_node_id is not None:
        flow_node = await session.get(FlowNode, payload.flow_node_id)
        if flow_node is None or flow_node.flow_id != flow.id:
            raise NotFoundError(f"No flow node found: {payload.flow_node_id}")

        if payload.node_attempt_id is None:
            attempt = await _load_latest_node_attempt_for_flow_node(
                session,
                flow_node_id=flow_node.id,
            )

    flow_node, attempt, node_attempt_id = _resolve_create_approval_target(
        flow=flow,
        payload=payload,
        flow_node=flow_node,
        attempt=attempt,
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

    if node_attempt_id is not None and attempt is None:
        attempt = await _load_node_attempt(session, node_attempt_id=node_attempt_id)
    _apply_pending_approval_block(flow, flow_node=flow_node, attempt=attempt)

    refresh_flow_status(flow)
    await session.flush()
    return approval


async def get_approval(session: AsyncSession, approval_id: UUID) -> Approval | None:
    return await session.get(Approval, approval_id)


async def resolve_approval(
    session: AsyncSession, approval_id: UUID, payload: ApprovalResolve
) -> Approval:
    approval_flow_id = await session.scalar(
        select(Approval.flow_id).where(Approval.id == approval_id)
    )
    if approval_flow_id is None:
        raise NotFoundError(f"No approval found: {approval_id}")

    await lock_flow(session, approval_flow_id)
    flow = await session.scalar(
        select(Flow).options(*_flow_resolve_approval_options()).where(Flow.id == approval_flow_id)
    )
    if flow is None:
        raise NotFoundError(f"No flow found: {approval_flow_id}")

    approval = next((item for item in flow.approvals if item.id == approval_id), None)
    if approval is None:
        raise NotFoundError(f"No approval found: {approval_id}")
    if approval.status in {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.NOT_REQUIRED,
        ApprovalStatus.EXPIRED,
    }:
        raise ConflictError(f"Approval already resolved: {approval.id}")

    ensure_flow_not_terminal(flow)

    attempt: NodeAttempt | None = None
    if approval.node_attempt_id is not None:
        attempt = await _load_node_attempt(session, node_attempt_id=approval.node_attempt_id)
        if attempt is None or attempt.flow_id != flow.id:
            raise NotFoundError(f"No node attempt found: {approval.node_attempt_id}")
        ensure_current_attempt(
            flow,
            attempt.flow_node,
            attempt,
            allowed_statuses={NodeAttemptStatus.BLOCKED},
        )

    approval.status = payload.status
    approval.resolution_payload = payload.resolution_payload

    if payload.status == ApprovalStatus.APPROVED:
        refresh_flow_status(flow)
    elif payload.status == ApprovalStatus.REJECTED:
        expire_pending_approvals(flow, reason="approval-rejected")
        supersede_projected_manifests(flow)
        set_flow_status(flow, FlowStatus.FAILED)
        _fail_open_attempts_for_rejected_approval(flow, attempt=attempt)
    elif payload.status == ApprovalStatus.NOT_REQUIRED:
        refresh_flow_status(flow)
    await session.flush()
    return approval
