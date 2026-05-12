from __future__ import annotations

from datetime import UTC, datetime, timedelta

_DISPATCH_DRAIN_TIMEOUT_SECONDS = 30


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def dispatch_control_deadline(*, base: datetime | None = None) -> datetime:
    return (base or utc_now()) + timedelta(seconds=_DISPATCH_DRAIN_TIMEOUT_SECONDS)
