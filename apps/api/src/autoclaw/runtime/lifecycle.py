from __future__ import annotations

from autoclaw.runtime.command_run_runner import stop_all_command_run_runners
from autoclaw.runtime.dispatch.openclaw.lifecycle import close_all_dispatch_runtimes
from autoclaw.runtime.post_commit.worker import stop_all_runtime_effect_runners
from autoclaw.runtime.watchdog.manager import stop_all_runtime_watchdogs


async def shutdown_runtime_lifecycle() -> None:
    await stop_all_command_run_runners()
    await stop_all_runtime_watchdogs()
    await stop_all_runtime_effect_runners()
    await close_all_dispatch_runtimes()


__all__ = ["shutdown_runtime_lifecycle"]
