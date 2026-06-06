from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import DispatchWatchdogStateModel
from autoclaw.runtime.post_commit import drive_runtime_once
from autoclaw.runtime.watchdog import drive_watchdog_once, drive_watchdog_until
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import (
    RuntimeApiContext,
    bootstrap_parent_runtime,
    prepare_runtime_db,
    runtime_api_context,
    set_dispatch_drain_timeout,
)


@dataclass(frozen=True)
class Phase4BWatchdogContext:
    api: RuntimeApiContext
    task_id: str
    task_root: Path


@asynccontextmanager
async def phase4b_watchdog_api(
    tmp_path: Path,
    *,
    task_id: str,
    compiler_version: str,
    openclaw_gateway_test_server: LocalGatewayTestServer,
    dispatch_drain_timeout_seconds: int | None = None,
) -> AsyncIterator[Phase4BWatchdogContext]:
    config_path = await prepare_runtime_db(tmp_path)
    if dispatch_drain_timeout_seconds is not None:
        set_dispatch_drain_timeout(
            config_path,
            timeout_seconds=dispatch_drain_timeout_seconds,
        )
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
        async with runtime_api_context(config_path) as api:
            yield Phase4BWatchdogContext(
                api=api,
                task_id=task_id,
                task_root=task_root,
            )


async def wait_for_watchdog_cycle(*, task_id: str) -> None:
    await drive_watchdog_once()
    await drive_runtime_once(task_id=task_id)


async def wait_for_watchdog_condition(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
    predicate: Callable[[DispatchWatchdogStateModel], bool],
    max_cycles: int = 6,
) -> DispatchWatchdogStateModel:
    latest: DispatchWatchdogStateModel | None = None

    async def watchdog_condition_ready() -> bool:
        nonlocal latest
        await drive_runtime_once(task_id=context.task_id)
        latest = await load_watchdog_state(context, dispatch_id=dispatch_id)
        return predicate(latest)

    await drive_watchdog_until(
        watchdog_condition_ready,
        max_cycles=max_cycles,
    )
    await drive_runtime_once(task_id=context.task_id)
    latest = await load_watchdog_state(context, dispatch_id=dispatch_id)
    assert latest is not None
    return latest


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
