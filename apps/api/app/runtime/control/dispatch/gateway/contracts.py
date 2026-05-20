from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.runtime.control.dispatch.openclaw_runtime import OpenClawDispatchLaunchLease
from app.runtime.openclaw import OpenClawLaunchResult


@dataclass(frozen=True)
class AcceptedGatewayRunCleanupResult:
    abort_requested: bool
    terminal: bool
    delivery_status: str
    event_kind: str
    summary: str
    detail: str
    observed_at: datetime
    provider_final_status: str | None = None
    provider_error: str | None = None


@dataclass(frozen=True)
class GatewayDispatchLaunchError(Exception):
    error: Exception
    request_sent: bool
    session_key: str
    lease: OpenClawDispatchLaunchLease | None = None

    def __str__(self) -> str:
        return str(self.error)


@dataclass(frozen=True)
class GatewayDispatchLaunchOutcome:
    launch_result: OpenClawLaunchResult
    prompt_path: str
    content_hash: str
    lease: OpenClawDispatchLaunchLease
