from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from autoclaw.persistence import DispatchTurnModel, NodeSessionModel
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_dispatch_support import current_open_dispatch_id
from tests.integration.watchdog.case_support import configure_watchdog_env
from tests.integration.watchdog.recovery_action_support import (
    assert_watchdog_state_payload,
    mark_dispatch_live_without_callback,
    prime_abort_completion_recovery,
    wait_for_watchdog_recovery_action,
)
from tests.integration.watchdog.support import (
    phase4b_watchdog_api,
    wait_for_watchdog_condition,
)


@pytest.mark.asyncio
async def test_phase4b_watchdog_escalates_when_parent_continuity_is_missing(
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
        watchdog_state = await wait_for_watchdog_condition(
            context,
            dispatch_id=dispatch_id,
            predicate=lambda row: row.recovery_action == "escalate",
            max_cycles=12,
        )
        assert watchdog_state.current_watchdog_kind == "execution_running.delivery_path_rebound"
        assert watchdog_state.recovery_dispatch_id is None
        async with context.api.session_factory() as session:
            original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert original_dispatch is not None
            assert original_dispatch.control_state == "ambiguous"
            assert original_dispatch.superseded_by_dispatch_id is None
        assert_watchdog_state_payload(
            task_root=context.task_root,
            dispatch_id=dispatch_id,
            replacement_dispatch_id=None,
            expected_kind="execution_running.delivery_path_rebound",
            expected_action="escalate",
        )
