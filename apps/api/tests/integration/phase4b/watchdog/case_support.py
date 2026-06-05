from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

import pytest
from autoclaw.config import get_settings
from autoclaw.interfaces.cli.support import temporary_env
from autoclaw.persistence import DispatchDeliveryStateModel, DispatchWatchdogStateModel, FlowModel
from autoclaw.runtime import PromptSendMode
from autoclaw.runtime.post_commit import stop_runtime_effect_runner
from autoclaw.runtime.watchdog import stop_runtime_watchdog
from sqlalchemy import select
from tests.integration.phase2.bootstrap.fixtures import (
    persist_bootstrap_runtime,
    seed_dispatch,
)
from tests.integration.phase3.runtime_support import phase3_runtime_api, prepare_runtime_db
from tests.integration.phase4b.watchdog.support import Phase4BWatchdogContext

_PHASE4B_WATCHDOG_COMPOSE_GATEWAY_BASE_URL = "http://127.0.0.1:19055"
_PHASE4B_WATCHDOG_COMPOSE_GATEWAY_TOKEN = "gateway-config-token"


def configure_watchdog_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    interval_seconds: int = 1,
    bootstrap_timeout_seconds: int | None = None,
    execution_stale_after_seconds: int | None = None,
    same_attempt_redispatch_limit: int | None = None,
    auto_recover: bool | None = None,
) -> None:
    monkeypatch.setenv("AUTOCLAW_RUNTIME__WATCHDOG_INTERVAL_SECONDS", str(interval_seconds))
    if bootstrap_timeout_seconds is not None:
        monkeypatch.setenv(
            "AUTOCLAW_RUNTIME__WATCHDOG_BOOTSTRAP_FIRST_PROGRESS_TIMEOUT_SECONDS",
            str(bootstrap_timeout_seconds),
        )
    if execution_stale_after_seconds is not None:
        monkeypatch.setenv(
            "AUTOCLAW_RUNTIME__WATCHDOG_EXECUTION_STALE_AFTER_SECONDS",
            str(execution_stale_after_seconds),
        )
    if same_attempt_redispatch_limit is not None:
        monkeypatch.setenv(
            "AUTOCLAW_RUNTIME__WATCHDOG_SAME_ATTEMPT_REDISPATCH_LIMIT",
            str(same_attempt_redispatch_limit),
        )
    if auto_recover is not None:
        monkeypatch.setenv(
            "AUTOCLAW_RUNTIME__WATCHDOG_AUTO_RECOVER",
            "true" if auto_recover else "false",
        )
    get_settings.cache_clear()


def reset_watchdog_row(row: DispatchWatchdogStateModel) -> None:
    row.watchdog_state = "clear"
    row.current_watchdog_kind = None
    row.current_watchdog_reason = None
    row.recovery_action = None
    row.recovery_reason = None
    row.recovery_dispatch_id = None


@contextmanager
def _manual_watchdog_startup_gateway_env() -> Iterator[None]:
    base_url = os.environ.get("AUTOCLAW_OPENCLAW__BASE_URL")
    gateway_token = os.environ.get("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN")
    if (
        base_url != _PHASE4B_WATCHDOG_COMPOSE_GATEWAY_BASE_URL
        or gateway_token != _PHASE4B_WATCHDOG_COMPOSE_GATEWAY_TOKEN
    ):
        yield
        return
    with temporary_env(
        {
            "AUTOCLAW_OPENCLAW__GATEWAY_TOKEN": None,
            "AUTOCLAW_OPENCLAW__GATEWAY_PASSWORD": None,
        }
    ):
        yield


@asynccontextmanager
async def manual_watchdog_context(
    tmp_path: Path,
    *,
    task_id: str,
) -> AsyncIterator[Phase4BWatchdogContext]:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

    with _manual_watchdog_startup_gateway_env():
        async with phase3_runtime_api(config_path) as api:
            async with api.session_factory() as session:
                await persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-4b-watchdog-manual",
                )
                dispatch = await seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=f"dispatch.{task_id}.root.01",
                    send_mode=PromptSendMode.FULL_PROMPT,
                )
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
                assert flow is not None
                assert delivery_state is not None
                flow.status = "running"
                flow.current_open_dispatch_id = dispatch.dispatch_id
                delivery_state.accepted_at = dispatch.rendered_at
                delivery_state.updated_at = dispatch.rendered_at
                await session.commit()

            await stop_runtime_effect_runner()
            await stop_runtime_watchdog()

            yield Phase4BWatchdogContext(
                api=api,
                task_id=task_id,
                task_root=task_root,
            )


__all__ = [
    "configure_watchdog_env",
    "manual_watchdog_context",
    "reset_watchdog_row",
]
