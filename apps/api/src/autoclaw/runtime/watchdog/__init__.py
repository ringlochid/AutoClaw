"""Temporary Phase 6 shims for the legacy runtime-watchdog owners."""

from __future__ import annotations

from app.runtime.watchdog import (
    drive_watchdog_once,
    drive_watchdog_until,
    notify_runtime_watchdog,
    start_runtime_watchdog,
    stop_runtime_watchdog,
    wait_for_runtime_watchdog,
)

__all__ = [
    "drive_watchdog_once",
    "drive_watchdog_until",
    "notify_runtime_watchdog",
    "start_runtime_watchdog",
    "stop_runtime_watchdog",
    "wait_for_runtime_watchdog",
]
