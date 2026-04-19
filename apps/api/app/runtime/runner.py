from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import cast
from uuid import UUID

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

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
    WaitReason,
)
from app.core.errors import ConflictError, InvalidDefinitionError, NotFoundError
from app.db.models.runtime import (
    CompiledPlan,
    CompiledPlanNode,
    ContextItem,
    ContextManifest,
    Flow,
    FlowEdge,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodeCheckpoint,
    NodeSession,
    Task,
    TaskResourceBinding,
)
from app.runtime.control import (
    abort_attempt,
    cancel_attempt,
    end_node_session,
    expire_pending_approvals,
    idle_node_session,
    is_operator_retryable,
    is_waiting_attempt_resumable,
    latest_attempt,
    lock_flow,
    refresh_flow_status,
    supersede_projected_manifests,
    waiting_block_reason,
)
from app.runtime.dispatcher import ensure_node_session, project_context_manifest
from app.runtime.packaging import ensure_task_compose_for_compiled_plan
from app.runtime.resources import ensure_task_resources_for_compiled_plan
from app.runtime.scheduler import (
    all_nodes_done,
    first_ready_node,
    first_running_node,
    node_dependencies_satisfied,
    open_nodes,
    ordered_nodes,
    pause_open_nodes,
    restore_paused_nodes,
)
from app.runtime.state import (
    mark_node_attempt_blocked,
    mark_node_attempt_running,
    set_flow_status,
    utcnow_naive,
)
from app.schemas.runtime import FlowStartFromWorkflowCreate
from app.services.compiler_service import compile_published_workflow
from app.services.task_service import create_task

MAX_LOCAL_ADVANCE_STEPS = 64


def _hash_json(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


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


def _resumable_waiting_node(flow: Flow) -> tuple[FlowNode, NodeAttempt] | None:
    for node in ordered_nodes(flow):
        if node.state != FlowNodeState.WAITING:
            continue
        current_attempt = latest_attempt(node)
        if current_attempt is None:
            continue
        if is_waiting_attempt_resumable(flow, node, current_attempt):
            return node, current_attempt
    return None


async def _next_unstarted_node(session: AsyncSession, flow: Flow) -> FlowNode | None:
    ready_node = first_ready_node(flow)
    if ready_node is not None:
        return ready_node

    if flow.active_flow_revision_id is None:
        return None

    loaded_nodes = list(
        (
            await session.scalars(
                select(FlowNode)
                .where(FlowNode.flow_revision_id == flow.active_flow_revision_id)
                .options(
                    selectinload(FlowNode.attempts).selectinload(NodeAttempt.checkpoints),
                    selectinload(FlowNode.incoming_edges),
                )
                .order_by(FlowNode.order_index.asc())
            )
        ).all()
    )
    loaded_nodes_by_id = {str(node.id): node for node in loaded_nodes}
    live_nodes_by_id = {node.id: node for node in ordered_nodes(flow)}

    for loaded_node in loaded_nodes:
        if (
            loaded_node.state == FlowNodeState.WAITING
            and not loaded_node.attempts
            and node_dependencies_satisfied(loaded_node, loaded_nodes_by_id)
        ):
            live_node = live_nodes_by_id.get(loaded_node.id)
            if live_node is None:
                return None
            live_node.state = FlowNodeState.READY
            return live_node

    return None


def _next_attempt_number(previous_attempt: NodeAttempt | None) -> int:
    return (previous_attempt.number + 1) if previous_attempt is not None else 1


async def _create_blocked_node_attempt(
    session: AsyncSession,
    *,
    flow: Flow,
    flow_node: FlowNode,
    previous_attempt: NodeAttempt | None,
) -> NodeAttempt:
    node_attempt = NodeAttempt(
        flow_id=flow.id,
        flow_revision_id=flow.active_flow_revision_id,
        flow_node_id=flow_node.id,
        number=_next_attempt_number(previous_attempt),
        status=NodeAttemptStatus.BLOCKED,
        retry_of_node_attempt_id=(previous_attempt.id if previous_attempt is not None else None),
        started_at=utcnow_naive(),
    )
    session.add(node_attempt)
    await session.flush()
    return node_attempt


async def _bootstrap_node_attempt_context(
    session: AsyncSession,
    *,
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
) -> None:
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
    mark_node_attempt_blocked(flow, flow_node, node_attempt)
    idle_node_session(node_session)
    await session.flush()


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
        adopted_at=utcnow_naive(),
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
            logical_node_key=compiled_node.node_key,
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
        metadata_={"inline_content": payload},
        published_by="system:task-create",
        published_at=utcnow_naive(),
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

    task = await create_task(session, payload.task, bootstrap_defaults=False)
    await ensure_task_resources_for_compiled_plan(
        session,
        task=task,
        compiled_plan=compiled_plan,
        allow_create=True,
    )
    await ensure_task_compose_for_compiled_plan(
        session,
        task=task,
        compiled_plan=compiled_plan,
    )
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
    set_flow_status(flow, FlowStatus.PENDING)
    await session.flush()
    return flow, flow_revision, flow_nodes


async def get_flow_with_relations(session: AsyncSession, flow_id: UUID) -> Flow | None:
    stmt = (
        select(Flow)
        .execution_options(populate_existing=True)
        .options(
            selectinload(Flow.task)
            .selectinload(Task.resource_bindings)
            .selectinload(TaskResourceBinding.workspace_root),
            selectinload(Flow.task)
            .selectinload(Task.resource_bindings)
            .selectinload(TaskResourceBinding.context_space),
            selectinload(Flow.task)
            .selectinload(Task.resource_bindings)
            .selectinload(TaskResourceBinding.manifest_root),
            selectinload(Flow.approvals),
            selectinload(Flow.context_manifests).selectinload(ContextManifest.node_session),
            selectinload(Flow.flow_revisions),
            selectinload(Flow.active_flow_revision),
        )
        .where(Flow.id == flow_id)
    )
    flow = cast(Flow | None, await session.scalar(stmt))
    if flow is None or flow.active_flow_revision_id is None:
        return flow

    active_revision = flow.active_flow_revision
    if active_revision is None:
        return flow

    flow_nodes = list(
        (
            await session.scalars(
                select(FlowNode)
                .execution_options(populate_existing=True)
                .where(FlowNode.flow_revision_id == flow.active_flow_revision_id)
                .order_by(FlowNode.order_index.asc())
            )
        ).all()
    )
    node_by_id = {node.id: node for node in flow_nodes}
    node_ids = list(node_by_id)

    flow_edges = list(
        (
            await session.scalars(
                select(FlowEdge)
                .execution_options(populate_existing=True)
                .where(FlowEdge.flow_revision_id == flow.active_flow_revision_id)
                .order_by(FlowEdge.created_at.asc())
            )
        ).all()
    )

    attempts_by_node_id: dict[UUID, list[NodeAttempt]] = defaultdict(list)
    checkpoints_by_attempt_id: dict[UUID, list[NodeCheckpoint]] = defaultdict(list)
    manifests_by_attempt_id: dict[UUID, list[ContextManifest]] = defaultdict(list)
    sessions_by_node_id: dict[UUID, NodeSession] = {}
    incoming_edges_by_node_id: dict[UUID, list[FlowEdge]] = defaultdict(list)
    compiled_nodes_by_id: dict[UUID, CompiledPlanNode] = {}

    if node_ids:
        attempts = list(
            (
                await session.scalars(
                    select(NodeAttempt)
                    .execution_options(populate_existing=True)
                    .where(NodeAttempt.flow_node_id.in_(node_ids))
                    .order_by(NodeAttempt.flow_node_id.asc(), NodeAttempt.number.asc())
                )
            ).all()
        )
        attempt_ids = [attempt.id for attempt in attempts]
        for attempt in attempts:
            attempts_by_node_id[attempt.flow_node_id].append(attempt)

        if attempt_ids:
            checkpoints = list(
                (
                    await session.scalars(
                        select(NodeCheckpoint)
                        .execution_options(populate_existing=True)
                        .where(NodeCheckpoint.node_attempt_id.in_(attempt_ids))
                        .order_by(
                            NodeCheckpoint.node_attempt_id.asc(),
                            NodeCheckpoint.sequence_no.asc(),
                        )
                    )
                ).all()
            )
            for checkpoint in checkpoints:
                checkpoints_by_attempt_id[checkpoint.node_attempt_id].append(checkpoint)

            manifests = list(
                (
                    await session.scalars(
                        select(ContextManifest)
                        .options(selectinload(ContextManifest.node_session))
                        .execution_options(populate_existing=True)
                        .where(ContextManifest.node_attempt_id.in_(attempt_ids))
                        .order_by(
                            ContextManifest.node_attempt_id.asc(),
                            ContextManifest.manifest_no.asc(),
                        )
                    )
                ).all()
            )
            for manifest in manifests:
                if manifest.node_attempt_id is not None:
                    manifests_by_attempt_id[manifest.node_attempt_id].append(manifest)

        sessions = list(
            (
                await session.scalars(
                    select(NodeSession)
                    .execution_options(populate_existing=True)
                    .where(NodeSession.flow_node_id.in_(node_ids))
                )
            ).all()
        )
        sessions_by_node_id = {node_session.flow_node_id: node_session for node_session in sessions}

        compiled_node_ids = [
            node.source_compiled_plan_node_id
            for node in flow_nodes
            if node.source_compiled_plan_node_id is not None
        ]
        if compiled_node_ids:
            compiled_nodes = list(
                (
                    await session.scalars(
                        select(CompiledPlanNode)
                        .execution_options(populate_existing=True)
                        .where(CompiledPlanNode.id.in_(compiled_node_ids))
                    )
                ).all()
            )
            compiled_nodes_by_id = {
                compiled_node.id: compiled_node for compiled_node in compiled_nodes
            }

    for edge in flow_edges:
        from_node = node_by_id.get(edge.from_flow_node_id)
        to_node = node_by_id.get(edge.to_flow_node_id)
        if from_node is not None:
            set_committed_value(edge, "from_flow_node", from_node)
        if to_node is not None:
            set_committed_value(edge, "to_flow_node", to_node)
            incoming_edges_by_node_id[to_node.id].append(edge)

    for node in flow_nodes:
        attempts = attempts_by_node_id.get(node.id, [])
        set_committed_value(node, "attempts", attempts)
        set_committed_value(node, "node_session", sessions_by_node_id.get(node.id))
        compiled_plan_node = (
            compiled_nodes_by_id.get(node.source_compiled_plan_node_id)
            if node.source_compiled_plan_node_id is not None
            else None
        )
        set_committed_value(
            node,
            "source_compiled_plan_node",
            compiled_plan_node,
        )
        set_committed_value(node, "incoming_edges", incoming_edges_by_node_id.get(node.id, []))
        for attempt in attempts:
            set_committed_value(
                attempt,
                "checkpoints",
                checkpoints_by_attempt_id.get(attempt.id, []),
            )
            set_committed_value(
                attempt,
                "context_manifests",
                manifests_by_attempt_id.get(attempt.id, []),
            )

    revision_with_plan = await session.scalar(
        select(FlowRevision)
        .execution_options(populate_existing=True)
        .where(FlowRevision.id == flow.active_flow_revision_id)
        .options(selectinload(FlowRevision.compiled_plan))
    )

    set_committed_value(active_revision, "nodes", flow_nodes)
    set_committed_value(active_revision, "edges", flow_edges)
    if revision_with_plan is not None and (
        "compiled_plan" not in sa_inspect(revision_with_plan).unloaded
    ):
        set_committed_value(active_revision, "compiled_plan", revision_with_plan.compiled_plan)
    return flow


def _continue_conflict_for_boundary(flow: Flow) -> ConflictError:
    pending_approvals = [
        approval for approval in flow.approvals if approval.status == ApprovalStatus.PENDING
    ]
    if pending_approvals:
        return ConflictError("Flow is waiting on pending approvals")

    projected_manifests = [
        manifest
        for manifest in flow.context_manifests
        if manifest.status == ContextManifestStatus.PROJECTED
    ]
    if projected_manifests:
        return ConflictError("Flow is waiting on context acknowledgement")

    blocked_wait_reasons = {
        reason
        for node in ordered_nodes(flow)
        if node.state == FlowNodeState.WAITING
        for reason in [waiting_block_reason(flow, node, latest_attempt(node))]
        if reason is not None
    }
    if WaitReason.WATCHDOG in blocked_wait_reasons:
        return ConflictError("Flow is waiting on watchdog recovery")
    if blocked_wait_reasons:
        return ConflictError("Flow is waiting on a non-runnable boundary")
    return ConflictError("Flow has no runnable nodes")


def _advance_boundary_reason(flow: Flow) -> str | None:
    if first_running_node(flow) is not None:
        return "running"

    pending_approvals = [
        approval for approval in flow.approvals if approval.status == ApprovalStatus.PENDING
    ]
    if pending_approvals:
        return "pending-approvals"

    projected_manifests = [
        manifest
        for manifest in flow.context_manifests
        if manifest.status == ContextManifestStatus.PROJECTED
    ]
    if projected_manifests:
        return "projected-context-manifest"

    if all_nodes_done(flow):
        return "all-nodes-done"

    return None


async def _advance_flow_once(session: AsyncSession, flow: Flow) -> tuple[Flow, bool]:
    if first_running_node(flow) is not None:
        refresh_flow_status(flow)
        await session.flush()
        return flow, False

    pending_approvals = [
        approval for approval in flow.approvals if approval.status == ApprovalStatus.PENDING
    ]
    if pending_approvals:
        refresh_flow_status(flow)
        await session.flush()
        return flow, False

    projected_manifests = [
        manifest
        for manifest in flow.context_manifests
        if manifest.status == ContextManifestStatus.PROJECTED
    ]
    if projected_manifests:
        refresh_flow_status(flow)
        await session.flush()
        return flow, False

    if all_nodes_done(flow):
        refresh_flow_status(flow)
        await session.flush()
        return flow, False

    resumable = _resumable_waiting_node(flow)
    if resumable is not None:
        resumable_node, resumable_attempt = resumable
        mark_node_attempt_running(flow, resumable_node, resumable_attempt)
        if resumable_node.node_session is not None:
            resumable_node.node_session.status = NodeSessionStatus.ACTIVE
            resumable_node.node_session.last_seen_at = utcnow_naive()
        await session.flush()
        refreshed = await get_flow_with_relations(session, flow.id)
        if refreshed is None:
            raise NotFoundError(f"No flow found: {flow.id}")
        return refreshed, True

    ready_node = await _next_unstarted_node(session, flow)
    if ready_node is None:
        refresh_flow_status(flow)
        await session.flush()
        return flow, False

    previous_attempt = await _latest_attempt_for_node(session, ready_node.id)
    node_attempt = await _create_blocked_node_attempt(
        session,
        flow=flow,
        flow_node=ready_node,
        previous_attempt=previous_attempt,
    )
    await _bootstrap_node_attempt_context(
        session,
        flow=flow,
        flow_node=ready_node,
        node_attempt=node_attempt,
    )
    refreshed = await get_flow_with_relations(session, flow.id)
    if refreshed is None:
        raise NotFoundError(f"No flow found: {flow.id}")
    return refreshed, True


async def advance_flow_until_boundary(
    session: AsyncSession,
    flow_id: UUID,
    *,
    cause: str,
    resume_paused: bool = False,
    raise_on_conflict: bool = False,
) -> Flow:
    del cause

    await lock_flow(session, flow_id)
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")

    if flow.status in {FlowStatus.CANCELLED, FlowStatus.FAILED, FlowStatus.SUCCEEDED}:
        if raise_on_conflict:
            raise ConflictError(f"Flow is already terminal: {flow.status.value}")
        return flow

    if flow.status == FlowStatus.PAUSED:
        if not resume_paused:
            if raise_on_conflict:
                raise ConflictError("Flow is paused")
            return flow
        restore_paused_nodes(flow)
        await session.flush()
        refreshed = await get_flow_with_relations(session, flow.id)
        if refreshed is None:
            raise NotFoundError(f"No flow found: {flow.id}")
        flow = refreshed

    progressed_any = False
    for _step in range(MAX_LOCAL_ADVANCE_STEPS):
        boundary_reason = _advance_boundary_reason(flow)
        if boundary_reason is not None:
            refresh_flow_status(flow)
            await session.flush()
            if boundary_reason != "running" and not progressed_any and raise_on_conflict:
                raise _continue_conflict_for_boundary(flow)
            return flow

        flow, progressed = await _advance_flow_once(session, flow)
        if not progressed:
            refresh_flow_status(flow)
            await session.flush()
            if not progressed_any and raise_on_conflict:
                raise _continue_conflict_for_boundary(flow)
            return flow
        progressed_any = True

    raise ConflictError("Flow advancement exceeded max safe controller steps")


async def continue_flow(session: AsyncSession, flow_id: UUID) -> Flow:
    return await advance_flow_until_boundary(
        session,
        flow_id,
        cause="operator-continue",
        resume_paused=True,
        raise_on_conflict=True,
    )


async def pause_flow(session: AsyncSession, flow_id: UUID) -> tuple[Flow, list[FlowNode]]:
    await lock_flow(session, flow_id)
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
            idle_node_session(node.node_session)

    set_flow_status(flow, FlowStatus.PAUSED)
    await session.flush()
    return flow, paused_nodes


async def retry_flow_node(
    session: AsyncSession,
    *,
    flow_id: UUID,
    flow_node_id: UUID,
) -> tuple[Flow, NodeAttempt]:
    await lock_flow(session, flow_id)
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

    current_attempt = latest_attempt(flow_node)
    if current_attempt is None:
        raise ConflictError("Flow node has no current attempt to retry")
    if not is_operator_retryable(flow, flow_node, current_attempt):
        raise ConflictError("Flow node is not at an explicit retry boundary")

    if current_attempt is not None:
        expire_pending_approvals(
            flow,
            node_attempt_id=current_attempt.id,
            reason="superseded-by-operator-retry",
        )
        supersede_projected_manifests(flow, node_attempt_id=current_attempt.id)
        abort_attempt(current_attempt)

    end_node_session(flow_node.node_session)

    node_attempt = await _create_blocked_node_attempt(
        session,
        flow=flow,
        flow_node=flow_node,
        previous_attempt=current_attempt,
    )
    await _bootstrap_node_attempt_context(
        session,
        flow=flow,
        flow_node=flow_node,
        node_attempt=node_attempt,
    )
    return flow, node_attempt


async def cancel_flow(session: AsyncSession, flow_id: UUID) -> Flow:
    await lock_flow(session, flow_id)
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")
    if flow.status == FlowStatus.CANCELLED:
        return flow
    if flow.status in {FlowStatus.FAILED, FlowStatus.SUCCEEDED}:
        raise ConflictError(f"Flow is already terminal: {flow.status.value}")

    for node in open_nodes(flow):
        current_attempt = latest_attempt(node)
        if current_attempt is not None:
            cancel_attempt(current_attempt)
        end_node_session(node.node_session)

    expire_pending_approvals(flow, reason="cancelled-flow")
    supersede_projected_manifests(flow)
    pause_open_nodes(flow)
    set_flow_status(flow, FlowStatus.CANCELLED)
    await session.flush()
    return flow


__all__ = [
    "advance_flow_until_boundary",
    "cancel_flow",
    "continue_flow",
    "get_flow_with_relations",
    "pause_flow",
    "retry_flow_node",
    "start_flow_from_workflow",
]
