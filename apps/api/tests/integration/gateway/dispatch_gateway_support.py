from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from autoclaw.config import get_settings
from autoclaw.persistence import (
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
    NodeSessionModel,
    ProviderEventRecordModel,
)
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
    overrides = {
        "AUTOCLAW_OPENCLAW__BASE_URL": base_url,
        "AUTOCLAW_OPENCLAW__GATEWAY_TOKEN": "gateway-config-token",
        "AUTOCLAW_OPENCLAW__AGENT_ID": "autoclaw-worker",
        "AUTOCLAW_OPENCLAW__BINARY_PATH": os.environ.get(
            "AUTOCLAW_OPENCLAW__BINARY_PATH",
            sys.executable,
        ),
    }
    previous: dict[str, str | None] = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            os.environ[key] = value
        get_settings.cache_clear()
        yield
    finally:
        for key, previous_value in previous.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
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
    max_cycles: int = 40,
    poll_interval_seconds: float = 0.05,
) -> DispatchGatewaySnapshot:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + (max_cycles * poll_interval_seconds)
    while True:
        async with session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
        if predicate(snapshot):
            return snapshot
        if loop.time() >= deadline:
            raise AssertionError(
                f"dispatch snapshot for task '{task_id}' did not satisfy the predicate"
            )
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
