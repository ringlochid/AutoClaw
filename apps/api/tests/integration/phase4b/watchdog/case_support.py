from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from app.db import DispatchDeliveryStateModel, DispatchWatchdogStateModel, FlowModel
from app.runtime import PromptSendMode
from app.runtime.watchdog import stop_runtime_watchdog
from sqlalchemy import select
from tests.integration.phase2.bootstrap.fixtures import (
    persist_bootstrap_runtime,
    seed_dispatch,
)
from tests.integration.phase3.runtime_support import phase3_runtime_api, prepare_runtime_db
from tests.integration.phase4b.watchdog.support import Phase4BWatchdogContext


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
            "AUTOCLAW_RUNTIME__WATCHDOG_BOOTSTRAP_ACK_TIMEOUT_SECONDS",
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


def reset_watchdog_row(row: DispatchWatchdogStateModel) -> None:
    row.watchdog_state = "clear"
    row.current_watchdog_kind = None
    row.current_watchdog_reason = None
    row.recovery_action = None
    row.recovery_reason = None
    row.recovery_dispatch_id = None


@asynccontextmanager
async def manual_watchdog_context(
    tmp_path: Path,
    *,
    task_id: str,
) -> AsyncIterator[Phase4BWatchdogContext]:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"

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
            delivery_state.controller_observation_state = "live"
            delivery_state.updated_at = dispatch.rendered_at
            await session.commit()
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
