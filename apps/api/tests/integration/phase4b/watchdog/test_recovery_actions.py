from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.db import (
    AssignmentModel,
    AttemptModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
)
from sqlalchemy import select
from tests.integration.phase3.dispatch_support import current_open_dispatch_id, read_json
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.watchdog.case_support import (
    configure_watchdog_env,
    reset_watchdog_row,
)
from tests.integration.phase4b.watchdog.support import (
    phase4b_watchdog_api,
    wait_for_watchdog_condition,
)


@pytest.mark.asyncio
async def test_phase4b_watchdog_classifies_bootstrap_callback_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    configure_watchdog_env(
        monkeypatch,
        bootstrap_timeout_seconds=1,
        execution_stale_after_seconds=300,
    )

    async with phase4b_watchdog_api(
        tmp_path,
        task_id="task_phase4b_bootstrap_timeout",
        compiler_version="phase-4b-watchdog-bootstrap-timeout",
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        accepted_at = datetime.now(tz=UTC) - timedelta(seconds=5)

        async with context.api.session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            assert dispatch is not None
            assert delivery_state is not None
            assert watchdog_state is not None
            dispatch.control_state = "live"
            dispatch.accepted_boundary = None
            delivery_state.accepted_at = accepted_at
            delivery_state.updated_at = accepted_at
            reset_watchdog_row(watchdog_state)
            await session.commit()

        watchdog_state = await wait_for_watchdog_condition(
            context,
            dispatch_id=dispatch_id,
            predicate=lambda row: row.recovery_dispatch_id is not None,
        )
        assert watchdog_state.watchdog_state == "classified"
        assert (
            watchdog_state.current_watchdog_kind
            == "bootstrap_pending_callback.bootstrap_callback_timeout"
        )
        assert watchdog_state.recovery_action == "redispatch_same_attempt"
        assert watchdog_state.recovery_dispatch_id is not None

        replacement_dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        assert replacement_dispatch_id != dispatch_id
        assert watchdog_state.recovery_dispatch_id == replacement_dispatch_id

        async with context.api.session_factory() as session:
            original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
            replacement_dispatch = await session.get(DispatchTurnModel, replacement_dispatch_id)
            assert original_dispatch is not None
            assert replacement_dispatch is not None
            assert original_dispatch.control_state == "fenced"
            assert original_dispatch.superseded_by_dispatch_id == replacement_dispatch_id
            assert replacement_dispatch.previous_dispatch_id == dispatch_id
            assert replacement_dispatch.attempt_id == original_dispatch.attempt_id

        payload = read_json(
            context.task_root / "_runtime" / "dispatch" / dispatch_id / "watchdog-state.json"
        )
        assert payload["current_watchdog_kind"] == (
            "bootstrap_pending_callback.bootstrap_callback_timeout"
        )
        assert payload["recovery_action"] == "redispatch_same_attempt"
        assert payload["recovery_dispatch_id"] == replacement_dispatch_id


@pytest.mark.asyncio
async def test_phase4b_watchdog_classifies_execution_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    configure_watchdog_env(
        monkeypatch,
        bootstrap_timeout_seconds=300,
        execution_stale_after_seconds=1,
    )

    async with phase4b_watchdog_api(
        tmp_path,
        task_id="task_phase4b_execution_stale",
        compiler_version="phase-4b-watchdog-execution-stale",
        openclaw_gateway_test_server=openclaw_gateway_test_server,
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
            dispatch.control_state = "live"
            dispatch.accepted_boundary = None
            delivery_state.accepted_at = stale_at
            delivery_state.last_controller_progress_at = stale_at
            delivery_state.updated_at = stale_at
            reset_watchdog_row(watchdog_state)
            await session.commit()

        watchdog_state = await wait_for_watchdog_condition(
            context,
            dispatch_id=dispatch_id,
            predicate=lambda row: row.recovery_dispatch_id is not None,
        )
        assert watchdog_state.watchdog_state == "classified"
        assert watchdog_state.current_watchdog_kind == "execution_running.execution_stale"
        assert watchdog_state.recovery_action == "redispatch_same_attempt"
        assert watchdog_state.recovery_dispatch_id is not None

        replacement_dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        assert replacement_dispatch_id == watchdog_state.recovery_dispatch_id
        assert replacement_dispatch_id != dispatch_id

        async with context.api.session_factory() as session:
            original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
            replacement_dispatch = await session.get(DispatchTurnModel, replacement_dispatch_id)
            assert original_dispatch is not None
            assert replacement_dispatch is not None
            assert original_dispatch.superseded_by_dispatch_id == replacement_dispatch_id
            assert replacement_dispatch.previous_dispatch_id == dispatch_id
            assert replacement_dispatch.attempt_id == original_dispatch.attempt_id


@pytest.mark.asyncio
async def test_phase4b_watchdog_classifies_terminal_provider_without_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    configure_watchdog_env(monkeypatch)

    async with phase4b_watchdog_api(
        tmp_path,
        task_id="task_phase4b_terminal_without_checkpoint",
        compiler_version="phase-4b-watchdog-terminal-without-checkpoint",
        openclaw_gateway_test_server=openclaw_gateway_test_server,
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
            dispatch.control_state = "fenced"
            dispatch.fenced_at = terminal_at
            dispatch.closed_at = terminal_at
            dispatch.delivery_status = "provider_completed"
            delivery_state.transport_state = "provider_completed"
            delivery_state.controller_observation_state = "fenced"
            delivery_state.provider_final_status = "ok"
            delivery_state.last_provider_signal_at = terminal_at
            delivery_state.last_controller_terminal_at = terminal_at
            delivery_state.updated_at = terminal_at
            reset_watchdog_row(watchdog_state)
            await session.commit()

        watchdog_state = await wait_for_watchdog_condition(
            context,
            dispatch_id=dispatch_id,
            predicate=lambda row: row.recovery_dispatch_id is not None,
        )
        assert watchdog_state.watchdog_state == "classified"
        assert (
            watchdog_state.current_watchdog_kind
            == "execution_running.terminal_provider_without_controller_checkpoint"
        )
        assert watchdog_state.recovery_action == "create_new_attempt"
        assert watchdog_state.recovery_dispatch_id is not None

        replacement_dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        assert replacement_dispatch_id == watchdog_state.recovery_dispatch_id
        assert replacement_dispatch_id != dispatch_id

        async with context.api.session_factory() as session:
            original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
            replacement_dispatch = await session.get(DispatchTurnModel, replacement_dispatch_id)
            assert original_dispatch is not None
            assert replacement_dispatch is not None
            assignment = await session.get(AssignmentModel, original_dispatch.assignment_id)
            previous_attempt = await session.get(AttemptModel, original_dispatch.attempt_id)
            replacement_attempt = await session.get(AttemptModel, replacement_dispatch.attempt_id)
            assert assignment is not None
            assert previous_attempt is not None
            assert replacement_attempt is not None
            assert original_dispatch.superseded_by_dispatch_id == replacement_dispatch_id
            assert replacement_dispatch.previous_dispatch_id == dispatch_id
            assert replacement_dispatch.attempt_id != original_dispatch.attempt_id
            assert assignment.current_attempt_id == replacement_dispatch.attempt_id
            assert previous_attempt.closed_at is not None
            assert previous_attempt.status == "failed"
            assert replacement_attempt.retry_of_attempt_id == previous_attempt.attempt_id
