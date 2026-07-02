from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn
from autoclaw.persistence import TaskEventModel
from autoclaw.persistence.session import _OPEN_SESSIONS_BY_LOOP
from autoclaw.runtime.contracts import TaskEventRecord
from autoclaw.runtime.task_events import append_task_event, encode_task_event_cursor
from sqlalchemy import func, select
from tests.integration.runtime.routes.support import (
    RuntimeRouteContext,
    SeededRouteTask,
    assign_child,
    launch_route_task,
    runtime_route_context,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def test_control_task_events_backfill_after_cursor_and_stop_at_snapshot_head(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_backfill",
            task_root_name="task-root",
        )
        launch_snapshot = await context.client.get(
            f"/control/tasks/{task.task_id}/snapshot",
            headers=context.operator_headers,
        )
        assert launch_snapshot.status_code == 200
        launch_head_event_id = launch_snapshot.json()["stream_head_event_id"]
        assert isinstance(launch_head_event_id, str)
        first = await append_route_task_event(context, task, label="first")
        second = await append_route_task_event(context, task, label="second")
        third = await append_route_task_event(context, task, label="third")
        fourth = await append_route_task_event(context, task, label="fourth")

        first_page = await context.client.get(
            f"/control/tasks/{task.task_id}/events",
            headers=context.operator_headers,
            params={"cursor": launch_head_event_id, "limit": 1},
        )
        assert first_page.status_code == 200
        assert [event["event_id"] for event in first_page.json()["items"]] == [first.event_id]
        assert first_page.json()["next_cursor"] is not None

        resumed = await context.client.get(
            f"/control/tasks/{task.task_id}/events",
            headers=context.operator_headers,
            params={
                "cursor": first_page.json()["next_cursor"],
                "through_event_id": third.event_id,
            },
        )
        assert resumed.status_code == 200
        resumed_json = resumed.json()
        assert [event["event_id"] for event in resumed_json["items"]] == [
            second.event_id,
            third.event_id,
        ]
        assert fourth.event_id not in {event["event_id"] for event in resumed_json["items"]}
        assert resumed_json["through_event_id"] == third.event_id
        assert resumed_json["next_cursor"] is None


async def test_control_task_events_require_reset_for_stale_cursor(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_reset",
            task_root_name="task-root",
        )
        await append_route_task_event(context, task, label="first")

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/events",
            headers=context.operator_headers,
            params={"cursor": encode_task_event_cursor("task-event.missing.00000001")},
        )

        assert response.status_code == 410
        assert response.json()["detail"]["code"] == "cursor_reset_required"


async def test_control_task_events_hide_legacy_provider_rows_but_accept_their_cursor(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_hide_provider",
            task_root_name="task-root",
        )
        launch_snapshot = await context.client.get(
            f"/control/tasks/{task.task_id}/snapshot",
            headers=context.operator_headers,
        )
        assert launch_snapshot.status_code == 200
        launch_head_event_id = launch_snapshot.json()["stream_head_event_id"]
        assert isinstance(launch_head_event_id, str)
        hidden_provider_event = await append_legacy_provider_task_event(
            context,
            task,
            event_type="provider_event_normalized",
            label="provider-hidden",
        )
        hidden_provider_resolution = await append_legacy_provider_task_event(
            context,
            task,
            event_type="provider_resolution_recorded",
            label="provider-resolution-hidden",
        )
        visible = await append_route_task_event(context, task, label="visible")

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/events",
            headers=context.operator_headers,
            params={"cursor": launch_head_event_id},
        )
        assert response.status_code == 200
        item_ids = [event["event_id"] for event in response.json()["items"]]
        assert hidden_provider_event.event_id not in item_ids
        assert hidden_provider_resolution.event_id not in item_ids
        assert visible.event_id in item_ids

        resumed = await context.client.get(
            f"/control/tasks/{task.task_id}/events",
            headers=context.operator_headers,
            params={"cursor": hidden_provider_resolution.event_id},
        )
        assert resumed.status_code == 200
        assert [event["event_id"] for event in resumed.json()["items"]] == [visible.event_id]


async def test_control_task_events_require_operator_auth_and_existing_task(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_auth",
            task_root_name="task-root",
        )

        unauthorized = await context.client.get(f"/control/tasks/{task.task_id}/events")
        assert unauthorized.status_code == 401
        assert unauthorized.json()["detail"]["code"] == "illegal_caller"

        missing = await context.client.get(
            "/control/tasks/task_missing/events",
            headers=context.operator_headers,
        )
        assert missing.status_code == 404
        assert missing.json()["detail"]["code"] == "missing_resource"


async def test_control_snapshot_returns_current_stream_head(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_snapshot_head",
            task_root_name="task-root",
        )
        head = await append_route_task_event(context, task, label="snapshot-head")

        control_task = await context.client.get(
            f"/control/tasks/{task.task_id}",
            headers=context.operator_headers,
        )
        control_snapshot = await context.client.get(
            f"/control/tasks/{task.task_id}/snapshot",
            headers=context.operator_headers,
        )
        control_trace = await context.client.get(
            f"/control/tasks/{task.task_id}/trace",
            headers=context.operator_headers,
        )
        operator_snapshot = await context.client.get(
            f"/operator/tasks/{task.task_id}/snapshot",
            headers=context.operator_headers,
        )

        assert control_task.status_code == 200
        assert control_snapshot.status_code == 200
        assert control_trace.status_code == 200
        assert operator_snapshot.status_code == 200
        assert control_task.json()["task_id"] == task.task_id
        assert control_trace.json()["task_id"] == task.task_id
        assert control_snapshot.json()["stream_head_event_id"] == head.event_id
        assert operator_snapshot.json()["stream_head_event_id"] == head.event_id


async def test_control_task_event_stream_delivers_live_child_assignment_staged_event(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_runtime_event_stream_live",
            task_root_name="task-root",
        )

        async with live_control_stream_client(context) as stream_client:
            reader = asyncio.create_task(
                read_task_event_stream(
                    stream_client,
                    context,
                    task,
                    expected_count=1,
                )
            )
            await asyncio.sleep(0.2)
            assign_response = await assign_child(context, task)
            assert assign_response.status_code == 200
            frames = await asyncio.wait_for(reader, timeout=8)

        assert [frame["event"] for frame in frames] == ["child_assignment_staged"]
        assert frames[0]["id"] == frames[0]["data"]["event_id"]
        assert frames[0]["data"]["dispatch_id"] == task.current_open_dispatch_id
        payload = frames[0]["data"]["payload"]
        assert payload["target_node_key"] == "implementation_subtree"
        assert payload["target_assignment_key"]
        assert payload["target_attempt_id"]
        assert payload["assignment_summary"] == "Start the implementation subtree."
        assert payload["child_assignment_ref"]["path"].endswith("assignment.md")
        assert payload["workflow_manifest_ref"]["path"].endswith("workflow-manifest.md")
        assert payload["latest_checkpoint_ref"] is None
        assert payload["transient_refs"] == []


async def test_control_task_event_stream_delivers_live_multiple_event_families(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_runtime_event_stream_multiple_families",
            task_root_name="task-root",
        )

        async with live_control_stream_client(context) as stream_client:
            reader = asyncio.create_task(
                read_task_event_stream(
                    stream_client,
                    context,
                    task,
                    expected_count=2,
                )
            )
            await asyncio.sleep(0.2)
            first = await append_route_task_event(context, task, label="checkpoint-live")
            second = await append_route_task_event(
                context,
                task,
                label="human-live",
                event_type="human_request_opened",
                event_source="node",
                payload={"request_id": "human-request.live"},
            )
            frames = await asyncio.wait_for(reader, timeout=8)

        assert [frame["event"] for frame in frames] == [
            "checkpoint_recorded",
            "human_request_opened",
        ]
        assert [frame["id"] for frame in frames] == [first.event_id, second.event_id]
        assert frames[0]["data"]["payload"]["label"] == "checkpoint-live"
        assert frames[1]["data"]["payload"] == {"request_id": "human-request.live"}


async def test_control_task_event_stream_replays_after_cursor_then_tails_live_events(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_stream_replay",
            task_root_name="task-root",
        )
        first = await append_route_task_event(context, task, label="first")
        second = await append_route_task_event(context, task, label="second")
        third = await append_route_task_event(context, task, label="third")

        async with live_control_stream_client(context) as stream_client:
            reader = asyncio.create_task(
                read_task_event_stream(
                    stream_client,
                    context,
                    task,
                    params={"cursor": first.event_id},
                    expected_count=3,
                )
            )
            await asyncio.sleep(0.2)
            fourth = await append_route_task_event(context, task, label="fourth")

            frames = await asyncio.wait_for(reader, timeout=8)
        assert [frame["id"] for frame in frames] == [
            second.event_id,
            third.event_id,
            fourth.event_id,
        ]
        assert [frame["event"] for frame in frames] == [
            "checkpoint_recorded",
            "checkpoint_recorded",
            "checkpoint_recorded",
        ]
        assert [frame["data"]["payload"]["label"] for frame in frames] == [
            "second",
            "third",
            "fourth",
        ]


async def test_control_task_event_stream_accepts_last_event_id_resume(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_stream_header",
            task_root_name="task-root",
        )
        first = await append_route_task_event(context, task, label="first")
        second = await append_route_task_event(context, task, label="second")

        async with live_control_stream_client(context) as stream_client:
            frames = await read_task_event_stream(
                stream_client,
                context,
                task,
                headers={"Last-Event-ID": first.event_id},
                expected_count=1,
            )

        assert [frame["id"] for frame in frames] == [second.event_id]
        assert frames[0]["data"]["event_id"] == second.event_id


async def test_control_task_event_stream_rejects_conflicting_resume_inputs(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_stream_conflict",
            task_root_name="task-root",
        )
        first = await append_route_task_event(context, task, label="first")
        second = await append_route_task_event(context, task, label="second")

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/events/stream",
            headers={**context.operator_headers, "Last-Event-ID": second.event_id},
            params={"cursor": first.event_id},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "invalid_request_shape"


async def test_control_task_event_stream_requires_reset_before_opening_stale_cursor(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_stream_reset",
            task_root_name="task-root",
        )
        await append_route_task_event(context, task, label="first")

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/events/stream",
            headers=context.operator_headers,
            params={"cursor": encode_task_event_cursor("task-event.missing.00000001")},
        )

        assert response.status_code == 410
        assert response.json()["detail"]["code"] == "cursor_reset_required"


async def test_control_task_event_stream_starts_from_current_head_without_cursor(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_stream_head",
            task_root_name="task-root",
        )
        historical = await append_route_task_event(context, task, label="historical")

        async with live_control_stream_client(context) as stream_client:
            reader = asyncio.create_task(
                read_task_event_stream(
                    stream_client,
                    context,
                    task,
                    expected_count=1,
                )
            )
            await asyncio.sleep(0.2)
            live = await append_route_task_event(context, task, label="live")

            frames = await asyncio.wait_for(reader, timeout=8)
        assert [frame["id"] for frame in frames] == [live.event_id]
        assert historical.event_id not in {frame["id"] for frame in frames}
        assert frames[0]["data"]["payload"]["label"] == "live"


async def test_control_task_event_stream_releases_preflight_session_while_open(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_event_stream_session",
            task_root_name="task-root",
        )
        await append_route_task_event(context, task, label="head")
        baseline_counts = open_runtime_session_counts()

        async with live_control_stream_client(context) as stream_client:
            async with stream_client.stream(
                "GET",
                f"/control/tasks/{task.task_id}/events/stream",
                headers=context.operator_headers,
            ) as response:
                assert response.status_code == 200
                await assert_runtime_sessions_return_to_baseline(baseline_counts)


async def append_route_task_event(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    label: str,
    event_type: str = "checkpoint_recorded",
    event_source: str = "controller",
    payload: dict[str, Any] | None = None,
) -> TaskEventRecord:
    async with context.session_factory() as session:
        event = await append_task_event(
            session,
            task_id=task.task_id,
            event_type=event_type,
            event_source=event_source,
            payload={"label": label} if payload is None else payload,
        )
        await session.commit()
        return event


async def append_legacy_provider_task_event(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    event_type: str,
    label: str,
) -> TaskEventModel:
    async with context.session_factory() as session:
        event_seq = int(
            await session.scalar(
                select(func.max(TaskEventModel.event_seq)).where(
                    TaskEventModel.task_id == task.task_id
                )
            )
            or 0
        ) + 1
        row = TaskEventModel(
            event_id=f"task-event.{task.task_id}.legacy-provider.{event_seq:08d}",
            event_seq=event_seq,
            task_id=task.task_id,
            event_type=event_type,
            event_source="provider",
            occurred_at=datetime(2026, 6, 24, 17, 0, tzinfo=UTC),
            flow_revision_id=task.active_flow_revision_id,
            dispatch_id=task.current_open_dispatch_id,
            attempt_id=None,
            node_key=None,
            actor_ref=None,
            payload={"label": label},
            prev_event_hash=None,
            event_hash=f"sha256:legacy-provider-{event_seq}",
        )
        session.add(row)
        await session.commit()
        return row


@asynccontextmanager
async def live_control_stream_client(
    context: RuntimeRouteContext,
) -> AsyncIterator[httpx.AsyncClient]:
    port = reserve_local_port()
    server = uvicorn.Server(
        uvicorn.Config(
            context.app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            log_level="warning",
        )
    )
    server_task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.05)
    else:
        raise TimeoutError("local control stream server did not start")
    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
            yield client
    finally:
        server.should_exit = True
        await asyncio.wait_for(server_task, timeout=5)


def reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def open_runtime_session_counts() -> dict[int, int]:
    return {loop_id: len(tuple(sessions)) for loop_id, sessions in _OPEN_SESSIONS_BY_LOOP.items()}


async def assert_runtime_sessions_return_to_baseline(
    baseline_counts: dict[int, int],
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 3
    latest_counts: dict[int, int] = {}
    while loop.time() < deadline:
        latest_counts = open_runtime_session_counts()
        if all(
            count <= baseline_counts.get(loop_id, 0) for loop_id, count in latest_counts.items()
        ):
            return
        await asyncio.sleep(0.05)
    assert latest_counts == baseline_counts


async def read_task_event_stream(
    stream_client: httpx.AsyncClient,
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    expected_count: int,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    request_headers = dict(context.operator_headers)
    if headers:
        request_headers.update(headers)
    frames: list[dict[str, Any]] = []
    current_frame: dict[str, Any] = {}

    async with stream_client.stream(
        "GET",
        f"/control/tasks/{task.task_id}/events/stream",
        headers=request_headers,
        params=params,
    ) as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line == "":
                if current_frame:
                    frames.append(current_frame)
                    if len(frames) == expected_count:
                        return frames
                    current_frame = {}
                continue
            field, _, value = line.partition(": ")
            if field == "data":
                current_frame[field] = json.loads(value)
            else:
                current_frame[field] = value
    return frames
