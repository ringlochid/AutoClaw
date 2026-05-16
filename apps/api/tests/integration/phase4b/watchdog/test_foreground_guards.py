from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.db import (
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
)
from app.runtime.watchdog.service import reconcile_watchdog_truth
from sqlalchemy import select
from tests.integration.phase3.dispatch_support import current_open_dispatch_id
from tests.integration.phase4b.watchdog.case_support import (
    configure_watchdog_env,
    manual_watchdog_context,
    reset_watchdog_row,
)
from tests.integration.phase4b.watchdog.support import (
    load_watchdog_state,
)


@pytest.mark.asyncio
async def test_phase4b_watchdog_skips_fenced_yield_handoff_without_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_watchdog_env(monkeypatch)

    async with manual_watchdog_context(
        tmp_path,
        task_id="task_phase4b_skip_fenced_yield_handoff",
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        terminal_at = datetime.now(tz=UTC) - timedelta(seconds=3)

        async with context.api.session_factory() as session:
            flow = await session.scalar(
                select(FlowModel).where(FlowModel.task_id == context.task_id)
            )
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            assert flow is not None
            assert dispatch is not None
            assert delivery_state is not None
            assert watchdog_state is not None
            flow.current_open_dispatch_id = None
            dispatch.accepted_boundary = "yield"
            dispatch.closed_by_boundary = "yield"
            dispatch.status = "closed"
            dispatch.control_state = "fenced"
            dispatch.control_state_reason = "boundary:yield:inactive_proven"
            dispatch.fenced_at = terminal_at
            dispatch.closed_at = terminal_at
            dispatch.delivery_status = "provider_completed"
            delivery_state.transport_state = "provider_completed"
            delivery_state.controller_observation_state = "fenced"
            delivery_state.last_provider_signal_at = terminal_at
            delivery_state.last_controller_terminal_at = terminal_at
            delivery_state.updated_at = terminal_at
            reset_watchdog_row(watchdog_state)
            await session.commit()

        changed = await reconcile_watchdog_truth(context.api.session_factory)
        assert changed is False
        watchdog_state = await load_watchdog_state(context, dispatch_id=dispatch_id)
        assert watchdog_state.watchdog_state == "clear"
        assert watchdog_state.current_watchdog_kind is None
        assert watchdog_state.recovery_action is None
        assert watchdog_state.recovery_dispatch_id is None

        async with context.api.session_factory() as session:
            flow = await session.scalar(
                select(FlowModel).where(FlowModel.task_id == context.task_id)
            )
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert flow is not None
            assert dispatch is not None
            assert flow.current_open_dispatch_id is None
            assert dispatch.superseded_by_dispatch_id is None


@pytest.mark.asyncio
async def test_phase4b_watchdog_skips_paused_fenced_dispatch_without_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_watchdog_env(monkeypatch)

    async with manual_watchdog_context(
        tmp_path,
        task_id="task_phase4b_skip_paused_fenced_dispatch",
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        terminal_at = datetime.now(tz=UTC) - timedelta(seconds=3)

        async with context.api.session_factory() as session:
            flow = await session.scalar(
                select(FlowModel).where(FlowModel.task_id == context.task_id)
            )
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            assert flow is not None
            assert dispatch is not None
            assert delivery_state is not None
            assert watchdog_state is not None
            flow.status = "paused"
            flow.current_open_dispatch_id = None
            dispatch.status = "closed"
            dispatch.control_state = "fenced"
            dispatch.control_state_reason = "pause_requested:inactive_proven"
            dispatch.fenced_at = terminal_at
            dispatch.closed_at = terminal_at
            dispatch.delivery_status = "provider_completed"
            delivery_state.transport_state = "provider_completed"
            delivery_state.controller_observation_state = "fenced"
            delivery_state.last_provider_signal_at = terminal_at
            delivery_state.last_controller_terminal_at = terminal_at
            delivery_state.updated_at = terminal_at
            reset_watchdog_row(watchdog_state)
            await session.commit()

        changed = await reconcile_watchdog_truth(context.api.session_factory)
        assert changed is False
        watchdog_state = await load_watchdog_state(context, dispatch_id=dispatch_id)
        assert watchdog_state.watchdog_state == "clear"
        assert watchdog_state.current_watchdog_kind is None
        assert watchdog_state.recovery_action is None
        assert watchdog_state.recovery_dispatch_id is None

        async with context.api.session_factory() as session:
            flow = await session.scalar(
                select(FlowModel).where(FlowModel.task_id == context.task_id)
            )
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert flow is not None
            assert dispatch is not None
            assert flow.status == "paused"
            assert flow.current_open_dispatch_id is None
            assert dispatch.superseded_by_dispatch_id is None


@pytest.mark.asyncio
async def test_phase4b_watchdog_escalates_ambiguous_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_watchdog_env(monkeypatch)

    async with manual_watchdog_context(
        tmp_path,
        task_id="task_phase4b_ambiguous_escalation",
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )

        async with context.api.session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            assert dispatch is not None
            assert delivery_state is not None
            dispatch.control_state = "ambiguous"
            dispatch.control_state_reason = "foreground_dispatch:timed_out"
            dispatch.delivery_status = "transport_ambiguous"
            delivery_state.transport_state = "transport_ambiguous"
            delivery_state.controller_observation_state = "ambiguous"
            await session.commit()

        changed = await reconcile_watchdog_truth(context.api.session_factory)
        assert changed is True
        watchdog_state = await load_watchdog_state(context, dispatch_id=dispatch_id)
        assert watchdog_state.watchdog_state == "classified"
        assert watchdog_state.current_watchdog_kind == "execution_running.delivery_path_rebound"
        assert watchdog_state.recovery_action == "escalate"
        assert watchdog_state.recovery_dispatch_id is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control_state", "accepted_boundary", "transport_state", "observation_state"),
    (
        ("launching", None, "prepared", "launching"),
        ("abort_requested", None, "accepted", "abort_requested"),
        ("live", "yield", "accepted", "live"),
    ),
)
async def test_phase4b_watchdog_skips_foreground_owned_dispatch_slots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    control_state: str,
    accepted_boundary: str | None,
    transport_state: str,
    observation_state: str,
) -> None:
    configure_watchdog_env(
        monkeypatch,
        bootstrap_timeout_seconds=1,
        execution_stale_after_seconds=1,
    )

    async with manual_watchdog_context(
        tmp_path,
        task_id=f"task_phase4b_skip_{control_state}_{accepted_boundary or 'none'}",
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        stale_at = datetime.now(tz=UTC) - timedelta(seconds=5)

        async with context.api.session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            assert dispatch is not None
            assert delivery_state is not None
            assert watchdog_state is not None
            dispatch.control_state = control_state
            dispatch.accepted_boundary = accepted_boundary
            if control_state == "abort_requested":
                dispatch.abort_requested_at = stale_at
                dispatch.control_deadline_at = datetime.now(tz=UTC) + timedelta(minutes=1)
            delivery_state.accepted_at = stale_at
            delivery_state.transport_state = transport_state
            delivery_state.controller_observation_state = observation_state
            delivery_state.updated_at = stale_at
            reset_watchdog_row(watchdog_state)
            await session.commit()

        changed = await reconcile_watchdog_truth(context.api.session_factory)
        assert changed is False
        watchdog_state = await load_watchdog_state(context, dispatch_id=dispatch_id)
        assert watchdog_state.watchdog_state == "clear"
        assert watchdog_state.current_watchdog_kind is None
        assert watchdog_state.recovery_action is None
        assert watchdog_state.recovery_dispatch_id is None
