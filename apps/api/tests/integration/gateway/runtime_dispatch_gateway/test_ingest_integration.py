from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from autoclaw.persistence import DispatchTurnModel, FlowModel, ProviderEventRecordModel
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.post_commit import drive_runtime_until
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.openclaw_gateway_support import gateway_server, recv_json, send_json
from tests.helpers.runtime_dispatch_support import current_open_dispatch_id
from tests.helpers.runtime_support import (
    assign_child,
    boundary,
    live_node_session_key_for_dispatch,
    load_live_dispatch,
    runtime_api_context,
    runtime_bootstrap_context,
    runtime_read_json,
)
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload
from tests.integration.gateway.dispatch_gateway_support import (
    override_gateway_base_url,
    wait_for_latest_dispatch_snapshot,
)
from tests.integration.gateway.runtime_dispatch_gateway.support import (
    send_basic_gateway_handshake,
    send_unsequenced_provider_delta_stream,
)
from websockets.asyncio.server import ServerConnection
from websockets.exceptions import ConnectionClosed


@pytest.mark.asyncio
async def test_runtime_ingest_persists_distinct_unsequenced_provider_deltas(
    tmp_path: Path,
) -> None:
    task_id = "task_phase4a_unsequenced_provider_deltas"

    async with gateway_server(send_unsequenced_provider_delta_stream) as base_url:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-4a-unsequenced-provider-deltas",
                    )

            snapshot = await wait_for_latest_dispatch_snapshot(
                runtime.session_factory,
                task_id=task_id,
                predicate=lambda current: (
                    len(current.provider_events) >= 4
                    and [event.event_kind for event in current.provider_events[:4]]
                    == ["accepted", "first_data", "output_delta", "response_completed"]
                    and current.delivery_state is not None
                    and current.delivery_state.last_provider_event_kind == "response_completed"
                    and current.dispatch.delivery_status == "provider_completed"
                ),
                timeout_seconds=10.0,
            )

    assert snapshot.delivery_state is not None
    assert snapshot.delivery_state.last_provider_event_kind == "response_completed"
    assert snapshot.dispatch.delivery_status == "provider_completed"


async def _dispatch_fenced_after_timeout_cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    dispatch_id: str,
) -> bool:
    async with session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        if dispatch is None:
            return False
        event_kinds = list(
            await session.scalars(
                select(ProviderEventRecordModel.event_kind)
                .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
                .order_by(ProviderEventRecordModel.event_no.asc())
            )
        )
        return (
            dispatch.control_state == "fenced"
            and dispatch.delivery_status == "transport_ambiguous"
            and event_kinds == ["accepted", "transport_timeout"]
        )


def terminal_ingest_timeout_handler() -> Any:
    run_counter = 0

    async def handler(connection: ServerConnection) -> None:
        nonlocal run_counter
        await send_basic_gateway_handshake(connection)
        root_run_id: str | None = None
        emitted_terminal = False
        while True:
            try:
                request = await recv_json(connection)
            except ConnectionClosed:
                return
            method = str(request["method"])
            if method == "agent":
                run_counter += 1
                active_run_id = f"run-{run_counter}"
                root_run_id = root_run_id or active_run_id
                await send_json(
                    connection,
                    {
                        "type": "res",
                        "id": request["id"],
                        "ok": True,
                        "payload": {
                            "runId": active_run_id,
                            "status": "accepted",
                            "acceptedAt": "2026-05-19T00:00:00+00:00",
                        },
                    },
                )
                continue
            if method == "agent.wait":
                request_run_id = str(request["params"]["runId"])
                if request_run_id == root_run_id and not emitted_terminal and run_counter >= 2:
                    emitted_terminal = True
                    await send_json(
                        connection,
                        {
                            "type": "event",
                            "event": "response.completed",
                            "payload": {
                                "runId": request_run_id,
                                "ts": "2026-05-19T00:00:01+00:00",
                            },
                        },
                    )
                    await asyncio.sleep(0.01)
                await send_json(
                    connection,
                    {
                        "type": "res",
                        "id": request["id"],
                        "ok": True,
                        "payload": {
                            "runId": request_run_id,
                            "status": "timeout",
                        },
                    },
                )
                continue
            if method == "sessions.abort":
                await send_json(
                    connection,
                    {
                        "type": "res",
                        "id": request["id"],
                        "ok": True,
                        "payload": {"status": "accepted"},
                    },
                )
                continue
            raise AssertionError(f"unexpected gateway method '{method}'")

    return handler


async def _root_dispatch_session_key(api: Any, *, task_id: str) -> tuple[str, str]:
    root_dispatch_id = await current_open_dispatch_id(
        api.session_factory,
        task_id=task_id,
    )
    async with api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        dispatch = await load_live_dispatch(session, task_id=task_id, flow=flow)
        root_session_key = await live_node_session_key_for_dispatch(
            session,
            dispatch=dispatch,
        )
        assert root_session_key is not None
    return root_dispatch_id, root_session_key


async def _yield_root_dispatch(
    api: Any,
    *,
    task_id: str,
    root_dispatch_id: str,
    root_session_key: str,
) -> None:
    runtime_read = await runtime_read_json(api.client, task_id)
    assign = await assign_child(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        child_node_key="implement_change",
        active_flow_revision_id=cast(
            str,
            runtime_read["active_flow_revision_id"],
        ),
    )
    assert assign.status_code == 200
    yielded = await boundary(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        boundary_name="yield",
    )
    assert yielded.status_code == 200
    async with api.session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
        assert dispatch is not None
        dispatch.control_deadline_at = dispatch.closed_at
        await session.commit()


async def _assert_root_dispatch_fenced_after_timeout_cleanup(
    api: Any,
    *,
    task_id: str,
    root_dispatch_id: str,
) -> None:
    await drive_runtime_until(
        lambda: _dispatch_fenced_after_timeout_cleanup(
            api.session_factory,
            dispatch_id=root_dispatch_id,
        ),
        task_id=task_id,
        max_cycles=60,
    )
    async with api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        dispatch = await session.get(DispatchTurnModel, root_dispatch_id)
        event_kinds = list(
            await session.scalars(
                select(ProviderEventRecordModel.event_kind)
                .where(ProviderEventRecordModel.dispatch_id == root_dispatch_id)
                .order_by(ProviderEventRecordModel.event_no.asc())
            )
        )
        assert flow is not None
        assert dispatch is not None
        assert dispatch.control_state == "fenced"
        assert dispatch.delivery_status == "transport_ambiguous"
        assert event_kinds == ["accepted", "transport_timeout"]


@pytest.mark.asyncio
async def test_boundary_timeout_cleanup_fences_root_dispatch_before_child_reopen(
    tmp_path: Path,
) -> None:
    task_id = "task_phase4a_terminal_ingest_beats_wait_timeout"

    try:
        async with gateway_server(terminal_ingest_timeout_handler()) as base_url:
            async with runtime_bootstrap_context(tmp_path) as runtime:
                with override_gateway_base_url(base_url):
                    async with runtime.session_factory() as session:
                        await launch_seeded_runtime(
                            session,
                            task_id=task_id,
                            task_root=runtime.paths.task_root,
                            task_compose=task_compose_payload("minimal-implement-change"),
                            compiler_version="phase-4a-terminal-ingest-fence",
                        )
                    async with runtime_api_context(runtime.paths.config_path) as api:
                        root_dispatch_id, root_session_key = await _root_dispatch_session_key(
                            api,
                            task_id=task_id,
                        )
                        await _yield_root_dispatch(
                            api,
                            task_id=task_id,
                            root_dispatch_id=root_dispatch_id,
                            root_session_key=root_session_key,
                        )
                        await _assert_root_dispatch_fenced_after_timeout_cleanup(
                            api,
                            task_id=task_id,
                            root_dispatch_id=root_dispatch_id,
                        )
    finally:
        await dispose_db_engine()
