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
from app.runtime.openclaw.fixtures import agent_wait_fixture
from sqlalchemy import select
from tests.integration.phase3.dispatch_support import current_open_dispatch_id, read_json
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.watchdog.case_support import (
    configure_watchdog_env,
    reset_watchdog_row,
)
from tests.integration.phase4b.watchdog.support import (
    Phase4BWatchdogContext,
    phase4b_watchdog_api,
    wait_for_watchdog_condition,
    wait_for_watchdog_cycle,
)


async def mark_dispatch_live_without_callback(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
    observed_at: datetime,
    last_controller_progress_at: datetime | None = None,
) -> None:
    async with context.api.session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
        watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
        assert dispatch is not None
        assert delivery_state is not None
        assert watchdog_state is not None
        dispatch.control_state = "live"
        dispatch.accepted_boundary = None
        delivery_state.accepted_at = observed_at
        delivery_state.updated_at = observed_at
        if last_controller_progress_at is not None:
            delivery_state.last_controller_progress_at = last_controller_progress_at
        reset_watchdog_row(watchdog_state)
        await session.commit()


async def wait_for_watchdog_recovery_action(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
    expected_kind: str,
    expected_action: str,
) -> DispatchWatchdogStateModel:
    watchdog_state = await wait_for_watchdog_condition(
        context,
        dispatch_id=dispatch_id,
        predicate=lambda row: row.recovery_action == expected_action,
        max_cycles=12,
    )
    assert watchdog_state.watchdog_state == "classified"
    assert watchdog_state.current_watchdog_kind == expected_kind
    assert watchdog_state.recovery_action == expected_action
    return watchdog_state


async def prime_abort_completion_recovery(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
    watchdog_state: DispatchWatchdogStateModel,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    async with context.api.session_factory() as session:
        original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert original_dispatch is not None
        assert original_dispatch.control_state == "abort_requested"
        assert watchdog_state.recovery_dispatch_id is None
        assert isinstance(original_dispatch.gateway_run_id, str)
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="ok", run_id=original_dispatch.gateway_run_id),
        )


async def wait_for_recovery_dispatch_id(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
) -> str:
    watchdog_state = await wait_for_watchdog_condition(
        context,
        dispatch_id=dispatch_id,
        predicate=lambda row: row.recovery_dispatch_id is not None,
        max_cycles=12,
    )
    replacement_dispatch_id = watchdog_state.recovery_dispatch_id
    assert replacement_dispatch_id is not None
    assert replacement_dispatch_id != dispatch_id
    return replacement_dispatch_id


async def assert_same_attempt_replacement_lineage(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
    replacement_dispatch_id: str,
) -> None:
    original_dispatch: DispatchTurnModel | None = None
    replacement_dispatch: DispatchTurnModel | None = None
    for _ in range(12):
        async with context.api.session_factory() as session:
            original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
            replacement_dispatch = await session.get(DispatchTurnModel, replacement_dispatch_id)
            if (
                original_dispatch is not None
                and replacement_dispatch is not None
                and original_dispatch.control_state == "fenced"
                and original_dispatch.superseded_by_dispatch_id == replacement_dispatch_id
                and replacement_dispatch.previous_dispatch_id == dispatch_id
                and replacement_dispatch.attempt_id == original_dispatch.attempt_id
                and replacement_dispatch.gateway_session_key
                == original_dispatch.gateway_session_key
                and replacement_dispatch.gateway_run_id != original_dispatch.gateway_run_id
            ):
                return
        await wait_for_watchdog_cycle(task_id=context.task_id)
    assert original_dispatch is not None
    assert replacement_dispatch is not None
    assert original_dispatch.control_state == "fenced"
    assert original_dispatch.superseded_by_dispatch_id == replacement_dispatch_id
    assert replacement_dispatch.previous_dispatch_id == dispatch_id
    assert replacement_dispatch.attempt_id == original_dispatch.attempt_id
    assert replacement_dispatch.gateway_session_key == original_dispatch.gateway_session_key
    assert replacement_dispatch.gateway_run_id != original_dispatch.gateway_run_id


def assert_watchdog_state_payload(
    *,
    task_root: Path,
    dispatch_id: str,
    replacement_dispatch_id: str,
    expected_kind: str,
    expected_action: str,
) -> None:
    payload = read_json(task_root / "_runtime" / "dispatch" / dispatch_id / "watchdog-state.json")
    assert payload["current_watchdog_kind"] == expected_kind
    assert payload["recovery_action"] == expected_action
    assert payload["recovery_dispatch_id"] == replacement_dispatch_id


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
        await mark_dispatch_live_without_callback(
            context,
            dispatch_id=dispatch_id,
            observed_at=accepted_at,
        )
        watchdog_state = await wait_for_watchdog_recovery_action(
            context,
            dispatch_id=dispatch_id,
            expected_kind="bootstrap_pending_callback.bootstrap_callback_timeout",
            expected_action="redispatch_same_attempt",
        )
        await prime_abort_completion_recovery(
            context,
            dispatch_id=dispatch_id,
            watchdog_state=watchdog_state,
            openclaw_gateway_test_server=openclaw_gateway_test_server,
        )
        replacement_dispatch_id = await wait_for_recovery_dispatch_id(
            context,
            dispatch_id=dispatch_id,
        )
        await assert_same_attempt_replacement_lineage(
            context,
            dispatch_id=dispatch_id,
            replacement_dispatch_id=replacement_dispatch_id,
        )
        assert_watchdog_state_payload(
            task_root=context.task_root,
            dispatch_id=dispatch_id,
            replacement_dispatch_id=replacement_dispatch_id,
            expected_kind="bootstrap_pending_callback.bootstrap_callback_timeout",
            expected_action="redispatch_same_attempt",
        )


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
        await mark_dispatch_live_without_callback(
            context,
            dispatch_id=dispatch_id,
            observed_at=stale_at,
            last_controller_progress_at=stale_at,
        )
        watchdog_state = await wait_for_watchdog_recovery_action(
            context,
            dispatch_id=dispatch_id,
            expected_kind="execution_running.execution_stale",
            expected_action="redispatch_same_attempt",
        )
        await prime_abort_completion_recovery(
            context,
            dispatch_id=dispatch_id,
            watchdog_state=watchdog_state,
            openclaw_gateway_test_server=openclaw_gateway_test_server,
        )
        replacement_dispatch_id = await wait_for_recovery_dispatch_id(
            context,
            dispatch_id=dispatch_id,
        )
        await assert_same_attempt_replacement_lineage(
            context,
            dispatch_id=dispatch_id,
            replacement_dispatch_id=replacement_dispatch_id,
        )


@pytest.mark.asyncio
async def test_phase4b_watchdog_classifies_terminal_provider_without_first_callback(
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
            delivery_state.provider_final_status = "ok"
            delivery_state.last_provider_signal_at = terminal_at
            delivery_state.last_controller_terminal_at = terminal_at
            delivery_state.updated_at = terminal_at
            reset_watchdog_row(watchdog_state)
            await session.commit()

        watchdog_state = await wait_for_watchdog_condition(
            context,
            dispatch_id=dispatch_id,
            predicate=lambda row: row.recovery_action == "escalate",
        )
        assert watchdog_state.watchdog_state == "classified"
        assert (
            watchdog_state.current_watchdog_kind
            == "bootstrap_pending_callback.terminal_provider_without_first_callback"
        )
        assert watchdog_state.recovery_action == "escalate"
        assert watchdog_state.recovery_dispatch_id is None

        async with context.api.session_factory() as session:
            flow = await session.scalar(
                select(FlowModel).where(FlowModel.task_id == context.task_id)
            )
            original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert flow is not None
            assert original_dispatch is not None
            assert flow.current_open_dispatch_id is None
            assert original_dispatch.superseded_by_dispatch_id is None


@pytest.mark.asyncio
async def test_phase4b_watchdog_escalates_when_same_attempt_recovery_cap_is_exhausted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    configure_watchdog_env(
        monkeypatch,
        bootstrap_timeout_seconds=1,
        execution_stale_after_seconds=300,
        same_attempt_redispatch_limit=0,
    )

    async with phase4b_watchdog_api(
        tmp_path,
        task_id="task_phase4b_same_attempt_cap_exhausted",
        compiler_version="phase-4b-watchdog-cap-exhausted",
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
            predicate=lambda row: row.recovery_action == "escalate",
        )
        assert watchdog_state.current_watchdog_kind == (
            "bootstrap_pending_callback.bootstrap_callback_timeout"
        )
        assert watchdog_state.recovery_dispatch_id is None
        assert "redispatch cap" in (watchdog_state.recovery_reason or "")
