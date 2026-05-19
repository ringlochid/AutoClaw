from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.runtime.control.dispatch.openclaw_runtime import OpenClawDispatchLaunchLease
from app.runtime.openclaw import OpenClawLaunchResult

CleanupState = tuple[bool, bool, str, str, str, str, datetime, str | None, str | None]


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
