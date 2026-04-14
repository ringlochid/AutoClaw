from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ApprovalStatus,
    ContextItemKind,
    ContextItemScope,
    ContextItemStatus,
    ContextManifestStatus,
    FlowNodeState,
    FlowRevisionStatus,
    FlowStatus,
    NodeAttemptStatus,
    NodeSessionStatus,
    TaskStatus,
)
from app.core.errors import ConflictError, InvalidDefinitionError, NotFoundError
from app.db.models.runtime import (
    CompiledPlan,
    ContextItem,
    Flow,
    FlowEdge,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodeCheckpoint,
)
from app.runtime.dispatcher import ensure_node_session, project_context_manifest
from app.runtime.scheduler import (
    all_nodes_done,
    first_ready_node,
    first_running_node,
    open_nodes,
    ordered_nodes,
    pause_open_nodes,
    release_next_unstarted_node,
    restore_paused_nodes,
)
from app.schemas.runtime import FlowStartFromWorkflowCreate
from app.services.compiler_service import compile_published_workflow
from app.services.task_service import create_task


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hash_json(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _set_flow_status(flow: Flow, status: FlowStatus) -> None:
    flow.status = status
    if status == FlowStatus.PENDING:
        flow.task.status = TaskStatus.PENDING
    elif status == FlowStatus.RUNNING:
        flow.task.status = TaskStatus.RUNNING
    elif status in {FlowStatus.BLOCKED, FlowStatus.PAUSED}:
        flow.task.status = TaskStatus.BLOCKED
    elif status == FlowStatus.FAILED:
        flow.task.status = TaskStatus.FAILED
    elif status == FlowStatus.SUCCEEDED:
        flow.task.status = TaskStatus.SUCCEEDED
    elif status == FlowStatus.CANCELLED:
        flow.task.status = TaskStatus.CANCELLED


def _build_node_path(compiled_node_key: str, parent: FlowNode | None) -> str:
    return compiled_node_key if parent is None else f"{parent.node_path}.{compiled_node_key}"


async def _latest_attempt_for_node(
    session: AsyncSession,
    flow_node_id: UUID,
) -> NodeAttempt | None:
    return cast(
        NodeAttempt | None,
        await session.scalar(
            select(NodeAttempt)
            .where(NodeAttempt.flow_node_id == flow_node_id)
            .order_by(NodeAttempt.number.desc())
            .limit(1)
        ),
    )


async def _resumable_waiting_node(
    session: AsyncSession,
    flow: Flow,
) -> tuple[FlowNode, NodeAttempt] | None:
    for node in ordered_nodes(flow):
        if node.state != FlowNodeState.WAITING:
            continue
        latest_attempt = await _latest_attempt_for_node(session, node.id)
        if latest_attempt is None:
            continue
        if latest_attempt.status in {NodeAttemptStatus.BLOCKED, NodeAttemptStatus.PENDING}:
            return node, latest_attempt
    return None


async def _next_unstarted_node(_session: AsyncSession, flow: Flow) -> FlowNode | None:
    ready_node = first_ready_node(flow)
    if ready_node is not None:
        return ready_node

    return release_next_unstarted_node(flow)


async def _create_flow(
    session: AsyncSession,
    *,
    task_id: UUID,
    compiled_plan_id: UUID,
) -> Flow:
    flow = Flow(
        task_id=task_id,
        seed_compiled_plan_id=compiled_plan_id,
        status=FlowStatus.PENDING,
        execution_no=1,
    )
    session.add(flow)
    await session.flush()
    return flow


async def _create_initial_flow_revision(
    session: AsyncSession,
    *,
    flow: Flow,
    compiled_plan: CompiledPlan,
) -> FlowRevision:
    flow_revision = FlowRevision(
        flow_id=flow.id,
        revision_no=1,
        compiled_plan_id=compiled_plan.id,
        status=FlowRevisionStatus.ACTIVE,
        reason="initial materialization from compiled plan",
        source_patch_payload={},
        adopted_at=_utcnow_naive(),
    )
    session.add(flow_revision)
    await session.flush()
    flow.active_flow_revision_id = flow_revision.id
    await session.flush()
    return flow_revision


async def _materialize_flow_graph(
    session: AsyncSession,
    *,
    flow: Flow,
    flow_revision: FlowRevision,
    compiled_plan: CompiledPlan,
) -> list[FlowNode]:
    node_by_key: dict[str, FlowNode] = {}
    flow_nodes: list[FlowNode] = []

    for compiled_node in compiled_plan.nodes:
        parent = node_by_key.get(compiled_node.parent_node_key or "")
        flow_node = FlowNode(
            flow_id=flow.id,
            flow_revision_id=flow_revision.id,
            source_compiled_plan_node_id=compiled_node.id,
            parent_flow_node_id=parent.id if parent is not None else None,
            node_key=compiled_node.node_key,
            node_path=_build_node_path(compiled_node.node_key, parent),
            state=FlowNodeState.WAITING,
            order_index=compiled_node.order_index,
            status_payload={"mode": compiled_node.mode.value},
        )
        session.add(flow_node)
        await session.flush()
        node_by_key[compiled_node.node_key] = flow_node
        flow_nodes.append(flow_node)

    for compiled_edge in compiled_plan.edges:
        from_flow_node = node_by_key[compiled_edge.from_node_key]
        to_flow_node = node_by_key[compiled_edge.to_node_key]
        session.add(
            FlowEdge(
                flow_id=flow.id,
                flow_revision_id=flow_revision.id,
                from_flow_node_id=from_flow_node.id,
                to_flow_node_id=to_flow_node.id,
                edge_kind=compiled_edge.edge_kind,
                condition_expr=compiled_edge.condition_expr,
            )
        )

    incoming_node_keys = {compiled_edge.to_node_key for compiled_edge in compiled_plan.edges}
    for flow_node in flow_nodes:
        if flow_node.node_key not in incoming_node_keys:
            flow_node.state = FlowNodeState.READY

    await session.flush()
    return flow_nodes


async def _seed_task_context(
    session: AsyncSession,
    *,
    flow: Flow,
) -> ContextItem:
    payload = cast(dict[str, object], flow.task.input_payload)
    item = ContextItem(
        task_id=flow.task_id,
        scope=ContextItemScope.TASK_SHARED,
        kind=ContextItemKind.FACT,
        visibility_policy={"default": "shared"},
        status=ContextItemStatus.PUBLISHED,
        title="task-input",
        storage_uri=f"task://{flow.task_id}/input_payload",
        content_hash=_hash_json(payload),
        published_by="system:task-create",
        published_at=_utcnow_naive(),
    )
    session.add(item)
    await session.flush()
    return item


async def start_flow_from_workflow(
    session: AsyncSession,
    *,
    workflow_key: str,
    payload: FlowStartFromWorkflowCreate,
) -> tuple[Flow, FlowRevision, list[FlowNode]]:
    compiled_plan = await compile_published_workflow(session, workflow_key)
    if not compiled_plan.nodes:
        raise InvalidDefinitionError("Compiled workflow produced no nodes")

    task = await create_task(session, payload.task)
    flow = await _create_flow(session, task_id=task.id, compiled_plan_id=compiled_plan.id)
    flow.task = task
    flow_revision = await _create_initial_flow_revision(
        session,
        flow=flow,
        compiled_plan=compiled_plan,
    )
    flow_nodes = await _materialize_flow_graph(
        session,
        flow=flow,
        flow_revision=flow_revision,
        compiled_plan=compiled_plan,
    )
    await _seed_task_context(session, flow=flow)
    _set_flow_status(flow, FlowStatus.PENDING)
    await session.flush()
    return flow, flow_revision, flow_nodes


async def get_flow_with_relations(session: AsyncSession, flow_id: UUID) -> Flow | None:
    stmt = (
        select(Flow)
        .options(
            selectinload(Flow.task),
            selectinload(Flow.approvals),
            selectinload(Flow.context_manifests),
            selectinload(Flow.active_flow_revision)
            .selectinload(FlowRevision.nodes)
            .selectinload(FlowNode.attempts)
            .selectinload(NodeAttempt.context_manifests),
            selectinload(Flow.active_flow_revision)
            .selectinload(FlowRevision.nodes)
            .selectinload(FlowNode.attempts)
            .selectinload(NodeAttempt.checkpoints),
            selectinload(Flow.active_flow_revision)
            .selectinload(FlowRevision.nodes)
            .selectinload(FlowNode.node_session),
            selectinload(Flow.active_flow_revision).selectinload(FlowRevision.edges),
        )
        .where(Flow.id == flow_id)
    )
    return cast(Flow | None, await session.scalar(stmt))


async def continue_flow(session: AsyncSession, flow_id: UUID) -> Flow:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")
    if flow.status in {FlowStatus.CANCELLED, FlowStatus.FAILED, FlowStatus.SUCCEEDED}:
        raise ConflictError(f"Flow is already terminal: {flow.status.value}")

    if flow.status == FlowStatus.PAUSED:
        restore_paused_nodes(flow)

    if first_running_node(flow) is not None:
        _set_flow_status(flow, FlowStatus.RUNNING)
        await session.flush()
        return flow

    pending_approvals = [
        approval for approval in flow.approvals if approval.status == ApprovalStatus.PENDING
    ]
    if pending_approvals:
        _set_flow_status(flow, FlowStatus.BLOCKED)
        await session.flush()
        raise ConflictError("Flow is waiting on pending approvals")

    projected_manifests = [
        manifest
        for manifest in flow.context_manifests
        if manifest.status == ContextManifestStatus.PROJECTED
    ]
    if projected_manifests:
        _set_flow_status(flow, FlowStatus.BLOCKED)
        await session.flush()
        raise ConflictError("Flow is waiting on context acknowledgement")

    if all_nodes_done(flow):
        _set_flow_status(flow, FlowStatus.SUCCEEDED)
        await session.flush()
        return flow

    resumable = await _resumable_waiting_node(session, flow)
    if resumable is not None:
        resumable_node, latest_attempt = resumable
        latest_attempt.status = NodeAttemptStatus.RUNNING
        resumable_node.state = FlowNodeState.RUNNING
        if resumable_node.node_session is not None:
            resumable_node.node_session.status = NodeSessionStatus.ACTIVE
            resumable_node.node_session.last_seen_at = _utcnow_naive()
        _set_flow_status(flow, FlowStatus.RUNNING)
        await session.flush()
        return flow

    ready_node = await _next_unstarted_node(session, flow)
    if ready_node is None:
        raise ConflictError("Flow has no runnable nodes")

    previous_attempt = await _latest_attempt_for_node(session, ready_node.id)
    node_attempt = NodeAttempt(
        flow_id=flow.id,
        flow_revision_id=flow.active_flow_revision_id,
        flow_node_id=ready_node.id,
        number=(previous_attempt.number + 1) if previous_attempt is not None else 1,
        status=NodeAttemptStatus.BLOCKED,
        retry_of_node_attempt_id=(previous_attempt.id if previous_attempt is not None else None),
        started_at=_utcnow_naive(),
    )
    session.add(node_attempt)
    await session.flush()

    node_session = await ensure_node_session(
        session,
        flow=flow,
        flow_node=ready_node,
        node_attempt=node_attempt,
    )
    await project_context_manifest(
        session,
        flow=flow,
        flow_node=ready_node,
        node_attempt=node_attempt,
        node_session=node_session,
    )
    ready_node.state = FlowNodeState.WAITING
    node_session.status = NodeSessionStatus.IDLE
    _set_flow_status(flow, FlowStatus.BLOCKED)
    await session.flush()
    return flow


async def pause_flow(session: AsyncSession, flow_id: UUID) -> tuple[Flow, list[FlowNode]]:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")
    if flow.status in {FlowStatus.CANCELLED, FlowStatus.FAILED, FlowStatus.SUCCEEDED}:
        raise ConflictError(f"Flow is already terminal: {flow.status.value}")

    paused_nodes = pause_open_nodes(flow)
    for node in paused_nodes:
        latest_attempt = node.attempts[-1] if node.attempts else None
        if latest_attempt is not None and latest_attempt.status == NodeAttemptStatus.RUNNING:
            latest_attempt.status = NodeAttemptStatus.BLOCKED
        if node.node_session is not None and node.node_session.status == NodeSessionStatus.ACTIVE:
            node.node_session.status = NodeSessionStatus.IDLE
            node.node_session.last_seen_at = _utcnow_naive()

    _set_flow_status(flow, FlowStatus.PAUSED)
    await session.flush()
    return flow, paused_nodes


async def retry_flow_node(
    session: AsyncSession,
    *,
    flow_id: UUID,
    flow_node_id: UUID,
) -> tuple[Flow, NodeAttempt]:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")
    if flow.status in {FlowStatus.CANCELLED, FlowStatus.FAILED, FlowStatus.SUCCEEDED}:
        raise ConflictError(f"Flow is already terminal: {flow.status.value}")
    if flow.active_flow_revision is None:
        raise ConflictError("Flow has no active revision")

    flow_node = next(
        (node for node in flow.active_flow_revision.nodes if node.id == flow_node_id),
        None,
    )
    if flow_node is None:
        raise NotFoundError(f"No flow node found: {flow_node_id}")

    latest_attempt = flow_node.attempts[-1] if flow_node.attempts else None
    if latest_attempt is not None and latest_attempt.status not in {
        NodeAttemptStatus.BLOCKED,
        NodeAttemptStatus.FAILED,
        NodeAttemptStatus.CANCELLED,
        NodeAttemptStatus.ABORTED,
    }:
        raise ConflictError("Flow node is not in a retryable state")

    for approval in flow.approvals:
        if approval.node_attempt_id == (latest_attempt.id if latest_attempt is not None else None):
            if approval.status == ApprovalStatus.PENDING:
                approval.status = ApprovalStatus.EXPIRED
                approval.resolution_payload = {"reason": "superseded-by-operator-retry"}

    for manifest in flow.context_manifests:
        if manifest.node_attempt_id == (latest_attempt.id if latest_attempt is not None else None):
            if manifest.status == ContextManifestStatus.PROJECTED:
                manifest.status = ContextManifestStatus.SUPERSEDED

    if latest_attempt is not None and latest_attempt.status not in {
        NodeAttemptStatus.CANCELLED,
        NodeAttemptStatus.FAILED,
        NodeAttemptStatus.ABORTED,
    }:
        latest_attempt.status = NodeAttemptStatus.ABORTED
        latest_attempt.finished_at = _utcnow_naive()

    if flow_node.node_session is not None:
        flow_node.node_session.status = NodeSessionStatus.ENDED
        flow_node.node_session.ended_at = _utcnow_naive()
        flow_node.node_session.node_attempt_id = None

    node_attempt = NodeAttempt(
        flow_id=flow.id,
        flow_revision_id=flow.active_flow_revision_id,
        flow_node_id=flow_node.id,
        number=(latest_attempt.number + 1) if latest_attempt is not None else 1,
        status=NodeAttemptStatus.BLOCKED,
        retry_of_node_attempt_id=(latest_attempt.id if latest_attempt is not None else None),
        started_at=_utcnow_naive(),
    )
    session.add(node_attempt)
    await session.flush()

    node_session = await ensure_node_session(
        session,
        flow=flow,
        flow_node=flow_node,
        node_attempt=node_attempt,
    )
    await project_context_manifest(
        session,
        flow=flow,
        flow_node=flow_node,
        node_attempt=node_attempt,
        node_session=node_session,
    )
    flow_node.state = FlowNodeState.WAITING
    node_session.status = NodeSessionStatus.IDLE
    _set_flow_status(flow, FlowStatus.BLOCKED)
    await session.flush()
    return flow, node_attempt


async def cancel_flow(session: AsyncSession, flow_id: UUID) -> Flow:
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")
    if flow.status == FlowStatus.CANCELLED:
        return flow
    if flow.status in {FlowStatus.FAILED, FlowStatus.SUCCEEDED}:
        raise ConflictError(f"Flow is already terminal: {flow.status.value}")

    for node in open_nodes(flow):
        latest_attempt = node.attempts[-1] if node.attempts else None
        if latest_attempt is not None and latest_attempt.status in {
            NodeAttemptStatus.PENDING,
            NodeAttemptStatus.RUNNING,
            NodeAttemptStatus.BLOCKED,
        }:
            latest_attempt.status = NodeAttemptStatus.CANCELLED
            latest_attempt.finished_at = _utcnow_naive()
        if node.node_session is not None:
            node.node_session.status = NodeSessionStatus.ENDED
            node.node_session.ended_at = _utcnow_naive()
            node.node_session.node_attempt_id = None

    pause_open_nodes(flow)
    _set_flow_status(flow, FlowStatus.CANCELLED)
    await session.flush()
    return flow


async def list_flow_checkpoints(session: AsyncSession, flow_id: UUID) -> list[NodeCheckpoint]:
    result = await session.scalars(
        select(NodeCheckpoint)
        .where(NodeCheckpoint.flow_id == flow_id)
        .order_by(NodeCheckpoint.created_at.asc(), NodeCheckpoint.sequence_no.asc())
    )
    return list(result.all())


__all__ = [
    "cancel_flow",
    "continue_flow",
    "get_flow_with_relations",
    "list_flow_checkpoints",
    "pause_flow",
    "retry_flow_node",
    "start_flow_from_workflow",
]
