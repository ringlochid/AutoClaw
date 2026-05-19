from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


def sql_in(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


NODE_KIND_VALUES = ("root", "parent", "worker")
NODE_STATE_VALUES = (
    "ready",
    "running",
    "waiting",
    "paused",
    "done",
    "failed",
    "superseded",
    "cancelled",
)
FLOW_STATUS_VALUES = ("pending", "running", "blocked", "paused", "succeeded", "cancelled")
STRUCTURAL_REVISION_CAUSE_VALUES = ("launch", "add_child", "update_child", "remove_child")
FLOW_EDGE_KIND_VALUES = ("artifact", "criteria")
CHECKPOINT_KIND_VALUES = ("progress", "terminal")
CHECKPOINT_OUTCOME_VALUES = ("green", "retry", "blocked")
ATTEMPT_STATUS_VALUES = (
    "pending",
    "running",
    "blocked",
    "failed",
    "succeeded",
    "cancelled",
    "aborted",
)
PROMPT_SEND_MODE_VALUES = ("full_prompt",)
DISPATCH_DELIVERY_STATUS_VALUES = (
    "prepared",
    "accepted",
    "provider_signal_seen",
    "provider_completed",
    "provider_failed",
    "transport_failed",
    "transport_ambiguous",
    "superseded",
)
DISPATCH_CONTROL_STATE_VALUES = ("launching", "live", "abort_requested", "ambiguous", "fenced")
RELEASE_PRECONDITION_KIND_VALUES = ("release_green", "release_blocked")
RUNTIME_REF_KIND_VALUES = ("artifact", "criteria", "doc", "wiki", "transient", "checkpoint")
PROVIDER_EVENT_SOURCE_VALUES = ("provider", "adapter")
PROVIDER_EVENT_KIND_VALUES = (
    "accepted",
    "first_data",
    "output_delta",
    "tool_event",
    "response_completed",
    "response_failed",
    "transport_timeout",
    "transport_failed",
)

__all__ = [
    "ATTEMPT_STATUS_VALUES",
    "CHECKPOINT_KIND_VALUES",
    "CHECKPOINT_OUTCOME_VALUES",
    "DISPATCH_CONTROL_STATE_VALUES",
    "DISPATCH_DELIVERY_STATUS_VALUES",
    "FLOW_EDGE_KIND_VALUES",
    "FLOW_STATUS_VALUES",
    "NODE_KIND_VALUES",
    "NODE_STATE_VALUES",
    "PROMPT_SEND_MODE_VALUES",
    "PROVIDER_EVENT_KIND_VALUES",
    "PROVIDER_EVENT_SOURCE_VALUES",
    "RELEASE_PRECONDITION_KIND_VALUES",
    "RUNTIME_REF_KIND_VALUES",
    "STRUCTURAL_REVISION_CAUSE_VALUES",
    "sql_in",
    "utcnow",
]
