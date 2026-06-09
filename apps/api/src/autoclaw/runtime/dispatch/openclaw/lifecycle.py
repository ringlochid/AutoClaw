from __future__ import annotations

import asyncio
from contextlib import suppress

from autoclaw.integrations.openclaw.gateway import (
    OpenClawAbortRequest,
    OpenClawWaitRequest,
    OpenClawWaitResult,
)
from autoclaw.runtime.dispatch.openclaw.event_ingest import ingest_dispatch_events
from autoclaw.runtime.dispatch.openclaw.lease import close_dispatch_launch_lease
from autoclaw.runtime.dispatch.openclaw.models import (
    ActiveOpenClawDispatchRuntime,
    OpenClawDispatchLaunchLease,
)

RUNTIME_BY_LOOP: dict[int, dict[str, ActiveOpenClawDispatchRuntime]] = {}


async def activate_dispatch_runtime(
    *,
    task_id: str,
    dispatch_id: str,
    attempt_id: str,
    session_key: str,
    run_id: str,
    lease: OpenClawDispatchLaunchLease,
) -> None:
    runtime = ActiveOpenClawDispatchRuntime(
        task_id=task_id,
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
        session_key=session_key,
        run_id=run_id,
        lease=lease,
    )
    registry = runtime_registry()
    registry[dispatch_id] = runtime
    runtime.ingest_task = asyncio.create_task(
        ingest_registered_dispatch_events(runtime, registry),
        name=f"openclaw-dispatch-ingest:{dispatch_id}",
    )


async def close_dispatch_runtime(
    dispatch_id: str,
    *,
    should_abort_remote: bool = False,
) -> None:
    runtime = runtime_registry().pop(dispatch_id, None)
    if runtime is None:
        return
    await close_runtime_instance(runtime, should_abort_remote=should_abort_remote)


async def close_all_dispatch_runtimes() -> None:
    runtimes = tuple(runtime_registry().values())
    runtime_registry().clear()
    for runtime in runtimes:
        await close_runtime_instance(runtime, should_abort_remote=True)


async def wait_for_dispatch_runtime_closed(
    dispatch_id: str,
    *,
    timeout_seconds: float = 2.0,
    poll_interval_seconds: float = 0.05,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while runtime_registry().get(dispatch_id) is not None:
        if loop.time() >= deadline:
            raise TimeoutError(f"timed out waiting for dispatch runtime '{dispatch_id}' to close")
        await asyncio.sleep(poll_interval_seconds)


async def abort_dispatch_runtime(
    dispatch_id: str,
    *,
    session_key: str,
    run_id: str | None,
) -> bool:
    runtime = runtime_registry().get(dispatch_id)
    if runtime is None:
        return False
    await runtime.lease.handle.abort_run(
        OpenClawAbortRequest(session_key=session_key, run_id=run_id)
    )
    return True


async def wait_dispatch_runtime(
    dispatch_id: str,
    *,
    run_id: str,
    timeout_ms: int,
) -> OpenClawWaitResult | None:
    runtime = runtime_registry().get(dispatch_id)
    if runtime is None:
        return None
    return await runtime.lease.handle.wait_for_run(
        OpenClawWaitRequest(run_id=run_id, timeout_ms=timeout_ms)
    )


async def ingest_registered_dispatch_events(
    runtime: ActiveOpenClawDispatchRuntime,
    registry: dict[str, ActiveOpenClawDispatchRuntime],
) -> None:
    try:
        await ingest_dispatch_events(runtime)
    finally:
        if registry.get(runtime.dispatch_id) is runtime:
            registry.pop(runtime.dispatch_id, None)


async def close_runtime_instance(
    runtime: ActiveOpenClawDispatchRuntime,
    *,
    should_abort_remote: bool = False,
) -> None:
    runtime.is_closing = True
    if should_abort_remote:
        with suppress(Exception):
            await runtime.lease.handle.abort_run(
                OpenClawAbortRequest(
                    session_key=runtime.session_key,
                    run_id=runtime.run_id,
                )
            )
    task = runtime.ingest_task
    current_task = asyncio.current_task()
    if task is not None and task is not current_task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    await close_dispatch_launch_lease(runtime.lease)


def runtime_registry() -> dict[str, ActiveOpenClawDispatchRuntime]:
    return RUNTIME_BY_LOOP.setdefault(id(asyncio.get_running_loop()), {})
