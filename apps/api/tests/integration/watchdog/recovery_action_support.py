from __future__ import annotations

from datetime import datetime
from pathlib import Path

from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import (
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
)
from autoclaw.runtime.post_commit import drive_runtime_until
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support.dispatch import read_json
from tests.integration.watchdog.case_support import reset_watchdog_row
from tests.integration.watchdog.support import (
    WatchdogApiContext,
    wait_for_watchdog_condition,
)


async def mark_dispatch_live_without_callback(
    context: WatchdogApiContext,
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
    context: WatchdogApiContext,
    *,
    dispatch_id: str,
    expected_kind: str,
    expected_action: str,
) -> DispatchWatchdogStateModel:
    return await wait_for_watchdog_condition(
        context,
        dispatch_id=dispatch_id,
        predicate=lambda row: (
            row.watchdog_state == "classified"
            and row.current_watchdog_kind == expected_kind
            and row.recovery_action == expected_action
        ),
        max_cycles=12,
    )


async def prime_abort_completion_recovery(
    context: WatchdogApiContext,
    *,
    dispatch_id: str,
    watchdog_state: DispatchWatchdogStateModel,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    assert watchdog_state.recovery_dispatch_id is None

    async def abort_completion_ready() -> bool:
        async with context.api.session_factory() as session:
            original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
            current_watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
            return (
                original_dispatch is not None
                and original_dispatch.control_state == "abort_requested"
                and current_watchdog_state is not None
                and current_watchdog_state.recovery_dispatch_id is None
            )

    await drive_runtime_until(
        abort_completion_ready,
        task_id=context.task_id,
        max_cycles=12,
    )

    async with context.api.session_factory() as session:
        original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
        current_watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
        assert original_dispatch is not None
        assert current_watchdog_state is not None
        assert original_dispatch.control_state == "abort_requested"
        assert current_watchdog_state.recovery_dispatch_id is None
        assert isinstance(original_dispatch.gateway_run_id, str)
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="ok", run_id=original_dispatch.gateway_run_id),
        )


async def wait_for_recovery_dispatch_id(
    context: WatchdogApiContext,
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
    context: WatchdogApiContext,
    *,
    dispatch_id: str,
    replacement_dispatch_id: str,
) -> None:
    async def same_attempt_replacement_ready() -> bool:
        async with context.api.session_factory() as session:
            original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
            replacement_dispatch = await session.get(DispatchTurnModel, replacement_dispatch_id)
            return (
                original_dispatch is not None
                and replacement_dispatch is not None
                and original_dispatch.control_state == "fenced"
                and original_dispatch.superseded_by_dispatch_id == replacement_dispatch_id
                and replacement_dispatch.previous_dispatch_id == dispatch_id
                and replacement_dispatch.attempt_id == original_dispatch.attempt_id
                and replacement_dispatch.gateway_session_key
                == original_dispatch.gateway_session_key
                and replacement_dispatch.gateway_run_id != original_dispatch.gateway_run_id
            )

    await drive_runtime_until(
        same_attempt_replacement_ready,
        task_id=context.task_id,
        max_cycles=12,
    )

    async with context.api.session_factory() as session:
        original_dispatch = await session.get(DispatchTurnModel, dispatch_id)
        replacement_dispatch = await session.get(DispatchTurnModel, replacement_dispatch_id)
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
    replacement_dispatch_id: str | None,
    expected_kind: str,
    expected_action: str,
) -> None:
    payload = read_json(task_root / "_runtime" / "dispatch" / dispatch_id / "watchdog-state.json")
    assert payload["current_watchdog_kind"] == expected_kind
    assert payload["recovery_action"] == expected_action
    assert payload["recovery_dispatch_id"] == replacement_dispatch_id


__all__ = [
    "assert_same_attempt_replacement_lineage",
    "assert_watchdog_state_payload",
    "mark_dispatch_live_without_callback",
    "prime_abort_completion_recovery",
    "wait_for_recovery_dispatch_id",
    "wait_for_watchdog_recovery_action",
]
