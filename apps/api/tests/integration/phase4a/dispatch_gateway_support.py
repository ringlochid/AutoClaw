from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from autoclaw.config import get_settings
from autoclaw.db import (
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
    NodeSessionModel,
    ProviderEventRecordModel,
)
from autoclaw.runtime.effects import drive_runtime_once
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload


@dataclass(frozen=True)
class DispatchGatewaySnapshot:
    flow: FlowModel
    dispatch: DispatchTurnModel
    delivery_state: DispatchDeliveryStateModel | None
    continuity_state: DispatchContinuityStateModel | None
    node_session: NodeSessionModel | None
    provider_events: list[ProviderEventRecordModel]


@contextmanager
def override_gateway_base_url(base_url: str) -> Iterator[None]:
    previous = os.environ.get("AUTOCLAW_OPENCLAW__BASE_URL")
    try:
        os.environ["AUTOCLAW_OPENCLAW__BASE_URL"] = base_url
        get_settings.cache_clear()
        yield
    finally:
        if previous is None:
            os.environ.pop("AUTOCLAW_OPENCLAW__BASE_URL", None)
        else:
            os.environ["AUTOCLAW_OPENCLAW__BASE_URL"] = previous
        get_settings.cache_clear()


async def load_latest_dispatch_snapshot(
    session: AsyncSession,
    *,
    task_id: str,
) -> DispatchGatewaySnapshot:
    latest_dispatch_id = (
        select(DispatchTurnModel.dispatch_id)
        .where(DispatchTurnModel.task_id == task_id)
        .order_by(DispatchTurnModel.rendered_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    dispatch = (
        (
            await session.execute(
                select(DispatchTurnModel)
                .where(DispatchTurnModel.dispatch_id == latest_dispatch_id)
                .options(
                    joinedload(DispatchTurnModel.flow),
                    joinedload(DispatchTurnModel.delivery_state),
                    joinedload(DispatchTurnModel.continuity_state),
                    joinedload(DispatchTurnModel.node_sessions),
                    joinedload(DispatchTurnModel.provider_events),
                )
            )
        )
        .unique()
        .scalar_one_or_none()
    )
    assert dispatch is not None
    snapshot = _build_dispatch_snapshot(dispatch)
    session.expunge_all()
    return snapshot


async def wait_for_latest_dispatch_snapshot(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    predicate: Callable[[DispatchGatewaySnapshot], bool],
    timeout_seconds: float = 2.0,
    poll_interval_seconds: float = 0.05,
    drive_runtime: bool = False,
) -> DispatchGatewaySnapshot:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        async with session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
        if predicate(snapshot):
            return snapshot
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError(f"timed out waiting for dispatch snapshot for task '{task_id}'")
        if drive_runtime:
            await drive_runtime_once(task_id=task_id)
        await asyncio.sleep(poll_interval_seconds)


def _build_dispatch_snapshot(
    dispatch: DispatchTurnModel,
) -> DispatchGatewaySnapshot:
    flow = dispatch.flow
    assert flow is not None
    node_session = next(
        (
            row
            for row in dispatch.node_sessions
            if row.node_session_id == f"node-session.{dispatch.dispatch_id}"
        ),
        None,
    )
    return DispatchGatewaySnapshot(
        flow=flow,
        dispatch=dispatch,
        delivery_state=dispatch.delivery_state,
        continuity_state=dispatch.continuity_state,
        node_session=node_session,
        provider_events=list(dispatch.provider_events),
    )


__all__ = [
    "DispatchGatewaySnapshot",
    "load_latest_dispatch_snapshot",
    "override_gateway_base_url",
    "wait_for_latest_dispatch_snapshot",
]
