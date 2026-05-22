from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db import DispatchTurnModel, FlowModel
from app.runtime.control.dispatch.control import fence_foreground_dispatch
from app.runtime.effects.dispatch_progression import auto_open_next_running_dispatch
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers.runtime_auth import OPERATOR_HEADERS
from tests.integration.phase2.bootstrap.support import (
    Phase2RuntimeContext,
    phase2_runtime_context,
)

JsonMap = dict[str, Any]
ArtifactClaims = list[dict[str, str]]

def _set_dispatch_drain_timeout(config_path: Path, *, timeout_seconds: int) -> None:
    config_text = config_path.read_text(encoding="utf-8")
    lines = config_text.splitlines()
    runtime_index = next(
        (index for index, line in enumerate(lines) if line.strip() == "[runtime]"),
        None,
    )
    if runtime_index is None:
        lines.extend(["", "[runtime]", f"dispatch_drain_timeout_seconds = {timeout_seconds}"])
    else:
        inserted = False
        for index in range(runtime_index + 1, len(lines)):
            line = lines[index].strip()
            if not line:
                break
            if line.startswith("[") and line.endswith("]"):
                break
            if line.startswith("dispatch_drain_timeout_seconds"):
                lines[index] = f"dispatch_drain_timeout_seconds = {timeout_seconds}"
                inserted = True
                break
        if not inserted:
            lines.insert(runtime_index + 1, f"dispatch_drain_timeout_seconds = {timeout_seconds}")
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        _set_dispatch_drain_timeout(runtime.paths.config_path, timeout_seconds=30)
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
    async with driver.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == driver.task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        dispatch.delivery_status = "provider_completed"
        await fence_foreground_dispatch(
            session,
            task_id=driver.task_id,
            flow=flow,
            dispatch=dispatch,
        )
        await auto_open_next_running_dispatch(
            session,
            task_id=driver.task_id,
            flow=flow,
            previous_dispatch=dispatch,
        )
        await session.commit()


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
