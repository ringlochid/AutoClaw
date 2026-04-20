from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

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


@dataclass(slots=True)
class FlowAuditSnapshot:
    flow: Flow
    attempts: list[NodeAttempt]
    checkpoints: list[NodeCheckpoint]
    sessions: list[NodeSession]
    context_items: list[ContextItem]


def _flow_task_binding_options() -> list[Any]:
    return [
        selectinload(Flow.task)
        .selectinload(Task.resource_bindings)
        .selectinload(TaskResourceBinding.workspace_root),
        selectinload(Flow.task)
        .selectinload(Task.resource_bindings)
        .selectinload(TaskResourceBinding.context_space),
        selectinload(Flow.task)
        .selectinload(Task.resource_bindings)
        .selectinload(TaskResourceBinding.manifest_root),
    ]


def _flow_summary_options() -> list[Any]:
    return [
        *_flow_task_binding_options(),
        selectinload(Flow.approvals),
        selectinload(Flow.context_manifests).selectinload(ContextManifest.node_session),
        selectinload(Flow.node_plan_revisions),
        selectinload(Flow.active_flow_revision)
        .selectinload(FlowRevision.compiled_plan)
        .selectinload(CompiledPlan.nodes),
        selectinload(Flow.active_flow_revision)
        .selectinload(FlowRevision.compiled_plan)
        .selectinload(CompiledPlan.edges),
        selectinload(Flow.active_flow_revision)
        .selectinload(FlowRevision.nodes)
        .selectinload(FlowNode.attempts)
        .selectinload(NodeAttempt.checkpoints),
        selectinload(Flow.active_flow_revision)
        .selectinload(FlowRevision.nodes)
        .selectinload(FlowNode.source_compiled_plan_node),
    ]


def _flow_audit_options() -> list[Any]:
    return [
        *_flow_task_binding_options(),
        selectinload(Flow.approvals),
        selectinload(Flow.context_manifests).selectinload(ContextManifest.node_session),
        selectinload(Flow.node_plan_revisions),
        selectinload(Flow.flow_revisions).selectinload(FlowRevision.compiled_plan),
        selectinload(Flow.flow_revisions)
        .selectinload(FlowRevision.nodes)
        .selectinload(FlowNode.attempts)
        .selectinload(NodeAttempt.checkpoints),
        selectinload(Flow.flow_revisions)
        .selectinload(FlowRevision.nodes)
        .selectinload(FlowNode.node_session),
        selectinload(Flow.flow_revisions)
        .selectinload(FlowRevision.nodes)
        .selectinload(FlowNode.source_compiled_plan_node),
        selectinload(Flow.active_flow_revision)
        .selectinload(FlowRevision.nodes)
        .selectinload(FlowNode.attempts)
        .selectinload(NodeAttempt.context_manifests)
        .selectinload(ContextManifest.node_session),
        selectinload(Flow.active_flow_revision)
        .selectinload(FlowRevision.nodes)
        .selectinload(FlowNode.node_session),
        selectinload(Flow.active_flow_revision)
        .selectinload(FlowRevision.nodes)
        .selectinload(FlowNode.source_compiled_plan_node),
        selectinload(Flow.active_flow_revision)
        .selectinload(FlowRevision.edges)
        .selectinload(FlowEdge.from_flow_node),
        selectinload(Flow.active_flow_revision)
        .selectinload(FlowRevision.edges)
        .selectinload(FlowEdge.to_flow_node),
    ]


async def list_flows(session: AsyncSession) -> list[Flow]:
    result = await session.scalars(
        select(Flow)
        .execution_options(populate_existing=True)
        .options(*_flow_summary_options())
        .order_by(Flow.created_at.desc())
    )
    return list(result.all())


async def get_flow_audit_snapshot(session: AsyncSession, flow_id: UUID) -> FlowAuditSnapshot | None:
    flow = cast(
        Flow | None,
        await session.scalar(
            select(Flow)
            .execution_options(populate_existing=True)
            .options(*_flow_audit_options())
            .where(Flow.id == flow_id)
        ),
    )
    if flow is None:
        return None

    attempts = list(
        (
            await session.scalars(
                select(NodeAttempt)
                .options(selectinload(NodeAttempt.flow_node))
                .where(NodeAttempt.flow_id == flow_id)
                .order_by(NodeAttempt.created_at.asc(), NodeAttempt.number.asc())
            )
        ).all()
    )
    checkpoints = list(
        (
            await session.scalars(
                select(NodeCheckpoint)
                .where(NodeCheckpoint.flow_id == flow_id)
                .order_by(NodeCheckpoint.created_at.asc(), NodeCheckpoint.sequence_no.asc())
            )
        ).all()
    )
    sessions = list(
        (
            await session.scalars(
                select(NodeSession)
                .where(NodeSession.flow_id == flow_id)
                .order_by(NodeSession.created_at.asc())
            )
        ).all()
    )
    context_items = list(
        (
            await session.scalars(
                select(ContextItem)
                .where(ContextItem.task_id == flow.task_id)
                .where(or_(ContextItem.flow_id.is_(None), ContextItem.flow_id == flow.id))
                .order_by(ContextItem.created_at.asc())
            )
        ).all()
    )

    return FlowAuditSnapshot(
        flow=flow,
        attempts=attempts,
        checkpoints=checkpoints,
        sessions=sessions,
        context_items=context_items,
    )


async def get_flow_with_relations(session: AsyncSession, flow_id: UUID) -> Flow | None:
    flow = cast(
        Flow | None,
        await session.scalar(
            select(Flow)
            .execution_options(populate_existing=True)
            .options(
                *_flow_task_binding_options(),
                selectinload(Flow.approvals),
                selectinload(Flow.context_manifests).selectinload(ContextManifest.node_session),
                selectinload(Flow.flow_revisions),
                selectinload(Flow.active_flow_revision),
            )
            .where(Flow.id == flow_id)
        ),
    )
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
        set_committed_value(node, "source_compiled_plan_node", compiled_plan_node)
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
