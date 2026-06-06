from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from autoclaw.persistence import (
    AttemptModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
    NodeSessionModel,
)
from autoclaw.runtime.watchdog.recovery import execute_watchdog_recovery
from sqlalchemy import select
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_dispatch_support import current_open_dispatch_id
from tests.integration.watchdog.case_support import (
    configure_watchdog_env,
    reset_watchdog_row,
)
from tests.integration.watchdog.recovery_action_support import (
    assert_same_attempt_replacement_lineage,
    assert_watchdog_state_payload,
    mark_dispatch_live_without_callback,
    prime_abort_completion_recovery,
    wait_for_recovery_dispatch_id,
    wait_for_watchdog_recovery_action,
)
from tests.integration.watchdog.support import (
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
        dispatch_drain_timeout_seconds=30,
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
        dispatch_drain_timeout_seconds=30,
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
async def test_phase4b_watchdog_commits_terminal_abort_normalization_without_recovery_open(
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
        task_id="task_phase4b_watchdog_terminal_abort_requested_normalization",
        compiler_version="phase-4b-watchdog-terminal-abort-normalization",
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        terminal_at = datetime.now(tz=UTC) - timedelta(seconds=5)

        async with context.api.session_factory() as session:
            flow = await session.scalar(
                select(FlowModel).where(FlowModel.task_id == context.task_id)
            )
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            assert flow is not None
            assert dispatch is not None
            assert dispatch.attempt_id is not None
            attempt = await session.get(AttemptModel, dispatch.attempt_id)
            assert attempt is not None
            assert delivery_state is not None
            assert watchdog_state is not None
            flow.current_open_dispatch_id = None
            dispatch.control_state = "abort_requested"
            dispatch.control_state_reason = "watchdog:execution_running.execution_stale"
            dispatch.abort_requested_at = terminal_at
            dispatch.closed_at = terminal_at
            dispatch.delivery_status = "provider_completed"
            delivery_state.transport_state = "provider_completed"
            delivery_state.provider_final_status = "ok"
            delivery_state.last_provider_signal_at = terminal_at
            delivery_state.updated_at = terminal_at
            reset_watchdog_row(watchdog_state)
            watchdog_state.recovery_action = "redispatch_same_attempt"
            watchdog_state.current_watchdog_kind = "execution_running.execution_stale"
            attempt.closed_at = terminal_at
            await session.commit()

        changed = await execute_watchdog_recovery(
            context.api.session_factory,
            task_id=context.task_id,
            dispatch_id=dispatch_id,
        )
        assert changed is True

        async with context.api.session_factory() as session:
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
            node_session = await session.get(NodeSessionModel, f"node-session.{dispatch_id}")
            watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            assert dispatch is not None
            assert delivery_state is not None
            assert node_session is not None
            assert watchdog_state is not None
            assert dispatch.control_state == "fenced"
            assert dispatch.control_deadline_at is None
            assert dispatch.fenced_at is not None
            assert dispatch.delivery_status == "provider_completed"
            assert delivery_state.transport_state == "provider_completed"
            assert delivery_state.last_controller_terminal_at is not None
            assert node_session.session_status == "fenced"
            assert node_session.closed_at is not None
            assert watchdog_state.recovery_dispatch_id is None


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
        assert watchdog_state.current_watchdog_reason == (
            "provider reached terminal completion before the first provider or controller "
            f"progress was recorded for dispatch {dispatch_id}"
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
