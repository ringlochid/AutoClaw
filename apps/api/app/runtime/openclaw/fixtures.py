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
    payload: dict[str, Any] = {
        "type": "hello-ok",
        "protocol": protocol,
        "server": {
            "version": "2026.4.25",
            "connId": "conn-123",
        },
        "snapshot": {},
        "policy": policy,
        "auth": {
            "role": role,
            "scopes": scopes or ["operator.read", "operator.write"],
        },
        "features": {
            "methods": methods or ["agent", "agent.wait", "sessions.abort"],
            "events": events
            or [
                "agent",
                "response.delta",
                "tool.call",
                "run.started",
                "run.completed",
                "run.failed",
            ],
        },
    }
    if device_token is not None:
        payload["auth"]["deviceToken"] = device_token
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
) -> dict[str, Any]:
    if ended_at is None:
        ended_at = datetime.now(tz=UTC)
    if started_at is None:
        started_at = ended_at - timedelta(seconds=4)
    payload: dict[str, Any] = {
        "runId": run_id,
        "status": status,
        "startedAt": started_at.isoformat(),
        "endedAt": ended_at.isoformat(),
    }
    if status == "error":
        payload["error"] = {"message": "run failed"}
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
