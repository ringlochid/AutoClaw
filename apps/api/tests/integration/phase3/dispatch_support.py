from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from autoclaw.db import FlowModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_wait_effects import (
    mark_dispatch_provider_completed,
    phase3_gateway_test_server_context,
)
from tests.integration.phase3.runtime_support import (
    Phase3RuntimeApi,
    assign_child,
    boundary,
    current_session_key,
    runtime_read_json,
)


async def current_open_dispatch_id(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> str:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        return flow.current_open_dispatch_id


def delivery_state_path(*, task_root: Path, dispatch_id: str) -> Path:
    return task_root / "_runtime" / "dispatch" / dispatch_id / "delivery-state.json"


def read_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


async def stage_child_yield(
    api: Phase3RuntimeApi,
    *,
    task_id: str,
    child_node_key: str,
) -> str:
    root_session_key = await current_session_key(
        session_factory=api.session_factory,
        task_id=task_id,
    )
    runtime_read = await runtime_read_json(api.client, task_id)
    assign = await assign_child(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        child_node_key=child_node_key,
        active_flow_revision_id=cast(str, runtime_read["active_flow_revision_id"]),
    )
    assert assign.status_code == 200
    yielded = await boundary(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        boundary_name="yield",
    )
    assert yielded.status_code == 200
    flow_payload = cast(dict[str, Any], yielded.json()["flow"])
    return cast(str, flow_payload["active_flow_revision_id"])


__all__ = [
    "current_open_dispatch_id",
    "delivery_state_path",
    "mark_dispatch_provider_completed",
    "phase3_gateway_test_server_context",
    "read_json",
    "stage_child_yield",
]
