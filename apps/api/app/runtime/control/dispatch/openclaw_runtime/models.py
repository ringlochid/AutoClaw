from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.runtime.openclaw import OpenClawGatewayRuntimeHandle

EVENT_POLL_TIMEOUT_SECONDS = 0.25
TERMINAL_DELIVERY_STATUS = {
    "response_completed": "provider_completed",
    "response_failed": "provider_failed",
}
PROGRESS_RAW_EVENT_LABELS = frozenset(
    {"assistant.delta", "assistant.message", "thinking.delta", "response.delta"}
)
TOOL_RAW_EVENT_LABELS = frozenset(
    {
        "tool.call",
        "tool.call.started",
        "tool.call.delta",
        "tool.call.completed",
        "tool.call.failed",
    }
)
COMPLETED_RAW_EVENT_LABELS = frozenset({"run.completed", "response.completed"})
FAILED_RAW_EVENT_LABELS = frozenset(
    {"run.failed", "run.cancelled", "run.timed_out", "response.failed"}
)
SUPPORTED_RAW_EVENT_LABELS = frozenset(
    PROGRESS_RAW_EVENT_LABELS
    | TOOL_RAW_EVENT_LABELS
    | COMPLETED_RAW_EVENT_LABELS
    | FAILED_RAW_EVENT_LABELS
)


@dataclass
class OpenClawDispatchLaunchLease:
    session_manager: AbstractAsyncContextManager[OpenClawGatewayRuntimeHandle]
    handle: OpenClawGatewayRuntimeHandle
    closed: bool = False


@dataclass(frozen=True)
class NormalizedOpenClawEvent:
    event_kind: str
    summary: str
    detail: str
    provider_event_name: str
    provider_occurred_at: datetime | None
    event_payload_json: dict[str, object]
    advances_liveness: bool


@dataclass
class ActiveOpenClawDispatchRuntime:
    task_id: str
    dispatch_id: str
    attempt_id: str
    session_key: str
    run_id: str
    lease: OpenClawDispatchLaunchLease
    session_factory: async_sessionmaker = field(default_factory=lambda: session_factory_factory())
    ingest_task: asyncio.Task[None] | None = None
    saw_provider_progress: bool = False
    seen_gateway_seqs: set[int] = field(default_factory=set)
    seen_event_fingerprints: set[str] = field(default_factory=set)
    closing: bool = False


def session_factory_factory() -> async_sessionmaker:
    from app.db.session import get_session_factory

    return get_session_factory()
