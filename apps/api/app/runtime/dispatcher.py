from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ContextItemStatus,
    ContextManifestStatus,
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


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
    node_session.last_seen_at = _utcnow_naive()
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
        projected_at=_utcnow_naive(),
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
            selectinload(ContextManifest.flow_node).selectinload(FlowNode.node_session),
            selectinload(ContextManifest.node_attempt),
            selectinload(ContextManifest.node_session),
        )
        .where(ContextManifest.id == manifest_id)
    )
    return cast(ContextManifest | None, await session.scalar(stmt))


async def acknowledge_context_manifest(
    session: AsyncSession,
    manifest_id: UUID,
) -> ContextManifest:
    manifest = await get_context_manifest(session, manifest_id)
    if manifest is None:
        raise NotFoundError(f"No context manifest found: {manifest_id}")
    if manifest.status == ContextManifestStatus.ACKED:
        return manifest
    if manifest.node_attempt.status in {
        NodeAttemptStatus.CANCELLED,
        NodeAttemptStatus.FAILED,
        NodeAttemptStatus.SUCCEEDED,
        NodeAttemptStatus.ABORTED,
    }:
        raise ConflictError("Context manifest belongs to a terminal node attempt")

    manifest.status = ContextManifestStatus.ACKED
    manifest.acked_at = _utcnow_naive()
    manifest.node_attempt.status = NodeAttemptStatus.RUNNING
    manifest.flow_node.state = manifest.flow_node.state.RUNNING
    manifest.flow.status = manifest.flow.status.RUNNING
    manifest.flow.task.status = manifest.flow.task.status.RUNNING
    if manifest.node_session is not None:
        manifest.node_session.status = NodeSessionStatus.ACTIVE
        manifest.node_session.last_seen_at = _utcnow_naive()
    await session.flush()
    return manifest
