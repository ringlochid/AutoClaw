from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.db import (
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
)
from app.runtime.watchdog.service import reconcile_watchdog_truth
from tests.integration.phase3.dispatch_support import current_open_dispatch_id
from tests.integration.phase4b.watchdog.case_support import (
    configure_watchdog_env,
    manual_watchdog_context,
    reset_watchdog_row,
)
from tests.integration.phase4b.watchdog.support import load_watchdog_state


@pytest.mark.asyncio
async def test_phase4b_watchdog_classifies_execution_stale_when_only_provider_signals_move(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_watchdog_env(
        monkeypatch,
        bootstrap_timeout_seconds=300,
        execution_stale_after_seconds=1,
        auto_recover=False,
    )

    async with manual_watchdog_context(
        tmp_path,
        task_id="task_phase4b_execution_stale_provider_signal_only",
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        stale_at = datetime.now(tz=UTC) - timedelta(seconds=5)
        provider_signal_at = datetime.now(tz=UTC)

        async with context.api.session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            assert dispatch is not None
            assert delivery_state is not None
            assert watchdog_state is not None
            dispatch.control_state = "live"
            dispatch.accepted_boundary = None
            delivery_state.accepted_at = stale_at
            delivery_state.last_controller_progress_at = stale_at
            delivery_state.last_provider_signal_at = provider_signal_at
            delivery_state.updated_at = provider_signal_at
            reset_watchdog_row(watchdog_state)
            await session.commit()

        changed = await reconcile_watchdog_truth(context.api.session_factory)
        assert changed is True
        watchdog_state = await load_watchdog_state(context, dispatch_id=dispatch_id)
        assert watchdog_state.watchdog_state == "classified"
        assert watchdog_state.current_watchdog_kind == "execution_running.execution_stale"
        assert watchdog_state.recovery_action == "redispatch_same_attempt"
        assert watchdog_state.recovery_dispatch_id is None
