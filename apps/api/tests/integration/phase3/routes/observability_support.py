from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

from autoclaw.db import ProviderEventRecordModel
from autoclaw.runtime.effects import drive_runtime_once
from sqlalchemy import select
from tests.integration.phase3.routes.support import (
    Phase3RouteContext,
    SeededRouteTask,
)
from tests.integration.phase4b.support_state_shapes import (
    CONTINUITY_STATE_FIELDS,
    DELIVERY_STATE_FIELDS,
    WATCHDOG_STATE_FIELDS,
    assert_payload_shape,
    assert_provider_event_shape,
    load_json_payload,
    load_provider_event_payloads,
)

OBSERVABILITY_ROUTES = (
    (
        "delivery-state",
        "delivery_state",
        "delivery-state.json",
        "Latest task-scoped delivery-state projection.",
    ),
    (
        "continuity-state",
        "continuity_state",
        "continuity-state.json",
        "Latest task-scoped continuity-state projection.",
    ),
    (
        "watchdog-state",
        "watchdog_state",
        "watchdog-state.json",
        "Latest task-scoped watchdog-state projection.",
    ),
    (
        "provider-events",
        "provider_events",
        "provider-events.ndjson",
        "Normalized provider-event history for the selected task.",
    ),
)


def current_dispatch_history_entry(trace_json: dict[str, object]) -> dict[str, str]:
    return cast(list[dict[str, str]], trace_json["dispatch_history"])[0]


def dispatch_support_path(task_root: Path, dispatch_id: str, filename: str) -> Path:
    return task_root / "_runtime" / "dispatch" / dispatch_id / filename


async def wait_for_path(path: Path, *, task_id: str, max_wait_seconds: float = 5.0) -> None:
    deadline = asyncio.get_running_loop().time() + max_wait_seconds
    while asyncio.get_running_loop().time() < deadline:
        if await asyncio.to_thread(path.is_file):
            return
        await drive_runtime_once(task_id=task_id)
        await asyncio.sleep(0.05)
    raise TimeoutError(f"expected materialized path '{path}' within {max_wait_seconds:.2f}s")


async def wait_for_provider_event_payloads(
    path: Path,
    *,
    task_id: str,
    max_wait_seconds: float = 5.0,
) -> list[dict[str, object]]:
    deadline = asyncio.get_running_loop().time() + max_wait_seconds
    while asyncio.get_running_loop().time() < deadline:
        if await asyncio.to_thread(path.is_file):
            payloads = load_provider_event_payloads(path)
            if payloads:
                return payloads
        await drive_runtime_once(task_id=task_id)
        await asyncio.sleep(0.05)
    if await asyncio.to_thread(path.is_file):
        return load_provider_event_payloads(path)
    return []


async def wait_for_support_state_json(
    path: Path,
    *,
    task_id: str,
    predicate: Callable[[dict[str, object]], bool],
    max_wait_seconds: float = 5.0,
) -> dict[str, object]:
    deadline = asyncio.get_running_loop().time() + max_wait_seconds
    while asyncio.get_running_loop().time() < deadline:
        if await asyncio.to_thread(path.is_file):
            payload = cast(
                dict[str, object],
                json.loads(await asyncio.to_thread(path.read_text, encoding="utf-8")),
            )
            if predicate(payload):
                return payload
        await drive_runtime_once(task_id=task_id)
        await asyncio.sleep(0.05)
    raise AssertionError(f"support-state predicate did not pass for '{path}'")


def assert_provider_event_text_fields(
    event_payload: dict[str, object],
    *,
    dispatch_id: str,
    attempt_id: str,
    node_key: str,
) -> None:
    assert event_payload["dispatch_id"] == dispatch_id
    assert event_payload["attempt_id"] == attempt_id
    assert event_payload["event_no"] == 1
    assert event_payload["event_source"] == "adapter"
    assert event_payload["event_kind"] == "accepted"
    assert event_payload["provider_event_name"] is None
    assert event_payload["summary"] == (
        "Dispatch accepted and waiting for provider or adapter progress."
    )
    assert event_payload["provider_occurred_at"] is None
    assert event_payload["detail"] == f"Dispatch opened for node '{node_key}'."
    assert event_payload["observed_at"] is not None


async def observability_payloads(
    context: Phase3RouteContext,
    task: SeededRouteTask,
) -> dict[str, dict[str, object]]:
    payloads: dict[str, dict[str, object]] = {}
    for route_name, expected_kind, expected_name, expected_description in OBSERVABILITY_ROUTES:
        response = await context.client.get(
            f"/observability/tasks/{task.task_id}/{route_name}",
            headers=context.operator_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        payloads[expected_name] = payload
        assert payload["kind"] == expected_kind
        assert Path(payload["path"]).name == expected_name
        assert payload["description"] == expected_description
        path = Path(str(payload["path"]))
        await wait_for_path(path, task_id=task.task_id)
        if expected_name == "provider-events.ndjson":
            event_payloads = await wait_for_provider_event_payloads(
                path,
                task_id=task.task_id,
            )
            assert event_payloads
            for event_payload in event_payloads:
                assert_provider_event_shape(
                    event_payload,
                    dispatch_id_from_path=path.parent.name,
                )
            continue
        assert_payload_shape(
            load_json_payload(path),
            expected_fields={
                "delivery-state.json": DELIVERY_STATE_FIELDS,
                "continuity-state.json": CONTINUITY_STATE_FIELDS,
                "watchdog-state.json": WATCHDOG_STATE_FIELDS,
            }[expected_name],
            dispatch_id_from_path=path.parent.name,
        )
    return payloads


def _dispatch_state_payload(
    payload: dict[str, object],
    trace_json: dict[str, object],
    *,
    expected_fields: frozenset[str],
) -> tuple[dict[str, str], dict[str, object]]:
    dispatch_history_entry = current_dispatch_history_entry(trace_json)
    path = Path(str(payload["path"]))
    state_payload = load_json_payload(path)
    assert_payload_shape(
        state_payload,
        expected_fields=expected_fields,
        dispatch_id_from_path=path.parent.name,
    )
    return dispatch_history_entry, state_payload


def _assert_payload_values(
    payload: dict[str, object],
    expected_values: dict[str, object],
) -> None:
    assert {key: payload[key] for key in expected_values} == expected_values


def assert_delivery_payload(
    payload: dict[str, object],
    trace_json: dict[str, object],
    *,
    expected_node_key: str = "implementation_subtree",
    expected_previous_dispatch_id: str | None = "dispatch.task_2026_0044.root.01",
    expected_transport_state: str = "accepted",
    expected_last_provider_event_kind: str | None = None,
    expected_provider_final_status: str | None = None,
    expected_provider_error: str | None = None,
    expect_last_provider_signal_at: bool = False,
    expect_last_controller_terminal_at: bool = False,
) -> None:
    dispatch_history_entry, delivery_payload = _dispatch_state_payload(
        payload,
        trace_json,
        expected_fields=DELIVERY_STATE_FIELDS,
    )
    _assert_payload_values(
        delivery_payload,
        {
            "attempt_id": dispatch_history_entry["attempt_id"],
            "assignment_key": dispatch_history_entry["assignment_key"],
            "node_key": expected_node_key,
            "transport_family": "openclaw_gateway_ws_rpc",
            "transport_state": expected_transport_state,
            "last_provider_event_kind": expected_last_provider_event_kind,
            "provider_final_status": expected_provider_final_status,
            "provider_error": expected_provider_error,
            "previous_dispatch_id": expected_previous_dispatch_id,
            "superseded_by_dispatch_id": None,
            "last_controller_progress_at": None,
        },
    )
    assert (
        delivery_payload["last_provider_signal_at"] is not None
    ) is expect_last_provider_signal_at
    assert (
        delivery_payload["last_controller_terminal_at"] is not None
    ) is expect_last_controller_terminal_at
    assert delivery_payload["accepted_at"] is not None
    assert delivery_payload["prepared_at"] is not None
    assert delivery_payload["updated_at"] is not None


def assert_continuity_payload(
    payload: dict[str, object],
    trace_json: dict[str, object],
    *,
    expected_node_key: str = "implementation_subtree",
    expected_session_key_present: bool = True,
    expected_invalidation_reason: str | None = None,
) -> None:
    dispatch_history_entry, continuity_payload = _dispatch_state_payload(
        payload,
        trace_json,
        expected_fields=CONTINUITY_STATE_FIELDS,
    )
    _assert_payload_values(
        continuity_payload,
        {
            "attempt_id": dispatch_history_entry["attempt_id"],
            "assignment_key": dispatch_history_entry["assignment_key"],
            "node_key": expected_node_key,
            "session_key_present": expected_session_key_present,
            "invalidation_reason": expected_invalidation_reason,
        },
    )
    assert continuity_payload["updated_at"] is not None


def assert_watchdog_payload(
    payload: dict[str, object],
    trace_json: dict[str, object],
    *,
    expected_node_key: str = "implementation_subtree",
    expected_watchdog_state: str = "clear",
    expected_previous_dispatch_id: str | None = "dispatch.task_2026_0044.root.01",
    expected_current_watchdog_kind: str | None = None,
    expected_current_watchdog_reason: str | None = None,
    expected_recovery_action: str | None = None,
    expected_recovery_reason: str | None = None,
    expected_recovery_dispatch_id: str | None = None,
    expected_superseded_by_dispatch_id: str | None = None,
) -> None:
    dispatch_history_entry, watchdog_payload = _dispatch_state_payload(
        payload,
        trace_json,
        expected_fields=WATCHDOG_STATE_FIELDS,
    )
    _assert_payload_values(
        watchdog_payload,
        {
            "attempt_id": dispatch_history_entry["attempt_id"],
            "assignment_key": dispatch_history_entry["assignment_key"],
            "node_key": expected_node_key,
            "watchdog_state": expected_watchdog_state,
            "previous_dispatch_id": expected_previous_dispatch_id,
            "current_watchdog_kind": expected_current_watchdog_kind,
            "current_watchdog_reason": expected_current_watchdog_reason,
            "recovery_action": expected_recovery_action,
            "recovery_reason": expected_recovery_reason,
            "recovery_dispatch_id": expected_recovery_dispatch_id,
            "superseded_by_dispatch_id": expected_superseded_by_dispatch_id,
        },
    )
    assert watchdog_payload["classified_at"] is not None
    assert watchdog_payload["updated_at"] is not None


async def _provider_event_records(
    context: Phase3RouteContext,
    *,
    dispatch_id: str,
) -> list[ProviderEventRecordModel]:
    async with context.session_factory() as session:
        return list(
            await session.scalars(
                select(ProviderEventRecordModel)
                .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
                .order_by(ProviderEventRecordModel.event_no.asc())
            )
        )


def _assert_provider_event_record_and_projection(
    payload: dict[str, object],
    record: ProviderEventRecordModel,
    *,
    attempt_id: str,
    node_key: str,
) -> None:
    assert record.event_no == 1
    assert record.attempt_id == attempt_id
    assert record.event_source == "adapter"
    assert record.event_kind == "accepted"
    assert record.provider_event_name is None
    assert record.summary == "Dispatch accepted and waiting for provider or adapter progress."
    assert record.provider_occurred_at is None
    assert record.detail == f"Dispatch opened for node '{node_key}'."
    assert record.event_payload_json is None
    assert payload == {
        "event_no": record.event_no,
        "dispatch_id": record.dispatch_id,
        "attempt_id": record.attempt_id,
        "event_source": record.event_source,
        "event_kind": record.event_kind,
        "provider_event_name": record.provider_event_name,
        "summary": record.summary,
        "observed_at": record.occurred_at.isoformat(),
        "provider_occurred_at": None,
        "detail": record.detail,
    }


async def assert_provider_event_payloads(
    context: Phase3RouteContext,
    payload: dict[str, object],
    trace_json: dict[str, object],
    *,
    expected_node_key: str = "implementation_subtree",
    expect_terminal_completion: bool = False,
) -> None:
    dispatch_history_entry = current_dispatch_history_entry(trace_json)
    provider_events_path = Path(str(payload["path"]))
    dispatch_id = provider_events_path.parent.name
    attempt_id = dispatch_history_entry["attempt_id"]
    provider_event_payloads = load_provider_event_payloads(provider_events_path)
    assert provider_event_payloads
    event_payload = provider_event_payloads[0]
    assert_provider_event_shape(
        event_payload,
        dispatch_id_from_path=dispatch_id,
    )
    assert_provider_event_text_fields(
        event_payload,
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
        node_key=expected_node_key,
    )
    provider_event_records = await _provider_event_records(context, dispatch_id=dispatch_id)
    assert provider_event_records
    _assert_provider_event_record_and_projection(
        event_payload,
        provider_event_records[0],
        attempt_id=attempt_id,
        node_key=expected_node_key,
    )
    if not expect_terminal_completion:
        assert len(provider_event_payloads) == 1
        assert len(provider_event_records) == 1
        return
    terminal_payload = provider_event_payloads[-1]
    terminal_record = provider_event_records[-1]
    assert len(provider_event_payloads) >= 2
    assert len(provider_event_records) >= 2
    assert terminal_payload["dispatch_id"] == dispatch_id
    assert terminal_payload["attempt_id"] == attempt_id
    assert terminal_payload["event_kind"] == "response_completed"
    assert terminal_record.dispatch_id == dispatch_id
    assert terminal_record.attempt_id == attempt_id
    assert terminal_record.event_kind == "response_completed"
