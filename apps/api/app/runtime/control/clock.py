from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config import get_settings


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def dispatch_control_deadline(*, base: datetime | None = None) -> datetime:
    timeout_seconds = get_settings().runtime.dispatch_drain_timeout_seconds
    return (base or utc_now()) + timedelta(seconds=timeout_seconds)
