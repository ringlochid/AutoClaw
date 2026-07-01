from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from autoclaw.integrations.openclaw.gateway import OpenClawObservedEvent
from autoclaw.integrations.openclaw.gateway.fixtures import (
    connect_challenge_fixture,
    hello_ok_fixture,
)
from autoclaw.persistence import TaskEventModel
from autoclaw.runtime.dispatch.openclaw.event_ingest import (
    normalize_observed_event,
)
from autoclaw.runtime.dispatch.openclaw.models import (
    ActiveOpenClawDispatchRuntime,
    OpenClawDispatchLaunchLease,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.openclaw_gateway_support import gateway_server, recv_json, send_json
from tests.helpers.runtime_support import runtime_bootstrap_context
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload
from tests.integration.gateway.dispatch_gateway_support import (
    DispatchGatewaySnapshot,
    override_gateway_base_url,
    wait_for_latest_dispatch_snapshot,
)
from websockets.asyncio.server import ServerConnection
from websockets.exceptions import ConnectionClosed


def _runtime_for_normalization(
    *,
    has_seen_provider_progress: bool = False,
) -> ActiveOpenClawDispatchRuntime:
    runtime = ActiveOpenClawDispatchRuntime(
        task_id="task-normalization",
        dispatch_id="dispatch.root.01",
        attempt_id="attempt.root.01",
        session_key="session-root-01",
        run_id="run-live",
        lease=cast(OpenClawDispatchLaunchLease, None),
        session_factory=cast(async_sessionmaker, None),
    )
    runtime.has_seen_provider_progress = has_seen_provider_progress
    return runtime


def _observed_event(raw_label: str) -> OpenClawObservedEvent:
    return OpenClawObservedEvent.model_validate(
        {
            "event": raw_label,
            "payload": {
                "runId": "run-live",
                "sessionKey": "session-root-01",
                "ts": "2026-05-24T00:00:01+00:00",
            },
        }
    )


def _agent_stream_observed_event(
    *,
    stream: str,
    data: dict[str, object],
) -> OpenClawObservedEvent:
    return OpenClawObservedEvent.model_validate(
        {
            "event": "agent",
            "payload": {
                "runId": "run-live",
                "sessionKey": "session-root-01",
                "stream": stream,
                "ts": "2026-05-24T00:00:01+00:00",
                "data": data,
            },
        }
    )


@pytest.mark.parametrize(
    ("raw_label", "saw_provider_progress", "expected_kind"),
    [
        ("assistant.delta", False, "first_data"),
        ("assistant.delta", True, "output_delta"),
        ("assistant.message", False, "first_data"),
        ("assistant.message", True, "output_delta"),
        ("thinking.delta", False, "first_data"),
        ("thinking.delta", True, "output_delta"),
        ("response.delta", False, "first_data"),
        ("response.delta", True, "output_delta"),
        ("tool.call", False, "tool_event"),
        ("tool.call.started", False, "tool_event"),
        ("tool.call.completed", False, "tool_event"),
        ("tool.call.failed", False, "tool_event"),
        ("run.completed", False, "response_completed"),
        ("response.completed", False, "response_completed"),
        ("run.failed", False, "response_failed"),
        ("run.cancelled", False, "response_failed"),
        ("run.timed_out", False, "response_failed"),
        ("response.failed", False, "response_failed"),
    ],
)
def test_normalize_observed_event_maps_legacy_direct_labels(
    raw_label: str,
    saw_provider_progress: bool,
    expected_kind: str,
) -> None:
    runtime = _runtime_for_normalization(has_seen_provider_progress=saw_provider_progress)

    normalized = normalize_observed_event(runtime, _observed_event(raw_label))

    assert normalized is not None
    assert normalized.event_kind == expected_kind
    assert normalized.provider_event_name == raw_label


def test_normalize_observed_event_drops_tool_call_delta() -> None:
    runtime = _runtime_for_normalization()

    normalized = normalize_observed_event(runtime, _observed_event("tool.call.delta"))

    assert normalized is None


@pytest.mark.parametrize(
    ("stream", "data", "saw_provider_progress", "expected_kind", "expected_provider_event_name"),
    [
        ("assistant", {"delta": "hello"}, False, "first_data", "assistant.delta"),
        ("assistant", {"text": "hello"}, False, "first_data", "assistant.message"),
        ("thinking", {"delta": "plan"}, False, "first_data", "thinking.delta"),
        ("assistant", {"text": "hello"}, True, "output_delta", "assistant.message"),
        (
            "tool",
            {"phase": "end", "status": "completed"},
            False,
            "tool_event",
            "tool.call.completed",
        ),
        ("tool", {"phase": "end", "status": "failed"}, False, "tool_event", "tool.call.failed"),
        ("tool", {"phase": "end", "status": "blocked"}, False, "tool_event", "tool.call.failed"),
        ("lifecycle", {"phase": "end"}, False, "response_completed", "run.completed"),
        (
            "lifecycle",
            {"phase": "end", "aborted": True, "stopReason": "rpc"},
            False,
            "response_failed",
            "run.cancelled",
        ),
        (
            "lifecycle",
            {"phase": "end", "stopReason": "timeout"},
            False,
            "response_failed",
            "run.timed_out",
        ),
    ],
)
def test_normalize_observed_event_maps_live_agent_stream_events(
    stream: str,
    data: dict[str, object],
    saw_provider_progress: bool,
    expected_kind: str,
    expected_provider_event_name: str,
) -> None:
    runtime = _runtime_for_normalization(has_seen_provider_progress=saw_provider_progress)

    normalized = normalize_observed_event(
        runtime,
        _agent_stream_observed_event(stream=stream, data=data),
    )

    assert normalized is not None
    assert normalized.event_kind == expected_kind
    assert normalized.provider_event_name == expected_provider_event_name


def test_normalize_observed_event_accepts_lowercased_session_key_for_agent_streams() -> None:
    runtime = ActiveOpenClawDispatchRuntime(
        task_id="task-normalization",
        dispatch_id="dispatch.root.01",
        attempt_id="attempt.root.01",
        session_key="agent:autoclaw-worker:gateway-session.dispatch.root.01.MixedCaseSuffix",
        run_id="run-live",
        lease=cast(OpenClawDispatchLaunchLease, None),
        session_factory=cast(async_sessionmaker, None),
    )

    normalized = normalize_observed_event(
        runtime,
        OpenClawObservedEvent.model_validate(
            {
                "event": "agent",
                "payload": {
                    "runId": "run-live",
                    "sessionKey": runtime.session_key.lower(),
                    "stream": "tool",
                    "ts": "2026-05-24T00:00:01+00:00",
                    "data": {"phase": "end", "status": "completed"},
                },
            }
        ),
    )

    assert normalized is not None
    assert normalized.event_kind == "tool_event"
    assert normalized.provider_event_name == "tool.call.completed"
    assert normalized.should_advance_liveness is True


def test_normalize_observed_event_treats_tool_activity_as_liveness() -> None:
    runtime = _runtime_for_normalization()

    normalized = normalize_observed_event(
        runtime,
        _agent_stream_observed_event(
            stream="tool",
            data={"phase": "start", "status": "running"},
        ),
    )

    assert normalized is not None
    assert normalized.event_kind == "tool_event"
    assert normalized.provider_event_name == "tool.call.started"
    assert normalized.should_advance_liveness is True


async def _send_current_openclaw_progress_stream(connection: ServerConnection) -> None:
    await _send_current_openclaw_handshake(connection)
    request = await recv_json(connection)
    assert request["method"] == "agent"
    run_id = "run-live"
    event_base = datetime.now(tz=UTC)
    await _send_agent_accepted_response(
        connection,
        request_id=request["id"],
        run_id=run_id,
        accepted_at=event_base - timedelta(seconds=1),
    )
    await _send_current_openclaw_event(
        connection,
        stream="assistant",
        data={"delta": "hello"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at=(event_base + timedelta(seconds=1)).isoformat(),
    )
    await _send_current_openclaw_event(
        connection,
        stream="tool",
        data={"phase": "end", "status": "completed"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at=(event_base + timedelta(seconds=2)).isoformat(),
    )
    await _send_current_openclaw_event(
        connection,
        stream="assistant",
        data={"text": "done"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at=(event_base + timedelta(seconds=3)).isoformat(),
    )
    await _send_current_openclaw_event(
        connection,
        stream="lifecycle",
        data={"phase": "end"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at=(event_base + timedelta(seconds=4)).isoformat(),
    )
    try:
        await connection.wait_closed()
    except ConnectionClosed:
        return


async def _send_current_openclaw_handshake(
    connection: ServerConnection,
) -> dict[str, object]:
    await send_json(connection, connect_challenge_fixture())
    connect_request = await recv_json(connection)
    hello_ok = hello_ok_fixture(
        device_token="device-token-test",
        events=["agent"],
    )
    hello_ok["id"] = connect_request["id"]
    await send_json(connection, hello_ok)
    return connect_request


async def _send_agent_accepted_response(
    connection: ServerConnection,
    *,
    request_id: object,
    run_id: str,
    accepted_at: datetime | None = None,
) -> None:
    accepted_at = accepted_at or datetime.now(tz=UTC)
    await send_json(
        connection,
        {
            "type": "res",
            "id": request_id,
            "ok": True,
            "payload": {
                "runId": run_id,
                "status": "accepted",
                "acceptedAt": accepted_at.isoformat(),
            },
        },
    )


async def _send_current_openclaw_event(
    connection: ServerConnection,
    *,
    stream: str,
    data: dict[str, object],
    run_id: str,
    session_key: object,
    occurred_at: str,
) -> None:
    await send_json(
        connection,
        {
            "type": "event",
            "event": "agent",
            "payload": {
                "runId": run_id,
                "sessionKey": session_key,
                "stream": stream,
                "ts": occurred_at,
                "data": data,
            },
        },
    )


@pytest.mark.asyncio
async def test_runtime_ingest_commits_provider_progress_from_current_openclaw_events(
    tmp_path: Path,
) -> None:
    task_id = "task_gateway_current_openclaw_event_progress"

    async with gateway_server(_send_current_openclaw_progress_stream) as base_url:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        compiler_version="gateway-current-openclaw-event-progress",
                    )

            snapshot = await wait_for_latest_dispatch_snapshot(
                runtime.session_factory,
                task_id=task_id,
                predicate=lambda current: (
                    len(current.provider_events) >= 4
                    and [event.event_kind for event in current.provider_events[:4]]
                    == [
                        "accepted",
                        "first_data",
                        "output_delta",
                        "response_completed",
                    ]
                    and current.delivery_state is not None
                    and current.delivery_state.last_provider_event_kind == "response_completed"
                    and current.delivery_state.last_provider_signal_at is not None
                    and current.dispatch.delivery_status == "provider_completed"
                ),
                max_cycles=200,
            )

    assert snapshot.delivery_state is not None
    assert [event.event_source for event in snapshot.provider_events[:4]] == [
        "adapter",
        "provider",
        "provider",
        "provider",
    ]
    assert [event.provider_event_name for event in snapshot.provider_events[1:4]] == [
        "assistant.delta",
        "assistant.message",
        "run.completed",
    ]
    task_events = await _load_provider_task_events(runtime.session_factory, task_id=task_id)
    _assert_current_openclaw_task_events(task_events, snapshot)
    assert (
        snapshot.delivery_state.last_provider_signal_at
        == snapshot.provider_events[1].provider_occurred_at
    )


async def _load_provider_task_events(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> list[TaskEventModel]:
    async with session_factory() as session:
        return list(
            await session.scalars(
                select(TaskEventModel)
                .where(
                    TaskEventModel.task_id == task_id,
                    TaskEventModel.event_type == "provider_event_normalized",
                )
                .order_by(TaskEventModel.event_seq.asc())
            )
        )


def _assert_current_openclaw_task_events(
    task_events: list[TaskEventModel],
    snapshot: DispatchGatewaySnapshot,
) -> None:
    assert [event.event_source for event in task_events[:4]] == [
        "adapter",
        "provider",
        "provider",
        "provider",
    ]
    assert [event.payload["event_kind"] for event in task_events[:4]] == [
        "accepted",
        "first_data",
        "output_delta",
        "response_completed",
    ]
    assert task_events[1].payload["provider_event_name"] == "assistant.delta"
    assert task_events[1].payload["transport_family"] == "openclaw_gateway_ws_rpc"
    assert task_events[1].payload["gateway_run_id"] == snapshot.dispatch.gateway_run_id
    assert task_events[1].payload["gateway_session_key"] == snapshot.dispatch.gateway_session_key


async def _send_openclaw_tool_delta_noise_stream(connection: ServerConnection) -> None:
    await _send_current_openclaw_handshake(connection)
    request = await recv_json(connection)
    assert request["method"] == "agent"
    run_id = "run-with-deltas"
    event_base = datetime.now(tz=UTC)
    await _send_agent_accepted_response(
        connection,
        request_id=request["id"],
        run_id=run_id,
        accepted_at=event_base - timedelta(seconds=1),
    )
    await _send_current_openclaw_event(
        connection,
        stream="tool",
        data={"phase": "start", "status": "running"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at=(event_base + timedelta(milliseconds=500)).isoformat(),
    )
    for offset_seconds in range(1, 6):
        await _send_current_openclaw_event(
            connection,
            stream="tool",
            data={"phase": "delta"},
            run_id=run_id,
            session_key=request["params"]["sessionKey"],
            occurred_at=(event_base + timedelta(seconds=offset_seconds)).isoformat(),
        )
    await _send_current_openclaw_event(
        connection,
        stream="tool",
        data={"phase": "end", "status": "completed"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at=(event_base + timedelta(seconds=6)).isoformat(),
    )
    await _send_current_openclaw_event(
        connection,
        stream="lifecycle",
        data={"phase": "end"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at=(event_base + timedelta(seconds=7)).isoformat(),
    )
    try:
        await connection.wait_closed()
    except ConnectionClosed:
        return


@pytest.mark.asyncio
async def test_runtime_ingest_prunes_tool_events_that_do_not_refresh_provider_signal(
    tmp_path: Path,
) -> None:
    task_id = "task_gateway_drops_tool_call_delta"

    async with gateway_server(_send_openclaw_tool_delta_noise_stream) as base_url:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        compiler_version="gateway-drops-tool-delta",
                    )

            snapshot = await wait_for_latest_dispatch_snapshot(
                runtime.session_factory,
                task_id=task_id,
                predicate=lambda current: (
                    current.dispatch.delivery_status == "provider_completed"
                    and len(current.provider_events) >= 3
                ),
                max_cycles=200,
            )

    provider_event_names = [event.provider_event_name for event in snapshot.provider_events]
    assert "tool.call.delta" not in provider_event_names
    assert "tool.call.completed" not in provider_event_names
    assert provider_event_names == [None, "tool.call.started", "run.completed"]


async def _send_stale_openclaw_replay_stream(connection: ServerConnection) -> None:
    await _send_current_openclaw_handshake(connection)
    request = await recv_json(connection)
    assert request["method"] == "agent"
    run_id = "run-stale-replay"
    event_base = datetime.now(tz=UTC) - timedelta(minutes=15)
    await _send_agent_accepted_response(
        connection,
        request_id=request["id"],
        run_id=run_id,
    )
    await _send_current_openclaw_event(
        connection,
        stream="tool",
        data={"phase": "end", "status": "completed"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at=(event_base + timedelta(seconds=1)).isoformat(),
    )
    await _send_current_openclaw_event(
        connection,
        stream="lifecycle",
        data={"phase": "end"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at=(event_base + timedelta(seconds=2)).isoformat(),
    )
    try:
        await connection.wait_closed()
    except ConnectionClosed:
        return


@pytest.mark.asyncio
async def test_runtime_ingest_keeps_stale_replay_out_of_provider_freshness(
    tmp_path: Path,
) -> None:
    task_id = "task_gateway_stale_replay_no_freshness"

    async with gateway_server(_send_stale_openclaw_replay_stream) as base_url:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        compiler_version="gateway-stale-replay-no-freshness",
                    )

            snapshot = await wait_for_latest_dispatch_snapshot(
                runtime.session_factory,
                task_id=task_id,
                predicate=lambda current: (
                    current.dispatch.delivery_status == "provider_completed"
                    and len(current.provider_events) >= 2
                ),
                max_cycles=200,
            )

    assert snapshot.delivery_state is not None
    assert snapshot.dispatch.delivery_status == "provider_completed"
    assert snapshot.delivery_state.last_provider_signal_at is None
    assert [event.provider_event_name for event in snapshot.provider_events] == [
        None,
        "run.completed",
    ]
