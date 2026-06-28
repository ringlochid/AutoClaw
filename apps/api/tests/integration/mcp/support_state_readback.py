from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.helpers.support_state_shapes import (
    assert_continuity_state_shape,
    assert_delivery_state_shape,
    assert_provider_event_shape,
    assert_watchdog_state_shape,
    load_json_payload,
    load_provider_event_payloads,
)
from tests.integration.mcp.support import call_tool_structured


async def load_support_state_refs(
    session: Any,
    *,
    task_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    trace = await call_tool_structured(
        session,
        "get_operator_trace",
        {"task_id": task_id, "scope": "current"},
    )
    delivery_ref = await call_tool_structured(
        session,
        "get_delivery_state_ref",
        {"task_id": task_id},
    )
    continuity_ref = await call_tool_structured(
        session,
        "get_continuity_state_ref",
        {"task_id": task_id},
    )
    watchdog_ref = await call_tool_structured(
        session,
        "get_watchdog_state_ref",
        {"task_id": task_id},
    )
    provider_events_ref = await call_tool_structured(
        session,
        "get_provider_events_ref",
        {"task_id": task_id},
    )
    return trace, delivery_ref, continuity_ref, watchdog_ref, provider_events_ref


def assert_support_state_ref_filenames(
    *,
    delivery_ref: dict[str, Any],
    continuity_ref: dict[str, Any],
    watchdog_ref: dict[str, Any],
    provider_events_ref: dict[str, Any],
) -> None:
    assert Path(str(delivery_ref["path"])).name == "delivery-state.json"
    assert Path(str(continuity_ref["path"])).name == "continuity-state.json"
    assert Path(str(watchdog_ref["path"])).name == "watchdog-state.json"
    assert Path(str(provider_events_ref["path"])).name == "provider-events.ndjson"


def assert_support_state_ref_payloads(
    *,
    delivery_ref: dict[str, Any],
    continuity_ref: dict[str, Any],
    watchdog_ref: dict[str, Any],
    provider_events_ref: dict[str, Any],
) -> None:
    delivery_path = Path(str(delivery_ref["path"]))
    continuity_path = Path(str(continuity_ref["path"]))
    watchdog_path = Path(str(watchdog_ref["path"]))
    provider_events_path = Path(str(provider_events_ref["path"]))
    delivery_payload = load_json_payload(delivery_path)
    continuity_payload = load_json_payload(continuity_path)
    watchdog_payload = load_json_payload(watchdog_path)
    provider_events = load_provider_event_payloads(provider_events_path)

    assert_delivery_state_shape(
        delivery_payload,
        dispatch_id_from_path=delivery_path.parent.name,
    )
    assert_continuity_state_shape(
        continuity_payload,
        dispatch_id_from_path=continuity_path.parent.name,
    )
    assert_watchdog_state_shape(
        watchdog_payload,
        dispatch_id_from_path=watchdog_path.parent.name,
    )
    assert provider_events
    for event_payload in provider_events:
        assert_provider_event_shape(
            event_payload,
            dispatch_id_from_path=provider_events_path.parent.name,
        )


__all__ = [
    "assert_support_state_ref_filenames",
    "assert_support_state_ref_payloads",
    "load_support_state_refs",
]
