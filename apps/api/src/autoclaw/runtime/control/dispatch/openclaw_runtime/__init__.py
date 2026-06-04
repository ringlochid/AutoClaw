"""Explicit Phase 6 bridge for the legacy dispatch OpenClaw runtime owner."""

from __future__ import annotations

from app.runtime.control.dispatch import openclaw_runtime as legacy_openclaw_runtime

OpenClawDispatchLaunchLease = legacy_openclaw_runtime.OpenClawDispatchLaunchLease
abort_dispatch_runtime = legacy_openclaw_runtime.abort_dispatch_runtime
activate_dispatch_runtime = legacy_openclaw_runtime.activate_dispatch_runtime
close_all_dispatch_runtimes = legacy_openclaw_runtime.close_all_dispatch_runtimes
close_dispatch_launch_lease = legacy_openclaw_runtime.close_dispatch_launch_lease
close_dispatch_runtime = legacy_openclaw_runtime.close_dispatch_runtime
open_dispatch_launch_lease = legacy_openclaw_runtime.open_dispatch_launch_lease
wait_dispatch_runtime = legacy_openclaw_runtime.wait_dispatch_runtime
wait_for_dispatch_runtime_closed = legacy_openclaw_runtime.wait_for_dispatch_runtime_closed

__all__ = [
    "OpenClawDispatchLaunchLease",
    "abort_dispatch_runtime",
    "activate_dispatch_runtime",
    "close_all_dispatch_runtimes",
    "close_dispatch_launch_lease",
    "close_dispatch_runtime",
    "open_dispatch_launch_lease",
    "wait_dispatch_runtime",
    "wait_for_dispatch_runtime_closed",
]
