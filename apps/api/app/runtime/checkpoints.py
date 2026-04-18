from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ApprovalStatus,
    CheckpointStatus,
    ContextItemKind,
    ContextItemScope,
    ContextItemStatus,
    ContextManifestStatus,
    FlowNodeState,
    NodeSessionStatus,
)
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import (
    Approval,
    ContextItem,
    Flow,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodeCheckpoint,
)
from app.runtime.callback_bindings import ensure_latest_acked_manifest, ensure_node_session_key
from app.runtime.packaging import upsert_runtime_container
from app.runtime.control import (
    ACTIVE_ATTEMPT_STATUSES,
    end_node_session,
    ensure_current_attempt,
    ensure_flow_not_terminal,
    idle_node_session,
    lock_flow,
    refresh_flow_status,
)
from app.runtime.state import (
    mark_node_attempt_blocked,
    mark_node_attempt_failed,
    mark_node_attempt_succeeded,
    utcnow_naive,
)
from app.schemas.runtime import CheckpointWrite


def _hash_context_payload(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _checkpoint_context_payload(
    checkpoint: NodeCheckpoint,
    *,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
) -> dict[str, object]:
    return {
        "checkpoint_id": str(checkpoint.id),
        "flow_node_id": str(flow_node.id),
        "flow_node_key": flow_node.node_key,
        "flow_node_path": flow_node.node_path,
        "node_attempt_id": str(node_attempt.id),
        "status": checkpoint.status.value,
        "summary": checkpoint.summary,
        "payload": checkpoint.payload,
        "failure_signature": checkpoint.failure_signature,
        "recommended_next_action": checkpoint.recommended_next_action,
        "wait_reason": checkpoint.wait_reason.value if checkpoint.wait_reason is not None else None,
    }


async def _publish_green_checkpoint_context_item(
    session: AsyncSession,
    *,
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
    checkpoint: NodeCheckpoint,
) -> None:
    evidence_payload = _checkpoint_context_payload(
        checkpoint,
        flow_node=flow_node,
        node_attempt=node_attempt,
    )
    session.add(
        ContextItem(
            task_id=flow.task_id,
            flow_id=flow.id,
            flow_revision_id=node_attempt.flow_revision_id,
            flow_node_id=flow_node.id,
            node_attempt_id=node_attempt.id,
            scope=ContextItemScope.FLOW_SHARED,
            kind=ContextItemKind.SUMMARY,
            visibility_policy={"default": "shared"},
            status=ContextItemStatus.PUBLISHED,
            title=f"checkpoint-summary:{flow_node.node_key}",
            storage_uri=f"checkpoint://{checkpoint.id}",
            content_hash=_hash_context_payload(evidence_payload),
            metadata_={"inline_content": evidence_payload},
            published_by="system:checkpoint:green",
            source_checkpoint_id=checkpoint.id,
            published_at=checkpoint.created_at,
        )
    )


async def record_checkpoint(session: AsyncSession, payload: CheckpointWrite) -> NodeCheckpoint:
    await lock_flow(session, payload.flow_id)
    stmt = (
        select(NodeAttempt)
        .options(
            selectinload(NodeAttempt.flow_node).selectinload(FlowNode.node_session),
            selectinload(NodeAttempt.flow_node).selectinload(FlowNode.attempts),
            selectinload(NodeAttempt.flow).selectinload(Flow.task),
            selectinload(NodeAttempt.flow).selectinload(Flow.approvals),
            selectinload(NodeAttempt.flow).selectinload(Flow.context_manifests),
            selectinload(NodeAttempt.flow)
            .selectinload(Flow.active_flow_revision)
            .selectinload(FlowRevision.nodes)
            .selectinload(FlowNode.attempts)
            .selectinload(NodeAttempt.checkpoints),
        )
        .where(NodeAttempt.id == payload.node_attempt_id)
        .with_for_update()
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

    ensure_flow_not_terminal(flow)
    ensure_current_attempt(
        flow,
        attempt.flow_node,
        attempt,
        allowed_statuses=ACTIVE_ATTEMPT_STATUSES,
    )

    manifest_id = getattr(payload, "manifest_id", None)
    manifest_hash = getattr(payload, "manifest_hash", None)
    node_session_key = getattr(payload, "node_session_key", None)
    ack_checkpoint_id = getattr(payload, "ack_checkpoint_id", None)
    if (
        manifest_id is None
        or manifest_hash is None
        or node_session_key is None
        or ack_checkpoint_id is None
    ):
        raise ConflictError("Checkpoint callback requires manifest, session, and ack lineage binding")

    node_session = ensure_node_session_key(
        attempt.flow_node.node_session,
        node_session_key=node_session_key,
    )
    manifest = ensure_latest_acked_manifest(
        flow,
        attempt,
        node_session,
        manifest_id=manifest_id,
        manifest_hash=manifest_hash,
        ack_checkpoint_id=ack_checkpoint_id,
    )

    node_session.status = NodeSessionStatus.ACTIVE
    node_session.last_seen_at = utcnow_naive()

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
    await session.flush()

    if payload.status == CheckpointStatus.GREEN:
        mark_node_attempt_succeeded(attempt.flow_node, attempt)
        end_node_session(attempt.flow_node.node_session)
        await _publish_green_checkpoint_context_item(
            session,
            flow=flow,
            flow_node=attempt.flow_node,
            node_attempt=attempt,
            checkpoint=checkpoint,
        )
    elif payload.status == CheckpointStatus.BLOCKED:
        mark_node_attempt_blocked(flow, attempt.flow_node, attempt)
        idle_node_session(attempt.flow_node.node_session)
    elif payload.status == CheckpointStatus.RETRY:
        mark_node_attempt_failed(attempt.flow_node, attempt)
        attempt.flow_node.state = FlowNodeState.READY
        end_node_session(attempt.flow_node.node_session)
    elif payload.status == CheckpointStatus.NEEDS_APPROVAL:
        mark_node_attempt_blocked(flow, attempt.flow_node, attempt)
        idle_node_session(attempt.flow_node.node_session)
        existing_pending_approval = await session.scalar(
            select(Approval.id)
            .where(Approval.node_attempt_id == attempt.id)
            .where(Approval.status == ApprovalStatus.PENDING)
            .limit(1)
        )
        if existing_pending_approval is None:
            flow.approvals.append(
                Approval(
                    flow_id=flow.id,
                    flow_node_id=attempt.flow_node_id,
                    node_attempt_id=attempt.id,
                    reason=payload.recommended_next_action or payload.summary,
                    request_payload=payload.payload,
                )
            )

    await upsert_runtime_container(
        session,
        flow=flow,
        flow_node=attempt.flow_node,
        node_attempt=attempt,
        node_session=attempt.flow_node.node_session,
        manifest=manifest,
    )
    await session.flush()

    refresh_flow_status(flow)

    return checkpoint


async def list_flow_checkpoints(session: AsyncSession, flow_id: UUID) -> list[NodeCheckpoint]:
    flow = await session.get(Flow, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")

    result = await session.scalars(
        select(NodeCheckpoint)
        .where(NodeCheckpoint.flow_id == flow_id)
        .where(NodeCheckpoint.sequence_no > 0)
        .order_by(NodeCheckpoint.created_at.asc(), NodeCheckpoint.sequence_no.asc())
    )
    return list(result.all())
