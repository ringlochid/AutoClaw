from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AttemptCheckpointModel,
    AttemptModel,
    DispatchTurnModel,
    FlowModel,
)


async def next_node_sequence_number(
    session: AsyncSession,
    model: type[AttemptModel] | type[DispatchTurnModel],
    task_id: str,
    node_key: str,
) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(model)
        .where(
            model.task_id == task_id,
            model.node_key == node_key,
        )
    )
    return int(count or 0) + 1


async def require_flow_for_task(session: AsyncSession, task_id: str) -> FlowModel:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    if flow is None:
        raise ValueError(f"unknown task_id '{task_id}'")
    return flow


async def latest_checkpoint_for_attempt(
    session: AsyncSession,
    attempt: AttemptModel,
) -> AttemptCheckpointModel | None:
    if attempt.latest_checkpoint_id is None:
        return None
    return await session.get(AttemptCheckpointModel, attempt.latest_checkpoint_id)


async def latest_resumable_dispatch_for_attempt(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
) -> DispatchTurnModel | None:
    dispatch = await session.scalar(
        select(DispatchTurnModel)
        .where(
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.attempt_id == attempt_id,
            DispatchTurnModel.accepted_boundary.is_(None),
            DispatchTurnModel.closed_at.is_not(None),
        )
        .order_by(DispatchTurnModel.rendered_at.desc())
    )
    return dispatch
