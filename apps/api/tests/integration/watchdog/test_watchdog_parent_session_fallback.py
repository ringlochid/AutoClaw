from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from autoclaw.persistence import (
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    NodeSessionModel,
)
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_dispatch_support import current_open_dispatch_id
from tests.integration.watchdog.case_support import configure_watchdog_env
from tests.integration.watchdog.recovery_action_support import (
    assert_watchdog_state_payload,
    mark_dispatch_live_without_callback,
    prime_abort_completion_recovery,
    wait_for_recovery_dispatch_id,
    wait_for_watchdog_recovery_action,
)
from tests.integration.watchdog.support import WatchdogApiContext, watchdog_api_context


async def assert_parent_continuity_recovery_fallback(
    context: WatchdogApiContext,
    *,
    dispatch_id: str,
    replacement_dispatch_id: str,
    original_gateway_session_key: str,
    original_gateway_run_id: str,
) -> None:
    async with context.api.session_factory() as session:
        original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
        replacement_dispatch = await session.get(DispatchTurnModel, replacement_dispatch_id)
        reloaded_watchdog_state = await session.get(
            DispatchWatchdogStateModel,
            dispatch_id,
        )
        assert original_dispatch is not None
        assert replacement_dispatch is not None
        assert reloaded_watchdog_state is not None
        assert original_dispatch.control_state == "fenced"
        assert original_dispatch.superseded_by_dispatch_id == replacement_dispatch_id
        assert replacement_dispatch.previous_dispatch_id == dispatch_id
        assert replacement_dispatch.attempt_id == original_dispatch.attempt_id
        assert replacement_dispatch.gateway_session_key is not None
        assert replacement_dispatch.gateway_session_key != original_gateway_session_key
        assert replacement_dispatch.gateway_run_id != original_gateway_run_id
        assert reloaded_watchdog_state.current_watchdog_kind == "execution_running.execution_stale"
        assert reloaded_watchdog_state.recovery_action == "redispatch_same_attempt"
        assert reloaded_watchdog_state.recovery_dispatch_id == replacement_dispatch_id

    assert_watchdog_state_payload(
        task_root=context.task_root,
        dispatch_id=dispatch_id,
        replacement_dispatch_id=replacement_dispatch_id,
        expected_kind="execution_running.execution_stale",
        expected_action="redispatch_same_attempt",
    )


@pytest.mark.asyncio
async def test_watchdog_escalates_when_parent_continuity_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    configure_watchdog_env(
        monkeypatch,
        bootstrap_timeout_seconds=300,
        execution_stale_after_seconds=1,
    )

    async with watchdog_api_context(
        tmp_path,
        task_id="task_watchdog_parent_fresh_session_fallback",
        compiler_version="watchdog-parent-fresh-session-fallback",
        openclaw_gateway_test_server=openclaw_gateway_test_server,
        dispatch_drain_timeout_seconds=30,
    ) as context:
        dispatch_id = await current_open_dispatch_id(
            context.api.session_factory,
            task_id=context.task_id,
        )
        async with context.api.session_factory() as session:
            original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert original_dispatch is not None
            assert original_dispatch.gateway_session_key is not None
            assert isinstance(original_dispatch.gateway_run_id, str)
            original_gateway_session_key = original_dispatch.gateway_session_key
            original_gateway_run_id = original_dispatch.gateway_run_id
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
        async with context.api.session_factory() as session:
            node_session = await session.get(
                NodeSessionModel,
                f"node-session.{dispatch_id}",
            )
            assert node_session is not None
            await session.delete(node_session)
            await session.commit()
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
        await assert_parent_continuity_recovery_fallback(
            context,
            dispatch_id=dispatch_id,
            replacement_dispatch_id=replacement_dispatch_id,
            original_gateway_session_key=original_gateway_session_key,
            original_gateway_run_id=original_gateway_run_id,
        )
