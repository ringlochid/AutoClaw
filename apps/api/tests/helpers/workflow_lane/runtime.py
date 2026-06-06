from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import DispatchTurnModel, FlowModel
from autoclaw.runtime.post_commit import drive_runtime_once, wait_for_runtime_effects
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers.operator_auth_headers import OPERATOR_HEADERS
from tests.helpers.runtime_support import (
    RuntimeBootstrapContext,
    runtime_bootstrap_context,
    set_dispatch_drain_timeout,
)

JsonMap = dict[str, Any]
ArtifactClaims = list[dict[str, str]]


@dataclass(frozen=True)
class ParentFirstLaneDriver:
    client: AsyncClient
    session_factory: async_sessionmaker[AsyncSession]
    task_id: str
    gateway_server: Any | None = None


@asynccontextmanager
async def workflow_lane_runtime_context(
    tmp_path: Path,
    *,
    dispatch_drain_timeout_seconds: int | None = None,
) -> AsyncIterator[RuntimeBootstrapContext]:
    async with runtime_bootstrap_context(
        tmp_path,
        quiet_init=True,
        init_log_level="WARNING",
    ) as runtime:
        if dispatch_drain_timeout_seconds is not None:
            set_dispatch_drain_timeout(
                runtime.paths.config_path,
                timeout_seconds=dispatch_drain_timeout_seconds,
            )
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


async def wait_for_current_dispatch_progression(driver: ParentFirstLaneDriver) -> None:
    if driver.gateway_server is not None:
        driver.gateway_server.queue_method_payloads(
            "agent.wait",
            agent_wait_fixture(status="ok"),
        )
    await wait_for_runtime_effects(task_id=driver.task_id, max_wait_seconds=2.0)
    await drive_runtime_once(task_id=driver.task_id)


__all__ = [
    "OPERATOR_HEADERS",
    "ArtifactClaims",
    "JsonMap",
    "ParentFirstLaneDriver",
    "current_session_key",
    "json_map",
    "wait_for_current_dispatch_progression",
    "workflow_lane_runtime_context",
    "write_lane_artifact",
]
