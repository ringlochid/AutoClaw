from __future__ import annotations

import json
from pathlib import Path
from typing import cast

_COMMON_STATE_FIELDS = frozenset(
    "dispatch_id attempt_id assignment_key node_key updated_at".split()
)
DELIVERY_STATE_FIELDS = _COMMON_STATE_FIELDS | frozenset(
    """
    transport_family transport_state
    last_provider_event_kind provider_final_status provider_error
    previous_dispatch_id superseded_by_dispatch_id prepared_at accepted_at
    last_provider_signal_at last_controller_progress_at last_controller_terminal_at
    """.split()
)
CONTINUITY_STATE_FIELDS = _COMMON_STATE_FIELDS | frozenset(
    "session_key_present invalidation_reason".split()
)
WATCHDOG_STATE_FIELDS = _COMMON_STATE_FIELDS | frozenset(
    """
    watchdog_state current_watchdog_kind current_watchdog_reason recovery_action
    recovery_reason recovery_dispatch_id previous_dispatch_id
    superseded_by_dispatch_id classified_at
    """.split()
)
PROVIDER_EVENT_FIELDS = frozenset(
    """
    event_no dispatch_id attempt_id event_source event_kind provider_event_name
    summary observed_at provider_occurred_at detail
    """.split()
)


def load_json_payload(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def load_provider_event_payloads(path: Path) -> list[dict[str, object]]:
    return [
        cast(dict[str, object], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def assert_payload_shape(
    payload: dict[str, object],
    *,
    expected_fields: frozenset[str],
    dispatch_id_from_path: str,
    forbid_event_payload_json: bool = False,
) -> None:
    assert set(payload) == expected_fields
    assert not forbid_event_payload_json or "event_payload_json" not in payload
    assert payload["dispatch_id"] == dispatch_id_from_path


def assert_delivery_state_shape(
    payload: dict[str, object],
    *,
    dispatch_id_from_path: str,
) -> None:
    assert_payload_shape(
        payload,
        expected_fields=DELIVERY_STATE_FIELDS,
        dispatch_id_from_path=dispatch_id_from_path,
    )


def assert_continuity_state_shape(
    payload: dict[str, object],
    *,
    dispatch_id_from_path: str,
) -> None:
    assert_payload_shape(
        payload,
        expected_fields=CONTINUITY_STATE_FIELDS,
        dispatch_id_from_path=dispatch_id_from_path,
    )


def assert_watchdog_state_shape(
    payload: dict[str, object],
    *,
    dispatch_id_from_path: str,
) -> None:
    assert_payload_shape(
        payload,
        expected_fields=WATCHDOG_STATE_FIELDS,
        dispatch_id_from_path=dispatch_id_from_path,
    )


def assert_provider_event_shape(
    event_payload: dict[str, object],
    *,
    dispatch_id_from_path: str,
) -> None:
    assert_payload_shape(
        event_payload,
        expected_fields=PROVIDER_EVENT_FIELDS,
        dispatch_id_from_path=dispatch_id_from_path,
        forbid_event_payload_json=True,
    )


__all__ = [
    "CONTINUITY_STATE_FIELDS",
    "DELIVERY_STATE_FIELDS",
    "PROVIDER_EVENT_FIELDS",
    "WATCHDOG_STATE_FIELDS",
    "assert_continuity_state_shape",
    "assert_delivery_state_shape",
    "assert_payload_shape",
    "assert_provider_event_shape",
    "assert_watchdog_state_shape",
    "load_json_payload",
    "load_provider_event_payloads",
]
