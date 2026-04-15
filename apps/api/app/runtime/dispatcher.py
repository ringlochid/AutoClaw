from __future__ import annotations

import hashlib
import json
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ContextItemStatus,
    ContextManifestStatus,
    FlowStatus,
    NodeAttemptStatus,
    NodeSessionStatus,
)
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import (
    ContextItem,
    ContextManifest,
    Flow,
    FlowNode,
    NodeAttempt,
    NodeSession,
)
from app.runtime.control import (
    ensure_current_attempt,
    ensure_flow_not_terminal,
    lock_flow,
    refresh_flow_status,
    waiting_block_reason,
)
from app.runtime.state import mark_node_attempt_blocked, mark_node_attempt_running, utcnow_naive


def _hash_payload(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def ensure_node_session(
    session: AsyncSession,
    *,
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
) -> NodeSession:
    node_session = flow_node.node_session
    if node_session is None:
        node_session = NodeSession(
            flow_id=flow.id,
            flow_node_id=flow_node.id,
            node_attempt_id=node_attempt.id,
            provider_session_key=f"ocl_{uuid4().hex[:12]}",
            status=NodeSessionStatus.IDLE,
        )
        session.add(node_session)
        await session.flush()
        flow_node.node_session = node_session
        return node_session

    if node_session.status == NodeSessionStatus.ENDED:
        node_session.ended_at = None
    node_session.node_attempt_id = node_attempt.id
    node_session.status = NodeSessionStatus.IDLE
    node_session.last_seen_at = utcnow_naive()
    await session.flush()
    return node_session


async def project_context_manifest(
    session: AsyncSession,
    *,
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
    node_session: NodeSession | None,
) -> ContextManifest:
    context_items = list(
        (
            await session.scalars(
                select(ContextItem)
                .where(
                    ContextItem.task_id == flow.task_id,
                    ContextItem.status == ContextItemStatus.PUBLISHED,
                )
                .order_by(ContextItem.published_at.asc(), ContextItem.created_at.asc())
            )
        ).all()
    )
    required_items = [
        {
            "context_item_id": str(item.id),
            "scope": item.scope.value,
            "kind": item.kind.value,
            "title": item.title,
            "storage_uri": item.storage_uri,
            "content_hash": item.content_hash,
        }
        for item in context_items
    ]
    manifest_payload: dict[str, object] = {
        "execution_phase": "bootstrap",
        "required_items": required_items,
        "optional_items": [],
        "node": {
            "flow_node_id": str(flow_node.id),
            "node_key": flow_node.node_key,
            "node_path": flow_node.node_path,
            "mode": flow_node.status_payload.get("mode"),
        },
    }
    manifest_no = (
        await session.scalar(
            select(func.coalesce(func.max(ContextManifest.manifest_no), 0) + 1).where(
                ContextManifest.node_attempt_id == node_attempt.id
            )
        )
    ) or 1
    manifest = ContextManifest(
        flow_id=flow.id,
        flow_node_id=flow_node.id,
        node_attempt_id=node_attempt.id,
        node_session_id=node_session.id if node_session is not None else None,
        manifest_no=int(manifest_no),
        manifest_payload=manifest_payload,
        manifest_hash=_hash_payload(manifest_payload),
        status=ContextManifestStatus.PROJECTED,
        projected_at=utcnow_naive(),
    )
    session.add(manifest)
    await session.flush()
    return manifest


async def get_context_manifest(
    session: AsyncSession,
    manifest_id: UUID,
) -> ContextManifest | None:
    stmt = (
        select(ContextManifest)
        .options(
            selectinload(ContextManifest.flow).selectinload(Flow.task),
            selectinload(ContextManifest.flow).selectinload(Flow.approvals),
            selectinload(ContextManifest.flow).selectinload(Flow.context_manifests),
            selectinload(ContextManifest.flow_node).selectinload(FlowNode.node_session),
            selectinload(ContextManifest.flow_node).selectinload(FlowNode.attempts),
            selectinload(ContextManifest.node_attempt).selectinload(NodeAttempt.checkpoints),
            selectinload(ContextManifest.node_session),
        )
        .where(ContextManifest.id == manifest_id)
    )
    return cast(ContextManifest | None, await session.scalar(stmt))


async def acknowledge_context_manifest(
    session: AsyncSession,
    manifest_id: UUID,
) -> ContextManifest:
    flow_id = await session.scalar(
        select(ContextManifest.flow_id).where(ContextManifest.id == manifest_id)
    )
    if flow_id is None:
        raise NotFoundError(f"No context manifest found: {manifest_id}")

    await lock_flow(session, flow_id)
    manifest = await get_context_manifest(session, manifest_id)
    if manifest is None:
        raise NotFoundError(f"No context manifest found: {manifest_id}")
    if manifest.status == ContextManifestStatus.ACKED:
        return manifest
    ensure_flow_not_terminal(manifest.flow)
    if manifest.status != ContextManifestStatus.PROJECTED:
        raise ConflictError("Context manifest is not awaiting acknowledgement")
    if manifest.flow.status == FlowStatus.PAUSED:
        raise ConflictError("Flow is paused; context acknowledgement cannot resume execution")

    ensure_current_attempt(
        manifest.flow,
        manifest.flow_node,
        manifest.node_attempt,
        allowed_statuses={NodeAttemptStatus.BLOCKED},
        require_current_session=manifest.node_session is not None,
        node_session=manifest.node_session,
    )

    manifest.status = ContextManifestStatus.ACKED
    manifest.acked_at = utcnow_naive()

    if waiting_block_reason(manifest.flow, manifest.flow_node, manifest.node_attempt) is None:
        mark_node_attempt_running(manifest.flow, manifest.flow_node, manifest.node_attempt)
        if manifest.node_session is not None:
            manifest.node_session.status = NodeSessionStatus.ACTIVE
            manifest.node_session.last_seen_at = utcnow_naive()
    else:
        mark_node_attempt_blocked(manifest.flow, manifest.flow_node, manifest.node_attempt)
        if manifest.node_session is not None:
            manifest.node_session.status = NodeSessionStatus.IDLE
            manifest.node_session.last_seen_at = utcnow_naive()
        refresh_flow_status(manifest.flow)

    await session.flush()
    return manifest
