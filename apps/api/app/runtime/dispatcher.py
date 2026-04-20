from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import load_settings
from app.core.enums import (
    CheckpointStatus,
    ContextItemStatus,
    ContextManifestStatus,
    FlowStatus,
    NodeSessionStatus,
    WaitReason,
)
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import (
    CompiledPlanNode,
    ContextItem,
    ContextManifest,
    Flow,
    FlowNode,
    NodeAttempt,
    NodeCheckpoint,
    NodeSession,
)
from app.paths import ensure_task_dirs
from app.runtime.callback_bindings import validate_manifest_ack_binding
from app.runtime.context_visibility import is_context_item_visible_to_target
from app.runtime.control import (
    lock_flow,
    refresh_flow_status,
    supersede_projected_manifests,
    waiting_block_reason,
)
from app.runtime.resources import resolve_manifest_projection_resources
from app.runtime.state import mark_node_attempt_blocked, mark_node_attempt_running, utcnow_naive


def _hash_payload(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _task_key(flow: Flow) -> str | None:
    task = flow.task
    if task is None or not isinstance(task.input_payload, dict):
        return None
    value = task.input_payload.get("_task_key")
    return value if isinstance(value, str) and value.strip() else None


def _manifest_materialized_path(flow: Flow, flow_node: FlowNode, manifest_no: int) -> Path:
    directories = ensure_task_dirs(flow.task_id, load_settings().data_dir, task_key=_task_key(flow))
    safe_node_key = "".join(
        ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in flow_node.node_key
    )
    return directories["manifests"] / f"{safe_node_key}--manifest-{manifest_no:04d}.json"


def _write_manifest_file(
    flow: Flow,
    *,
    flow_node: FlowNode,
    manifest_no: int,
    payload: dict[str, object],
    manifest_hash: str,
) -> Path:
    path = _manifest_materialized_path(flow, flow_node, manifest_no)
    envelope = {
        "flow_id": str(flow.id),
        "task_id": str(flow.task_id),
        "manifest_no": manifest_no,
        "manifest_hash": manifest_hash,
        "payload": payload,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


async def ensure_node_session(
    session: AsyncSession,
    *,
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
) -> NodeSession:
    inspection = sa_inspect(flow_node)
    if "node_session" in inspection.unloaded:
        node_session = cast(
            NodeSession | None,
            await session.scalar(
                select(NodeSession).where(NodeSession.flow_node_id == flow_node.id)
            ),
        )
    else:
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


async def _checkpoint_inline_content_by_id(
    session: AsyncSession,
    *,
    flow: Flow,
    items: list[ContextItem],
) -> dict[UUID, dict[str, Any]]:
    checkpoint_ids = [
        item.source_checkpoint_id for item in items if item.source_checkpoint_id is not None
    ]
    if not checkpoint_ids:
        return {}

    checkpoints = list(
        (
            await session.scalars(
                select(NodeCheckpoint).where(NodeCheckpoint.id.in_(checkpoint_ids))
            )
        ).all()
    )
    nodes_by_id = {}
    if flow.active_flow_revision is not None:
        nodes_by_id = {node.id: node for node in flow.active_flow_revision.nodes}

    payloads: dict[UUID, dict[str, Any]] = {}
    for checkpoint in checkpoints:
        flow_node = nodes_by_id.get(checkpoint.flow_node_id)
        payloads[checkpoint.id] = {
            "checkpoint_id": str(checkpoint.id),
            "flow_node_id": str(checkpoint.flow_node_id),
            "flow_node_key": flow_node.node_key if flow_node is not None else None,
            "flow_node_path": flow_node.node_path if flow_node is not None else None,
            "node_attempt_id": str(checkpoint.node_attempt_id),
            "status": checkpoint.status.value,
            "summary": checkpoint.summary,
            "payload": checkpoint.payload,
            "failure_signature": checkpoint.failure_signature,
            "recommended_next_action": checkpoint.recommended_next_action,
            "wait_reason": checkpoint.wait_reason.value if checkpoint.wait_reason else None,
            "created_at": checkpoint.created_at.isoformat(),
        }
    return payloads


def _inline_manifest_item_content(
    flow: Flow,
    item: ContextItem,
    *,
    checkpoint_payloads: dict[UUID, dict[str, Any]],
) -> Any | None:
    inline_content = item.metadata_.get("inline_content")
    if inline_content is not None:
        return inline_content

    if item.source_checkpoint_id is not None:
        return checkpoint_payloads.get(item.source_checkpoint_id)

    task_uri = f"task://{flow.task_id}/input_payload"
    if item.storage_uri != task_uri:
        return None

    task = flow.task
    if task is None:
        return None
    return task.input_payload


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
    checkpoint_payloads = await _checkpoint_inline_content_by_id(
        session,
        flow=flow,
        items=context_items,
    )
    required_items = []
    for item in context_items:
        if not is_context_item_visible_to_target(
            item,
            flow_id=flow.id,
            flow_node_id=flow_node.id,
            node_attempt_id=node_attempt.id,
        ):
            continue

        manifest_item: dict[str, Any] = {
            "context_item_id": str(item.id),
            "scope": item.scope.value,
            "kind": item.kind.value,
            "title": item.title,
            "storage_uri": item.storage_uri,
            "content_hash": item.content_hash,
        }
        inline_content = _inline_manifest_item_content(
            flow,
            item,
            checkpoint_payloads=checkpoint_payloads,
        )
        if inline_content is not None:
            manifest_item["inline_content"] = inline_content
        required_items.append(manifest_item)
    compiled_node = flow_node.source_compiled_plan_node
    if compiled_node is None and flow_node.source_compiled_plan_node_id is not None:
        compiled_node = cast(
            CompiledPlanNode | None,
            await session.scalar(
                select(CompiledPlanNode).where(
                    CompiledPlanNode.id == flow_node.source_compiled_plan_node_id
                )
            ),
        )
    if compiled_node is None:
        raise ConflictError(f"Flow node {flow_node.id} is missing source compiled plan node")

    resolved_resources, manifest_root = await resolve_manifest_projection_resources(
        session,
        task=flow.task,
        compiled_node=compiled_node,
    )
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
        "task_defaults": compiled_node.effective_payload.get("task_defaults", {}),
        "resources": resolved_resources,
    }
    manifest_no = (
        await session.scalar(
            select(func.coalesce(func.max(ContextManifest.manifest_no), 0) + 1).where(
                ContextManifest.node_attempt_id == node_attempt.id
            )
        )
    ) or 1
    manifest_no = int(manifest_no)
    manifest_hash = _hash_payload(manifest_payload)
    materialized_path = _write_manifest_file(
        flow,
        flow_node=flow_node,
        manifest_no=manifest_no,
        payload=manifest_payload,
        manifest_hash=manifest_hash,
    )
    manifest = ContextManifest(
        flow_id=flow.id,
        flow_node_id=flow_node.id,
        node_attempt_id=node_attempt.id,
        node_session_id=node_session.id if node_session is not None else None,
        manifest_no=manifest_no,
        manifest_payload=manifest_payload,
        manifest_hash=manifest_hash,
        manifest_root_id=manifest_root.id if manifest_root is not None else None,
        status=ContextManifestStatus.PROJECTED,
        projected_at=utcnow_naive(),
    )
    manifest.manifest_payload.setdefault("materialized_path", str(materialized_path))
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


async def _ensure_manifest_ack_checkpoint(manifest: ContextManifest) -> None:
    if manifest.ack_checkpoint_id is not None:
        return

    checkpoint = NodeCheckpoint(
        id=uuid4(),
        flow_id=manifest.flow_id,
        flow_node_id=manifest.flow_node_id,
        node_attempt_id=manifest.node_attempt_id,
        sequence_no=0,
        status=CheckpointStatus.BLOCKED,
        summary="context manifest acknowledged",
        payload={
            "manifest_id": str(manifest.id),
            "manifest_hash": manifest.manifest_hash,
            "node_session_key": (
                manifest.node_session.provider_session_key
                if manifest.node_session is not None
                else None
            ),
        },
        wait_reason=WaitReason.CONTEXT,
    )
    manifest.node_attempt.checkpoints.append(checkpoint)
    manifest.ack_checkpoint_id = checkpoint.id


async def acknowledge_context_manifest(
    session: AsyncSession,
    manifest_id: UUID,
    *,
    manifest_hash: str,
    node_session_key: str,
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

    binding = validate_manifest_ack_binding(
        manifest,
        flow_id=flow_id,
        node_session_key=node_session_key,
        manifest_hash=manifest_hash,
    )
    manifest = binding.manifest
    if manifest.status == ContextManifestStatus.ACKED:
        return manifest
    if binding.flow.status == FlowStatus.PAUSED:
        raise ConflictError("Flow is paused; context acknowledgement cannot resume execution")

    supersede_projected_manifests(
        binding.flow,
        node_attempt_id=manifest.node_attempt_id,
        keep_manifest_id=manifest.id,
    )

    manifest.status = ContextManifestStatus.ACKED
    manifest.acked_at = utcnow_naive()
    await _ensure_manifest_ack_checkpoint(manifest)

    if waiting_block_reason(binding.flow, binding.flow_node, binding.node_attempt) is None:
        mark_node_attempt_running(binding.flow, binding.flow_node, binding.node_attempt)
        binding.node_session.status = NodeSessionStatus.ACTIVE
        binding.node_session.last_seen_at = utcnow_naive()
    else:
        mark_node_attempt_blocked(binding.flow, binding.flow_node, binding.node_attempt)
        binding.node_session.status = NodeSessionStatus.IDLE
        binding.node_session.last_seen_at = utcnow_naive()
        refresh_flow_status(binding.flow)
    await session.flush()
    return manifest
