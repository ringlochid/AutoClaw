from __future__ import annotations

from autoclaw.integrations.openclaw.gateway.contracts import OpenClawObservedEvent

_AGENT_TOOL_STREAMS = frozenset({"tool", "item", "command_output"})
_CANCELLED_END_STATUSES = frozenset({"aborted", "cancelled", "canceled", "killed"})
_CANCELLED_STOP_REASONS = frozenset({"aborted", "cancelled", "canceled", "killed", "rpc", "user"})
_TIMED_OUT_END_STATUSES = frozenset({"timeout", "timed_out"})


def normalize_gateway_event_name(event: OpenClawObservedEvent) -> str | None:
    gateway_event_name = str(event.event).strip()
    if not gateway_event_name:
        return None
    if gateway_event_name == "agent":
        return normalize_agent_gateway_event_name(event.payload)
    if gateway_event_name == "session.message":
        return "assistant.message"
    if gateway_event_name == "session.tool":
        return "tool.call.delta"
    return gateway_event_name


def normalize_agent_gateway_event_name(payload: dict[str, object]) -> str | None:
    stream = read_string(payload.get("stream"))
    data = as_payload_record(payload.get("data"))
    phase = read_string(data.get("phase"))
    status = read_lower_string(data.get("status"))
    stop_reason = read_lower_string(data.get("stopReason"))

    if stream == "assistant":
        return (
            "assistant.delta"
            if data.get("delta") is True or isinstance(data.get("delta"), str)
            else "assistant.message"
        )
    if stream in {"thinking", "plan"}:
        return "thinking.delta"
    if stream == "lifecycle":
        if phase == "start":
            return "run.started"
        if phase == "end":
            return normalize_lifecycle_end_event_name(data, status, stop_reason)
        if phase == "error":
            return "run.failed"
        return None
    if stream in _AGENT_TOOL_STREAMS:
        if phase == "start" or status == "running":
            return "tool.call.started"
        if phase in {"delta", "update"}:
            return "tool.call.delta"
        if phase == "end" or status == "completed":
            return "tool.call.completed"
        if status in {"failed", "blocked"}:
            return "tool.call.failed"
        return "tool.call.delta"
    if stream == "error":
        return "run.failed"
    return None


def normalize_lifecycle_end_event_name(
    data: dict[str, object],
    status: str | None,
    stop_reason: str | None,
) -> str:
    if (
        status in _CANCELLED_END_STATUSES
        or stop_reason in _CANCELLED_STOP_REASONS
        or (data.get("aborted") is True and stop_reason == "stop")
    ):
        return "run.cancelled"
    if (
        status in _TIMED_OUT_END_STATUSES
        or stop_reason in _TIMED_OUT_END_STATUSES
        or data.get("aborted") is True
    ):
        return "run.timed_out"
    return "run.completed"


def read_lower_string(value: object) -> str | None:
    text = read_string(value)
    return None if text is None else text.lower()


def as_payload_record(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def read_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
