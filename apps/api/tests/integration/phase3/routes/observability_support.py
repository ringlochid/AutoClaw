from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TypedDict, cast

from app.db import ProviderEventRecordModel
from app.runtime.effects import wait_for_runtime_effects
from sqlalchemy import select
from tests.integration.phase3.routes.support import (
    Phase3RouteContext,
    SeededRouteTask,
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


class DispatchHistoryEntry(TypedDict):
    attempt_id: str
    assignment_key: str


def current_dispatch_history_entry(trace_json: dict[str, object]) -> DispatchHistoryEntry:
    dispatch_history = cast(list[DispatchHistoryEntry], trace_json["dispatch_history"])
    return dispatch_history[0]


async def wait_for_path(path: Path, *, task_id: str, max_wait_seconds: float = 5.0) -> None:
    deadline = asyncio.get_running_loop().time() + max_wait_seconds
    while asyncio.get_running_loop().time() < deadline:
        if await asyncio.to_thread(path.is_file):
            return
        await wait_for_runtime_effects(
            task_id=task_id,
            max_wait_seconds=min(0.5, max_wait_seconds),
        )
        await asyncio.sleep(0.05)
    raise TimeoutError(f"expected materialized path '{path}' within {max_wait_seconds:.2f}s")


def assert_provider_event_text_fields(
    event_payload: dict[str, object],
    *,
    dispatch_id: str,
    attempt_id: str,
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
    assert event_payload["detail"] == (
        "Dispatch opened for node 'implementation_subtree' with send mode 'full_prompt'."
    )
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
        await wait_for_path(Path(str(payload["path"])), task_id=task.task_id)
    return payloads


def assert_delivery_payload(
    payload: dict[str, object],
    trace_json: dict[str, object],
) -> None:
    dispatch_history_entry = current_dispatch_history_entry(trace_json)
    delivery_path = Path(str(payload["path"]))
    delivery_payload = json.loads(delivery_path.read_text(encoding="utf-8"))
    assert set(delivery_payload) == {
        "dispatch_id",
        "attempt_id",
        "assignment_key",
        "node_key",
        "transport_family",
        "transport_state",
        "controller_observation_state",
        "last_provider_event_kind",
        "provider_final_status",
        "provider_error",
        "send_mode",
        "previous_dispatch_id",
        "superseded_by_dispatch_id",
        "prepared_at",
        "accepted_at",
        "last_provider_signal_at",
        "last_controller_progress_at",
        "last_controller_terminal_at",
        "updated_at",
    }
    assert delivery_payload["dispatch_id"] == delivery_path.parent.name
    assert delivery_payload["attempt_id"] == dispatch_history_entry["attempt_id"]
    assert delivery_payload["assignment_key"] == dispatch_history_entry["assignment_key"]
    assert delivery_payload["node_key"] == "implementation_subtree"
    assert delivery_payload["transport_family"] == "phase3_local_runtime"
    assert delivery_payload["transport_state"] == "accepted"
    assert delivery_payload["controller_observation_state"] == "live"
    assert delivery_payload["last_provider_event_kind"] is None
    assert delivery_payload["provider_final_status"] is None
    assert delivery_payload["provider_error"] is None
    assert delivery_payload["send_mode"] == "full_prompt"
    assert delivery_payload["previous_dispatch_id"] == "dispatch.task_2026_0044.root.01"
    assert delivery_payload["superseded_by_dispatch_id"] is None
    assert delivery_payload["accepted_at"] is not None
    assert delivery_payload["prepared_at"] is not None
    assert delivery_payload["last_provider_signal_at"] is None
    assert delivery_payload["last_controller_progress_at"] is None
    assert delivery_payload["last_controller_terminal_at"] is None
    assert delivery_payload["updated_at"] is not None


async def _provider_event_payloads(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (await asyncio.to_thread(path.read_text, encoding="utf-8")).splitlines()
        if line.strip()
    ]


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


def _assert_provider_event_record(
    record: ProviderEventRecordModel,
    *,
    attempt_id: str,
) -> None:
    assert record.event_no == 1
    assert record.attempt_id == attempt_id
    assert record.event_source == "adapter"
    assert record.event_kind == "accepted"
    assert record.provider_event_name is None
    assert record.summary == "Dispatch accepted and waiting for provider or adapter progress."
    assert record.provider_occurred_at is None
    assert record.detail == (
        "Dispatch opened for node 'implementation_subtree' with send mode 'full_prompt'."
    )
    assert record.event_payload_json == {
        "transport_family": "phase3_local_runtime",
        "send_mode": "full_prompt",
    }


def _assert_provider_event_projection(
    payload: dict[str, object],
    record: ProviderEventRecordModel,
) -> None:
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
) -> None:
    dispatch_history_entry = current_dispatch_history_entry(trace_json)
    provider_events_path = Path(str(payload["path"]))
    dispatch_id = provider_events_path.parent.name
    attempt_id = dispatch_history_entry["attempt_id"]
    provider_event_payloads = await _provider_event_payloads(provider_events_path)
    assert len(provider_event_payloads) == 1
    event_payload = provider_event_payloads[0]
    assert set(event_payload) == {
        "event_no",
        "dispatch_id",
        "attempt_id",
        "event_source",
        "event_kind",
        "provider_event_name",
        "summary",
        "observed_at",
        "provider_occurred_at",
        "detail",
    }
    assert "event_payload_json" not in event_payload
    assert_provider_event_text_fields(
        event_payload,
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
    )
    provider_event_records = await _provider_event_records(context, dispatch_id=dispatch_id)
    assert len(provider_event_records) == 1
    provider_event_record = provider_event_records[0]
    _assert_provider_event_record(provider_event_record, attempt_id=attempt_id)
    _assert_provider_event_projection(event_payload, provider_event_record)
