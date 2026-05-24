from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.runtime.openclaw.protocol import OPENCLAW_PROTOCOL_VERSION


def connect_challenge_fixture() -> dict[str, Any]:
    return {
        "type": "event",
        "event": "connect.challenge",
        "payload": {"nonce": "nonce-123", "ts": 1737264000000},
    }


def hello_ok_fixture(
    *,
    device_token: str | None = "device-token-123",
    protocol: int = OPENCLAW_PROTOCOL_VERSION,
    role: str = "operator",
    scopes: list[str] | None = None,
    methods: list[str] | None = None,
    events: list[str] | None = None,
    plugin_surface_urls: dict[str, str] | None = None,
    tick_interval_ms: int = 15000,
    max_payload: int | None = 262144,
    max_buffered_bytes: int | None = 524288,
) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "tickIntervalMs": tick_interval_ms,
    }
    if max_payload is not None:
        policy["maxPayload"] = max_payload
    if max_buffered_bytes is not None:
        policy["maxBufferedBytes"] = max_buffered_bytes
    resolved_scopes = scopes if scopes is not None else ["operator.read", "operator.write"]
    resolved_methods = methods if methods is not None else ["agent", "agent.wait", "sessions.abort"]
    resolved_events = (
        events
        if events is not None
        else [
            "agent",
            "sessions.changed",
        ]
    )
    payload: dict[str, Any] = {
        "type": "hello-ok",
        "protocol": protocol,
        "server": {
            "version": "2026.5.12",
            "connId": "conn-123",
        },
        "snapshot": {},
        "policy": policy,
        "auth": {
            "role": role,
            "scopes": resolved_scopes,
        },
        "features": {
            "methods": resolved_methods,
            "events": resolved_events,
        },
    }
    if device_token is not None:
        payload["auth"]["deviceToken"] = device_token
    if plugin_surface_urls is not None:
        payload["pluginSurfaceUrls"] = plugin_surface_urls
    return {
        "type": "res",
        "id": "connect-1",
        "ok": True,
        "payload": payload,
    }


def auth_token_mismatch_fixture() -> dict[str, Any]:
    return {
        "type": "res",
        "id": "connect-1",
        "ok": False,
        "error": {
            "message": "shared token mismatch",
            "details": {
                "code": "AUTH_TOKEN_MISMATCH",
                "canRetryWithDeviceToken": True,
                "recommendedNextStep": "retry_with_device_token",
            },
        },
    }


def agent_accepted_fixture(
    *,
    accepted_at: datetime | None = None,
) -> dict[str, Any]:
    if accepted_at is None:
        accepted_at = datetime.now(tz=UTC)
    return {
        "type": "res",
        "id": "agent-1",
        "ok": True,
        "payload": {
            "runId": "run-123",
            "status": "accepted",
            "acceptedAt": accepted_at.isoformat(),
        },
    }


def agent_wait_fixture(
    *,
    run_id: str = "run-123",
    status: str = "ok",
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    error: dict[str, Any] | str | None = None,
    stop_reason: str | None = None,
    liveness_state: str | None = None,
    aborted: bool | None = None,
    yielded: bool | None = None,
) -> dict[str, Any]:
    include_timestamps = (
        status != "timeout"
        or started_at is not None
        or ended_at is not None
        or error is not None
        or stop_reason is not None
        or liveness_state is not None
        or aborted is not None
        or yielded is not None
    )
    payload: dict[str, Any] = {"runId": run_id, "status": status}
    if error is None and status == "error":
        error = {"message": "run failed"}
    if include_timestamps:
        if ended_at is None:
            ended_at = datetime.now(tz=UTC)
        if started_at is None:
            started_at = ended_at - timedelta(seconds=4)
        payload["startedAt"] = started_at.isoformat()
        payload["endedAt"] = ended_at.isoformat()
    if error is not None:
        payload["error"] = error
    if stop_reason is not None:
        payload["stopReason"] = stop_reason
    if liveness_state is not None:
        payload["livenessState"] = liveness_state
    if aborted is not None:
        payload["aborted"] = aborted
    if yielded is not None:
        payload["yielded"] = yielded
    return {
        "type": "res",
        "id": "wait-1",
        "ok": True,
        "payload": payload,
    }


def sessions_abort_fixture() -> dict[str, Any]:
    return {
        "type": "res",
        "id": "abort-1",
        "ok": True,
        "payload": {"status": "accepted"},
    }


__all__ = [
    "agent_accepted_fixture",
    "agent_wait_fixture",
    "auth_token_mismatch_fixture",
    "connect_challenge_fixture",
    "hello_ok_fixture",
    "sessions_abort_fixture",
]
