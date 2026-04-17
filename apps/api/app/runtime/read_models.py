from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.runtime import (
    ContextItem,
    Flow,
    FlowEdge,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodeCheckpoint,
    NodeSession,
)


@dataclass(slots=True)
class FlowAuditSnapshot:
    flow: Flow
    attempts: list[NodeAttempt]
    checkpoints: list[NodeCheckpoint]
    sessions: list[NodeSession]
    context_items: list[ContextItem]


async def list_flows(session: AsyncSession) -> list[Flow]:
    result = await session.scalars(
        select(Flow)
        .execution_options(populate_existing=True)
        .options(
            selectinload(Flow.task),
            selectinload(Flow.approvals),
            selectinload(Flow.context_manifests),
            selectinload(Flow.node_plan_revisions),
            selectinload(Flow.active_flow_revision)
            .selectinload(FlowRevision.nodes)
            .selectinload(FlowNode.attempts)
            .selectinload(NodeAttempt.checkpoints),
            selectinload(Flow.active_flow_revision)
            .selectinload(FlowRevision.nodes)
            .selectinload(FlowNode.source_compiled_plan_node),
        )
        .order_by(Flow.created_at.desc())
    )
    return list(result.all())


async def get_flow_audit_snapshot(session: AsyncSession, flow_id: UUID) -> FlowAuditSnapshot | None:
    flow = cast(
        Flow | None,
        await session.scalar(
            select(Flow)
            .execution_options(populate_existing=True)
            .options(
                selectinload(Flow.task),
                selectinload(Flow.approvals),
                selectinload(Flow.context_manifests),
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
                .selectinload(NodeAttempt.context_manifests),
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
            )
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
