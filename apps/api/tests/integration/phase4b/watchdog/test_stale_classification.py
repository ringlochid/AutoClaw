from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.db import (
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    ProviderEventRecordModel,
)
from app.runtime.watchdog.service import reconcile_watchdog_truth
from tests.integration.phase3.dispatch_support import current_open_dispatch_id
from tests.integration.phase4b.watchdog.case_support import (
    configure_watchdog_env,
    manual_watchdog_context,
    reset_watchdog_row,
)
from tests.integration.phase4b.watchdog.support import load_watchdog_state


def _terminal_provider_events(
    dispatch_id: str,
    *,
    task_id: str,
    attempt_id: str,
    terminal_at: datetime,
) -> list[ProviderEventRecordModel]:
    return [
        ProviderEventRecordModel(
            provider_event_record_id=f"provider-event.{dispatch_id}.1",
            dispatch_id=dispatch_id,
            task_id=task_id,
            attempt_id=attempt_id,
            event_no=1,
            event_source="provider",
            event_kind="accepted",
            provider_event_name="response.created",
            summary="Dispatch accepted.",
            detail=None,
            occurred_at=terminal_at - timedelta(seconds=2),
        ),
        ProviderEventRecordModel(
            provider_event_record_id=f"provider-event.{dispatch_id}.2",
            dispatch_id=dispatch_id,
            task_id=task_id,
            attempt_id=attempt_id,
            event_no=2,
            event_source="provider",
            event_kind="output_delta",
            provider_event_name="response.output_text.delta",
            summary="Provider emitted output.",
            detail=None,
            occurred_at=terminal_at - timedelta(seconds=1),
        ),
        ProviderEventRecordModel(
            provider_event_record_id=f"provider-event.{dispatch_id}.3",
            dispatch_id=dispatch_id,
            task_id=task_id,
            attempt_id=attempt_id,
            event_no=3,
            event_source="provider",
            event_kind="response_completed",
            provider_event_name="response.completed",
            summary="Provider completed.",
            detail=None,
            occurred_at=terminal_at,
        ),
    ]


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


@pytest.mark.asyncio
async def test_phase4b_watchdog_classifies_terminal_provider_without_controller_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_watchdog_env(monkeypatch, auto_recover=False)

    async with manual_watchdog_context(
        tmp_path,
        task_id="task_phase4b_terminal_without_controller_checkpoint",
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        terminal_at = datetime.now(tz=UTC) - timedelta(seconds=3)

        async with context.api.session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            assert dispatch is not None
            assert dispatch.attempt_id is not None
            assert delivery_state is not None
            assert watchdog_state is not None
            dispatch.control_state = "fenced"
            dispatch.fenced_at = terminal_at
            dispatch.closed_at = terminal_at
            dispatch.delivery_status = "provider_completed"
            delivery_state.transport_state = "provider_completed"
            delivery_state.controller_observation_state = "fenced"
            delivery_state.last_provider_event_kind = "response_completed"
            delivery_state.provider_final_status = "ok"
            delivery_state.last_provider_signal_at = terminal_at
            delivery_state.last_controller_terminal_at = terminal_at
            delivery_state.updated_at = terminal_at
            reset_watchdog_row(watchdog_state)
            session.add_all(
                _terminal_provider_events(
                    dispatch_id,
                    task_id=context.task_id,
                    attempt_id=dispatch.attempt_id,
                    terminal_at=terminal_at,
                )
            )
            await session.commit()

        changed = await reconcile_watchdog_truth(context.api.session_factory)
        assert changed is True
        watchdog_state = await load_watchdog_state(context, dispatch_id=dispatch_id)
        assert watchdog_state.watchdog_state == "classified"
        assert (
            watchdog_state.current_watchdog_kind
            == "execution_running.terminal_provider_without_controller_checkpoint"
        )
        assert watchdog_state.recovery_action == "create_new_attempt"
        assert watchdog_state.recovery_dispatch_id is None


@pytest.mark.asyncio
async def test_phase4b_watchdog_classifies_delivery_path_rebound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_watchdog_env(
        monkeypatch,
        bootstrap_timeout_seconds=300,
        execution_stale_after_seconds=300,
        auto_recover=False,
    )

    async with manual_watchdog_context(
        tmp_path,
        task_id="task_phase4b_delivery_path_rebound",
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        observed_at = datetime.now(tz=UTC)

        async with context.api.session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            continuity_state = await session.get(DispatchContinuityStateModel, dispatch_id)
            watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            assert dispatch is not None
            assert delivery_state is not None
            assert continuity_state is not None
            assert watchdog_state is not None
            dispatch.control_state = "live"
            dispatch.accepted_boundary = None
            delivery_state.accepted_at = observed_at
            delivery_state.updated_at = observed_at
            continuity_state.continuity_state = "rebound"
            continuity_state.session_key_present = True
            continuity_state.invalidation_reason = "continuity:rebound"
            continuity_state.updated_at = observed_at
            reset_watchdog_row(watchdog_state)
            await session.commit()

        changed = await reconcile_watchdog_truth(context.api.session_factory)
        assert changed is True
        watchdog_state = await load_watchdog_state(context, dispatch_id=dispatch_id)
        assert watchdog_state.watchdog_state == "classified"
        assert watchdog_state.current_watchdog_kind == "execution_running.delivery_path_rebound"
        assert watchdog_state.current_watchdog_reason == "continuity:rebound"
        assert watchdog_state.recovery_action == "escalate"
        assert watchdog_state.recovery_dispatch_id is None
