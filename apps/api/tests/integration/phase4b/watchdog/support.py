from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.db import DispatchWatchdogStateModel
from app.runtime.effects import wait_for_runtime_effects
from app.runtime.openclaw.fixtures import agent_wait_fixture
from app.runtime.watchdog import wait_for_runtime_watchdog
from tests.integration.phase3.runtime_support import (
    Phase3RuntimeApi,
    bootstrap_parent_runtime,
    phase3_runtime_api,
    prepare_runtime_db,
)
from tests.integration.phase4a.support import LocalGatewayTestServer


@dataclass(frozen=True)
class Phase4BWatchdogContext:
    api: Phase3RuntimeApi
    task_id: str
    task_root: Path


@asynccontextmanager
async def phase4b_watchdog_api(
    tmp_path: Path,
    *,
    task_id: str,
    compiler_version: str,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> AsyncIterator[Phase4BWatchdogContext]:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    with openclaw_gateway_test_server.configured_env():
        get_settings.cache_clear()
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version=compiler_version,
        )
        async with phase3_runtime_api(config_path) as api:
            yield Phase4BWatchdogContext(
                api=api,
                task_id=task_id,
                task_root=task_root,
            )


async def wait_for_watchdog_cycle(*, task_id: str) -> None:
    await wait_for_runtime_watchdog(max_wait_seconds=2.0)
    await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)


async def wait_for_watchdog_condition(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
    predicate: Callable[[DispatchWatchdogStateModel], bool],
    max_cycles: int = 6,
) -> DispatchWatchdogStateModel:
    latest: DispatchWatchdogStateModel | None = None
    for _ in range(max_cycles):
        await wait_for_watchdog_cycle(task_id=context.task_id)
        latest = await load_watchdog_state(context, dispatch_id=dispatch_id)
        if predicate(latest):
            return latest
    assert latest is not None
    raise AssertionError(
        f"watchdog condition did not pass for dispatch '{dispatch_id}' after {max_cycles} cycles"
    )


async def load_watchdog_state(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
) -> DispatchWatchdogStateModel:
    async with context.api.session_factory() as session:
        row = await session.get(DispatchWatchdogStateModel, dispatch_id)
        assert row is not None
        return row


__all__ = [
    "Phase4BWatchdogContext",
    "load_watchdog_state",
    "phase4b_watchdog_api",
    "wait_for_watchdog_condition",
    "wait_for_watchdog_cycle",
]
