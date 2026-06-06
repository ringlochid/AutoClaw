from __future__ import annotations

from pathlib import Path

import autoclaw.interfaces.cli as cli
from autoclaw.config import get_settings
from autoclaw.persistence.session import dispose_db_engine, get_session_factory
from tests.integration.gateway.dispatch_gateway_support import (
    DispatchGatewaySnapshot,
    load_latest_dispatch_snapshot,
)


async def load_dispatch_snapshot_from_config(
    *,
    config_path: Path,
    task_id: str,
) -> DispatchGatewaySnapshot:
    try:
        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()
            async with session_factory() as session:
                return await load_latest_dispatch_snapshot(session, task_id=task_id)
    finally:
        await dispose_db_engine()


def assert_transport_failed_launch_snapshot(
    snapshot: DispatchGatewaySnapshot,
    *,
    invalidation_reason: str | None = None,
    expected_event_kinds: list[str],
    expect_node_session_none: bool = False,
    expect_provider_error: bool = False,
    expect_transport_family: bool = False,
) -> None:
    assert snapshot.flow.current_open_dispatch_id is None
    assert snapshot.delivery_state is not None
    assert snapshot.continuity_state is not None
    assert snapshot.dispatch.delivery_status == "transport_failed"
    assert snapshot.dispatch.control_state == "fenced"
    assert snapshot.dispatch.gateway_session_key is None
    assert snapshot.dispatch.gateway_run_id is None
    if expect_transport_family:
        assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
    assert snapshot.delivery_state.transport_state == "transport_failed"
    if expect_provider_error:
        assert snapshot.delivery_state.provider_error is not None
    assert snapshot.continuity_state.session_key_present is False
    if invalidation_reason is not None:
        assert snapshot.continuity_state.invalidation_reason == invalidation_reason
    if expect_node_session_none:
        assert snapshot.node_session is None
    assert [event.event_kind for event in snapshot.provider_events] == expected_event_kinds


def assert_transport_ambiguous_launch_snapshot(
    snapshot: DispatchGatewaySnapshot,
    *,
    invalidation_reason: str | None = None,
    expect_provider_error: bool = False,
    expect_transport_family: bool = False,
) -> None:
    assert snapshot.delivery_state is not None
    assert snapshot.continuity_state is not None
    assert snapshot.dispatch.delivery_status == "transport_ambiguous"
    assert snapshot.dispatch.control_state == "ambiguous"
    assert snapshot.dispatch.gateway_session_key is not None
    assert snapshot.dispatch.gateway_run_id is None
    if expect_transport_family:
        assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
    assert snapshot.delivery_state.transport_state == "transport_ambiguous"
    if expect_provider_error:
        assert snapshot.delivery_state.provider_error is not None
    assert snapshot.continuity_state.session_key_present is True
    if invalidation_reason is not None:
        assert snapshot.continuity_state.invalidation_reason == invalidation_reason
    assert [event.event_kind for event in snapshot.provider_events] == [
        "transport_failed",
        "tool_event",
    ]
