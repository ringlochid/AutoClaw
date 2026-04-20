from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import FlowStatus, NodeAttemptStatus, NodeSessionStatus
from app.db.models.runtime import Flow
from app.runtime.read_models import get_flow_with_relations
from app.runtime.scheduler import ordered_nodes
from app.runtime.state import utcnow_naive


async def list_watchdog_candidate_flow_ids(
    session: AsyncSession,
    *,
    stale_after_seconds: int,
    limit: int,
) -> list[UUID]:
    threshold = utcnow_naive() - timedelta(seconds=stale_after_seconds)
    flow_ids = list(
        (
            await session.scalars(
                select(Flow.id)
                .where(Flow.status.in_([FlowStatus.RUNNING, FlowStatus.BLOCKED]))
                .order_by(Flow.created_at.asc())
                .limit(limit)
            )
        ).all()
    )

    candidates: list[UUID] = []
    for flow_id in flow_ids:
        flow = await get_flow_with_relations(session, flow_id)
        if flow is None or flow.active_flow_revision is None:
            continue
        for flow_node in ordered_nodes(flow):
            latest_node_attempt = flow_node.attempts[-1] if flow_node.attempts else None
            if (
                latest_node_attempt is None
                or latest_node_attempt.status != NodeAttemptStatus.RUNNING
            ):
                continue
            if (
                flow_node.node_session is not None
                and flow_node.node_session.status == NodeSessionStatus.ACTIVE
            ):
                continue
            visible_checkpoints = [
                checkpoint
                for checkpoint in latest_node_attempt.checkpoints
                if checkpoint.sequence_no > 0
            ]
            last_checkpoint_time = (
                visible_checkpoints[-1].created_at
                if visible_checkpoints
                else latest_node_attempt.started_at
            )
            if last_checkpoint_time < threshold:
                candidates.append(flow_id)
                break
            if (
                flow_node.node_session is not None
                and flow_node.node_session.node_attempt_id != latest_node_attempt.id
            ):
                candidates.append(flow_id)
                break
        if len(candidates) >= limit:
            break
    return candidates
