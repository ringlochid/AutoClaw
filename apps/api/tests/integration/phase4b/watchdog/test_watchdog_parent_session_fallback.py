from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from autoclaw.db import DispatchTurnModel, NodeSessionModel
from tests.integration.phase3.dispatch_support import current_open_dispatch_id
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.watchdog.case_support import configure_watchdog_env
from tests.integration.phase4b.watchdog.support import (
    Phase4BWatchdogContext,
    phase4b_watchdog_api,
    wait_for_watchdog_cycle,
)
from tests.integration.phase4b.watchdog.test_recovery_actions import (
    assert_watchdog_state_payload,
    mark_dispatch_live_without_callback,
    prime_abort_completion_recovery,
    wait_for_recovery_dispatch_id,
    wait_for_watchdog_recovery_action,
)


async def assert_same_attempt_replacement_uses_fresh_session_key(
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
                and replacement_dispatch.gateway_session_key is not None
                and replacement_dispatch.gateway_session_key
                != original_dispatch.gateway_session_key
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
    assert replacement_dispatch.gateway_session_key is not None
    assert replacement_dispatch.gateway_session_key != original_dispatch.gateway_session_key
    assert replacement_dispatch.gateway_run_id != original_dispatch.gateway_run_id


@pytest.mark.asyncio
async def test_phase4b_watchdog_falls_back_to_fresh_session_when_parent_continuity_is_missing(
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
        task_id="task_phase4b_watchdog_parent_fresh_session_fallback",
        compiler_version="phase-4b-watchdog-parent-fresh-session-fallback",
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
        await assert_same_attempt_replacement_uses_fresh_session_key(
            context,
            dispatch_id=dispatch_id,
            replacement_dispatch_id=replacement_dispatch_id,
        )
        assert_watchdog_state_payload(
            task_root=context.task_root,
            dispatch_id=dispatch_id,
            replacement_dispatch_id=replacement_dispatch_id,
            expected_kind="execution_running.execution_stale",
            expected_action="redispatch_same_attempt",
        )
