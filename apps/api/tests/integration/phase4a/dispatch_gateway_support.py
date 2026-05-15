from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from app.config import get_settings
from app.db import (
    DispatchCallbackBindingModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
    NodeSessionModel,
    ProviderEventRecordModel,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class DispatchGatewaySnapshot:
    flow: FlowModel
    dispatch: DispatchTurnModel
    delivery_state: DispatchDeliveryStateModel | None
    continuity_state: DispatchContinuityStateModel | None
    binding: DispatchCallbackBindingModel | None
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
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    assert flow is not None
    dispatch = await session.scalar(
        select(DispatchTurnModel)
        .where(DispatchTurnModel.task_id == task_id)
        .order_by(DispatchTurnModel.rendered_at.desc())
    )
    assert dispatch is not None
    return await build_dispatch_snapshot(
        session,
        flow=flow,
        dispatch_id=dispatch.dispatch_id,
    )


async def build_dispatch_snapshot(
    session: AsyncSession,
    *,
    flow: FlowModel,
    dispatch_id: str,
) -> DispatchGatewaySnapshot:
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch_id)
    binding = await session.get(
        DispatchCallbackBindingModel,
        f"dispatch-callback-binding.{dispatch_id}",
    )
    node_session = await session.get(NodeSessionModel, f"node-session.{dispatch_id}")
    provider_events = list(
        await session.scalars(
            select(ProviderEventRecordModel)
            .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
            .order_by(ProviderEventRecordModel.event_no.asc())
        )
    )
    dispatch = await session.get(DispatchTurnModel, dispatch_id)
    assert dispatch is not None
    return DispatchGatewaySnapshot(
        flow=flow,
        dispatch=dispatch,
        delivery_state=delivery_state,
        continuity_state=continuity_state,
        binding=binding,
        node_session=node_session,
        provider_events=provider_events,
    )


__all__ = [
    "DispatchGatewaySnapshot",
    "build_dispatch_snapshot",
    "load_latest_dispatch_snapshot",
    "override_gateway_base_url",
]
