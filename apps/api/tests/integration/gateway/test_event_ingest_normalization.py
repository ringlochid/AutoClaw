from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from autoclaw.integrations.openclaw.gateway import OpenClawObservedEvent
from autoclaw.integrations.openclaw.gateway.fixtures import (
    connect_challenge_fixture,
    hello_ok_fixture,
)
from autoclaw.runtime.dispatch.openclaw.event_ingest import (
    normalize_observed_event,
)
from autoclaw.runtime.dispatch.openclaw.models import (
    ActiveOpenClawDispatchRuntime,
    OpenClawDispatchLaunchLease,
)
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.helpers.openclaw_gateway_support import gateway_server, recv_json, send_json
from tests.helpers.runtime_support import runtime_bootstrap_context
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload
from tests.integration.gateway.dispatch_gateway_support import (
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
        ("tool.call.delta", False, "tool_event"),
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
    await _send_agent_accepted_response(connection, request_id=request["id"], run_id=run_id)
    await _send_current_openclaw_event(
        connection,
        stream="assistant",
        data={"delta": "hello"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at="2026-05-24T00:00:01+00:00",
    )
    await _send_current_openclaw_event(
        connection,
        stream="tool",
        data={"phase": "end", "status": "completed"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at="2026-05-24T00:00:02+00:00",
    )
    await _send_current_openclaw_event(
        connection,
        stream="assistant",
        data={"text": "done"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at="2026-05-24T00:00:03+00:00",
    )
    await _send_current_openclaw_event(
        connection,
        stream="lifecycle",
        data={"phase": "end"},
        run_id=run_id,
        session_key=request["params"]["sessionKey"],
        occurred_at="2026-05-24T00:00:04+00:00",
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
) -> None:
    await send_json(
        connection,
        {
            "type": "res",
            "id": request_id,
            "ok": True,
            "payload": {
                "runId": run_id,
                "status": "accepted",
                "acceptedAt": "2026-05-24T00:00:00+00:00",
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
                    len(current.provider_events) >= 5
                    and [event.event_kind for event in current.provider_events[:5]]
                    == [
                        "accepted",
                        "first_data",
                        "tool_event",
                        "output_delta",
                        "response_completed",
                    ]
                    and current.delivery_state is not None
                    and current.delivery_state.last_provider_event_kind == "response_completed"
                    and current.delivery_state.last_provider_signal_at is not None
                    and current.dispatch.delivery_status == "provider_completed"
                ),
                timeout_seconds=10.0,
            )

    assert snapshot.delivery_state is not None
    assert [event.event_source for event in snapshot.provider_events[:5]] == [
        "adapter",
        "provider",
        "provider",
        "provider",
        "provider",
    ]
    assert [event.provider_event_name for event in snapshot.provider_events[1:5]] == [
        "assistant.delta",
        "tool.call.completed",
        "assistant.message",
        "run.completed",
    ]
