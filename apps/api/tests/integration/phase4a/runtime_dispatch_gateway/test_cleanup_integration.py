from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import DispatchTurnModel
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.dispatch.gateway_launch_state import (
    append_dispatch_event as original_append_dispatch_event,
)
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase2.bootstrap.support import phase2_runtime_context
from tests.integration.phase4a.dispatch_gateway_support import load_latest_dispatch_snapshot
from tests.integration.phase4a.support import LocalGatewayTestServer


def patch_acceptance_event_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    failed_once = False

    async def fail_acceptance_event(
        session: AsyncSession,
        *,
        dispatch: DispatchTurnModel,
        attempt_id: str,
        event_kind: str,
        summary: str,
        detail: str,
        provider_event_name: str | None = None,
        provider_occurred_at: datetime | None = None,
        event_payload_json: dict[str, object] | None = None,
    ) -> None:
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            raise RuntimeError("acceptance event write failed")
        await original_append_dispatch_event(
            session,
            dispatch=dispatch,
            attempt_id=attempt_id,
            event_kind=event_kind,
            summary=summary,
            detail=detail,
            provider_event_name=provider_event_name,
            provider_occurred_at=provider_occurred_at,
            event_payload_json=event_payload_json,
        )

    monkeypatch.setattr(
        "autoclaw.runtime.dispatch.gateway_launch_state.append_dispatch_event",
        fail_acceptance_event,
    )


def assert_post_acceptance_cleanup_snapshot(snapshot: Any) -> None:
    assert snapshot.flow.current_open_dispatch_id is None
    assert snapshot.delivery_state is not None
    assert snapshot.continuity_state is not None
    assert snapshot.dispatch.delivery_status == "provider_completed"
    assert snapshot.dispatch.control_state == "fenced"
    assert snapshot.dispatch.gateway_session_key is not None
    assert snapshot.dispatch.gateway_run_id == "run-1"
    assert snapshot.dispatch.closed_at is not None
    assert snapshot.dispatch.fenced_at is not None
    assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
    assert snapshot.delivery_state.transport_state == "provider_completed"
    assert snapshot.delivery_state.accepted_at is not None
    assert snapshot.continuity_state.session_key_present is True
    assert snapshot.continuity_state.invalidation_reason == (
        "gateway_acceptance_persist_failed:RuntimeError"
    )
    assert snapshot.node_session is None
    assert [event.event_kind for event in snapshot.provider_events] == [
        "accepted",
        "tool_event",
        "response_completed",
    ]


@pytest.mark.asyncio
async def test_launch_runtime_post_acceptance_persistence_failure_cleans_up_remote_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4a_launch_gateway_post_acceptance_failure"
    patch_acceptance_event_failure(monkeypatch)
    try:
        async with phase2_runtime_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                with pytest.raises(RuntimeError, match="acceptance event write failed"):
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-4a-post-acceptance-failure",
                    )

            async with runtime.session_factory() as session:
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

        assert_post_acceptance_cleanup_snapshot(snapshot)
        assert {request.method for request in openclaw_gateway_test_server.requests} >= {
            "agent",
            "agent.wait",
            "sessions.abort",
        }
        assert openclaw_gateway_test_server.connection_count == 1
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_launch_runtime_post_acceptance_timeout_stays_ambiguous_and_blocks_current_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4a_launch_gateway_post_acceptance_timeout"
    failed_once = False

    async def fail_acceptance_event(
        session: AsyncSession,
        *,
        dispatch: DispatchTurnModel,
        attempt_id: str,
        event_kind: str,
        summary: str,
        detail: str,
        provider_event_name: str | None = None,
        provider_occurred_at: datetime | None = None,
        event_payload_json: dict[str, object] | None = None,
    ) -> None:
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            raise RuntimeError("acceptance event write failed")
        await original_append_dispatch_event(
            session,
            dispatch=dispatch,
            attempt_id=attempt_id,
            event_kind=event_kind,
            summary=summary,
            detail=detail,
            provider_event_name=provider_event_name,
            provider_occurred_at=provider_occurred_at,
            event_payload_json=event_payload_json,
        )

    openclaw_gateway_test_server.set_default_method_payload(
        "agent.wait",
        agent_wait_fixture(status="timeout"),
    )
    monkeypatch.setattr(
        "autoclaw.runtime.dispatch.gateway_launch_state.append_dispatch_event",
        fail_acceptance_event,
    )
    try:
        async with phase2_runtime_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                with pytest.raises(RuntimeError, match="acceptance event write failed"):
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-4a-post-acceptance-timeout",
                    )

            async with runtime.session_factory() as session:
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

        assert snapshot.flow.current_open_dispatch_id == snapshot.dispatch.dispatch_id
        assert snapshot.dispatch.delivery_status == "transport_ambiguous"
        assert snapshot.dispatch.control_state == "ambiguous"
        assert snapshot.delivery_state is not None
        assert snapshot.delivery_state.transport_state == "transport_ambiguous"
        assert snapshot.continuity_state is not None
        assert snapshot.continuity_state.invalidation_reason == (
            "gateway_acceptance_persist_failed:RuntimeError"
        )
        assert [event.event_kind for event in snapshot.provider_events] == [
            "accepted",
            "tool_event",
            "transport_timeout",
        ]
        assert {request.method for request in openclaw_gateway_test_server.requests} >= {
            "agent",
            "agent.wait",
            "sessions.abort",
        }
        assert openclaw_gateway_test_server.connection_count == 1
    finally:
        await dispose_db_engine()
