from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ApprovalStatus,
    ContextManifestStatus,
    FlowStatus,
    NodeAttemptStatus,
)
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import Approval, Flow, FlowNode, FlowRevision, NodeAttempt
from app.runtime.callback_bindings import (
    ensure_latest_acked_manifest,
    ensure_node_session_key,
    latest_acked_manifest,
)
from app.runtime.packaging import upsert_runtime_container
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


async def create_approval(session: AsyncSession, payload: ApprovalCreate) -> Approval:
    await lock_flow(session, payload.flow_id)
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

    ensure_flow_not_terminal(flow)

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

        if attempt is not None and attempt.flow_node_id != flow_node.id:
            raise ConflictError("Approval flow node does not match the provided node attempt")

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

        manifest_id = getattr(payload, "manifest_id", None)
        manifest_hash = getattr(payload, "manifest_hash", None)
        node_session_key = getattr(payload, "node_session_key", None)
        ack_checkpoint_id = getattr(payload, "ack_checkpoint_id", None)
        if (
            manifest_id is not None
            or manifest_hash is not None
            or node_session_key is not None
            or ack_checkpoint_id is not None
        ):
            if (
                manifest_id is None
                or manifest_hash is None
                or node_session_key is None
                or ack_checkpoint_id is None
            ):
                raise ConflictError(
                    "Approval callback requires manifest, session, and ack lineage binding"
                )
            node_session = ensure_node_session_key(
                attempt.flow_node.node_session,
                node_session_key=node_session_key,
            )
            ensure_latest_acked_manifest(
                flow,
                attempt,
                node_session,
                manifest_id=manifest_id,
                manifest_hash=manifest_hash,
                ack_checkpoint_id=ack_checkpoint_id,
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
    if attempt is not None and attempt.flow_node is not None:
        await upsert_runtime_container(
            session,
            flow=flow,
            flow_node=attempt.flow_node,
            node_attempt=attempt,
            node_session=attempt.flow_node.node_session,
            manifest=latest_acked_manifest(flow, attempt),
        )
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
        .where(Flow.id == approval_flow_id)
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
        attempt = await session.scalar(
            select(NodeAttempt)
            .options(
                selectinload(NodeAttempt.flow_node).selectinload(FlowNode.node_session),
                selectinload(NodeAttempt.flow_node).selectinload(FlowNode.attempts),
            )
            .where(NodeAttempt.id == approval.node_attempt_id)
        )
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

        if attempt is not None and attempt.flow_node is not None:
            mark_node_attempt_failed(attempt.flow_node, attempt)
            end_node_session(attempt.flow_node.node_session)
        elif attempt is not None:
            attempt.status = NodeAttemptStatus.FAILED
            attempt.finished_at = utcnow_naive()
        elif flow.active_flow_revision is not None:
            for flow_node in flow.active_flow_revision.nodes:
                current_attempt = latest_attempt(flow_node)
                if current_attempt is None:
                    continue
                if current_attempt.status in {
                    NodeAttemptStatus.SUCCEEDED,
                    NodeAttemptStatus.FAILED,
                    NodeAttemptStatus.CANCELLED,
                    NodeAttemptStatus.ABORTED,
                }:
                    continue
                mark_node_attempt_failed(flow_node, current_attempt)
                end_node_session(flow_node.node_session)
    elif payload.status == ApprovalStatus.NOT_REQUIRED:
        refresh_flow_status(flow)

    if attempt is not None and attempt.flow_node is not None:
        await upsert_runtime_container(
            session,
            flow=flow,
            flow_node=attempt.flow_node,
            node_attempt=attempt,
            node_session=attempt.flow_node.node_session,
            manifest=latest_acked_manifest(flow, attempt),
        )

    await session.flush()
    return approval
