from __future__ import annotations

from autoclaw.integrations.openclaw.gateway.contracts import OpenClawWaitStatus
from autoclaw.integrations.openclaw.gateway.protocol import OpenClawAgentWaitPayload

TERMINAL_CANCEL_WAIT_STATUSES = frozenset({"aborted", "cancelled", "canceled", "killed"})
TERMINAL_CANCEL_STOP_REASONS = frozenset(
    {"aborted", "cancelled", "canceled", "killed", "rpc", "user"}
)
TERMINAL_TIMEOUT_STOP_REASONS = frozenset({"timeout", "timed_out"})
SUCCESS_WAIT_STATUSES = frozenset({"ok", "completed", "succeeded"})


def normalize_gateway_wait_status(payload: OpenClawAgentWaitPayload) -> OpenClawWaitStatus:
    status = payload.status.lower()
    stop_reason = "" if payload.stop_reason is None else payload.stop_reason.lower()
    if status in SUCCESS_WAIT_STATUSES:
        return OpenClawWaitStatus.OK
    if (
        status in TERMINAL_CANCEL_WAIT_STATUSES
        or stop_reason in TERMINAL_CANCEL_STOP_REASONS
        or (payload.aborted is True and stop_reason == "stop")
    ):
        return OpenClawWaitStatus.ERROR
    if status in {"timeout", "timed_out"}:
        if gateway_wait_payload_is_terminal(payload):
            return OpenClawWaitStatus.ERROR
        return OpenClawWaitStatus.TIMEOUT
    if status == "accepted":
        if gateway_wait_payload_is_terminal(payload):
            return OpenClawWaitStatus.ERROR
        return OpenClawWaitStatus.TIMEOUT
    return OpenClawWaitStatus.ERROR


def gateway_wait_payload_is_terminal(payload: OpenClawAgentWaitPayload) -> bool:
    stop_reason = "" if payload.stop_reason is None else payload.stop_reason.lower()
    return (
        payload.ended_at is not None
        or payload.error is not None
        or stop_reason in TERMINAL_TIMEOUT_STOP_REASONS
        or bool(stop_reason)
        or payload.liveness_state is not None
        or payload.yielded is True
        or payload.aborted is True
    )


__all__ = ["normalize_gateway_wait_status"]
