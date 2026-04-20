from __future__ import annotations

import hashlib
import json
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    ContextItemKind,
    ContextItemScope,
    ContextItemStatus,
    FlowNodeState,
    FlowRevisionStatus,
    FlowStatus,
    NodeAttemptStatus,
    NodeSessionStatus,
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
    TaskCompose,
)
from app.runtime.control import (
    abort_attempt,
    cancel_attempt,
    end_node_session,
    expire_pending_approvals,
    flow_boundary_snapshot,
    idle_node_session,
    is_operator_retryable,
    latest_attempt,
    lock_flow,
    refresh_flow_status,
    supersede_projected_manifests,
)
from app.runtime.dispatcher import ensure_node_session, project_context_manifest
from app.runtime.packaging import (
    ensure_task_compose_for_compiled_plan,
    ensure_task_compose_for_task,
)
from app.runtime.read_models import get_flow_with_relations as load_flow_with_relations
from app.runtime.resources import ensure_task_resources_for_compiled_plan
from app.runtime.scheduler import (
    open_nodes,
    pause_open_nodes,
    release_next_unstarted_node,
    restore_paused_nodes,
)
from app.runtime.state import (
    mark_node_attempt_blocked,
    set_flow_status,
    utcnow_naive,
)
from app.schemas.runtime import FlowStartFromWorkflowCreate, TaskComposeStartCreate, TaskCreate
from app.services.compiler_service import compile_published_workflow
from app.services.task_service import bootstrap_task_runtime_state, create_task

MAX_LOCAL_ADVANCE_STEPS = 64


def _hash_json(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _build_node_path(compiled_node_key: str, parent: FlowNode | None) -> str:
    segment = compiled_node_key.rsplit(".", 1)[-1]
    return segment if parent is None else f"{parent.node_path}.{segment}"


def _task_defaults_from_compose_roots(
    payload: TaskComposeStartCreate,
) -> dict[str, dict[str, object]]:
    task_defaults: dict[str, dict[str, object]] = {}
    if payload.roots.workspace:
        task_defaults["workspace"] = {"mode": "ensure_task_primary"}
    if payload.roots.context:
        task_defaults["context"] = {
            "mode": "seed_from",
            "seed_from": ["workspace"] if payload.roots.workspace else [],
        }
    if payload.roots.manifests:
        task_defaults["manifests"] = {"mode": "ensure_task_root"}
    return task_defaults


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
    return await load_flow_with_relations(session, flow_id)


def _continue_conflict_for_boundary(flow: Flow) -> ConflictError:
    return flow_boundary_snapshot(flow).conflict_error()


def _advance_boundary_reason(flow: Flow) -> str | None:
    return flow_boundary_snapshot(flow).boundary_reason()


async def _advance_flow_once(session: AsyncSession, flow: Flow) -> tuple[Flow, bool]:
    if flow_boundary_snapshot(flow).boundary_reason() is not None:
        refresh_flow_status(flow)
        await session.flush()
        return flow, False

    ready_node = release_next_unstarted_node(flow)
    if ready_node is None:
        refresh_flow_status(flow)
        await session.flush()
        return flow, False

    supersede_projected_manifests(flow)

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
            if (
                boundary_reason not in {"running", "projected-manifests"}
                and not progressed_any
                and raise_on_conflict
            ):
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
    flow = await advance_flow_until_boundary(
        session,
        flow_id,
        cause="operator-continue",
        resume_paused=True,
        raise_on_conflict=True,
    )
    try:
        from app.services.openclaw_bridge import (
            prepare_flow_dispatch_to_openclaw,
            spawn_detached_openclaw_dispatch,
        )

        prepared_dispatch = await prepare_flow_dispatch_to_openclaw(session, flow_id=flow_id)
    except ConflictError:
        return flow
    spawn_detached_openclaw_dispatch(prepared_dispatch)
    refreshed = await get_flow_with_relations(session, flow_id)
    return refreshed or flow


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
    "pause_flow",
    "retry_flow_node",
    "start_flow_from_workflow",
]


async def start_flow_from_task_compose(
    session: AsyncSession,
    *,
    payload: TaskComposeStartCreate,
) -> tuple[Flow, FlowRevision, list[FlowNode]]:
    if payload.workflow.entrypoint is not None:
        raise InvalidDefinitionError("workflow.entrypoint is not supported yet")
    workflow_key = payload.workflow.key
    task_payload = TaskCreate(
        title=payload.metadata.title,
        description=payload.metadata.description,
        input_payload=payload.input,
        key=payload.metadata.key,
    )
    flow, revision, flow_nodes = await start_flow_from_workflow(
        session,
        workflow_key=workflow_key,
        payload=FlowStartFromWorkflowCreate(task=task_payload),
    )
    task_defaults = _task_defaults_from_compose_roots(payload)
    if task_defaults:
        await bootstrap_task_runtime_state(
            session,
            task=flow.task,
            task_defaults=task_defaults,
        )
    existing_task_compose = await session.scalar(
        select(TaskCompose).where(TaskCompose.task_id == flow.task_id)
    )
    materialized_paths = {}
    if existing_task_compose is not None:
        materialized_paths = existing_task_compose.metadata_.get("materialized_paths", {})
    await ensure_task_compose_for_task(
        session,
        task=flow.task,
        metadata={
            "key": payload.metadata.key,
            "title": payload.metadata.title,
            "description": payload.metadata.description,
            "labels": payload.metadata.labels,
            "materialized_paths": materialized_paths,
        },
        task_defaults=task_defaults,
        context_refs_override=payload.context_refs,
        skill_dependencies=[item.model_dump(mode="json") for item in payload.skill_dependencies],
    )
    return flow, revision, flow_nodes
