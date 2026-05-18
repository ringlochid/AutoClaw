from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db import DispatchTurnModel, FlowModel
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.integration.phase2.bootstrap.support import (
    Phase2RuntimeContext,
    phase2_runtime_context,
)
from tests.integration.phase3.dispatch_support import (
    current_open_dispatch_id,
    mark_dispatch_provider_completed,
)

JsonMap = dict[str, Any]
ArtifactClaims = list[dict[str, str]]

OPERATOR_HEADERS = {"X-AutoClaw-API-Key": "api-test-key"}


@dataclass(frozen=True)
class ParentFirstLaneDriver:
    client: AsyncClient
    session_factory: async_sessionmaker[AsyncSession]
    task_id: str


@asynccontextmanager
async def parent_first_lane_runtime_context(
    tmp_path: Path,
) -> AsyncIterator[Phase2RuntimeContext]:
    async with phase2_runtime_context(
        tmp_path,
        quiet_init=True,
        init_log_level="WARNING",
    ) as runtime:
        yield runtime


def write_lane_artifact(task_root: Path, relative_path: str, content: str) -> Path:
    path = task_root / "workspace" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def json_map(response: Response) -> JsonMap:
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


async def current_session_key(driver: ParentFirstLaneDriver) -> str:
    async with driver.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == driver.task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        assert isinstance(dispatch.gateway_session_key, str)
        return dispatch.gateway_session_key


async def prove_open_dispatch_inactive(driver: ParentFirstLaneDriver) -> None:
    dispatch_id = await current_open_dispatch_id(
        driver.session_factory,
        task_id=driver.task_id,
    )
    await mark_dispatch_provider_completed(
        driver.session_factory,
        dispatch_id=dispatch_id,
    )


__all__ = [
    "OPERATOR_HEADERS",
    "ArtifactClaims",
    "JsonMap",
    "ParentFirstLaneDriver",
    "current_session_key",
    "json_map",
    "parent_first_lane_runtime_context",
    "prove_open_dispatch_inactive",
    "write_lane_artifact",
]
