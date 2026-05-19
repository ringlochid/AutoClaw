from __future__ import annotations

import asyncio
from contextlib import suppress

from app.runtime.control.dispatch.openclaw_runtime.event_ingest import run_dispatch_ingest
from app.runtime.control.dispatch.openclaw_runtime.lease import close_dispatch_launch_lease
from app.runtime.control.dispatch.openclaw_runtime.models import (
    ActiveOpenClawDispatchRuntime,
    OpenClawDispatchLaunchLease,
)
from app.runtime.openclaw import OpenClawAbortRequest, OpenClawWaitRequest, OpenClawWaitResult

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
        run_registered_dispatch_ingest(runtime, registry),
        name=f"openclaw-dispatch-ingest:{dispatch_id}",
    )


async def close_dispatch_runtime(dispatch_id: str) -> None:
    runtime = runtime_registry().pop(dispatch_id, None)
    if runtime is None:
        return
    await close_runtime_instance(runtime)


async def close_all_dispatch_runtimes() -> None:
    runtimes = tuple(runtime_registry().values())
    runtime_registry().clear()
    for runtime in runtimes:
        await close_runtime_instance(runtime)


async def wait_for_dispatch_runtime_closed(
    dispatch_id: str,
    *,
    timeout_seconds: float = 2.0,
    poll_interval_seconds: float = 0.05,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while runtime_registry().get(dispatch_id) is not None or dispatch_runtime_session_open(
        dispatch_id
    ):
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


async def run_registered_dispatch_ingest(
    runtime: ActiveOpenClawDispatchRuntime,
    registry: dict[str, ActiveOpenClawDispatchRuntime],
) -> None:
    try:
        await run_dispatch_ingest(runtime)
    finally:
        if registry.get(runtime.dispatch_id) is runtime:
            registry.pop(runtime.dispatch_id, None)


async def close_runtime_instance(runtime: ActiveOpenClawDispatchRuntime) -> None:
    runtime.closing = True
    task = runtime.ingest_task
    current_task = asyncio.current_task()
    if task is not None and task is not current_task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    await close_dispatch_launch_lease(runtime.lease)


def runtime_registry() -> dict[str, ActiveOpenClawDispatchRuntime]:
    return RUNTIME_BY_LOOP.setdefault(id(asyncio.get_running_loop()), {})


def dispatch_runtime_session_open(dispatch_id: str) -> bool:
    from app.db.session import open_session_info_value_present

    return open_session_info_value_present(
        key="openclaw_dispatch_runtime",
        value=dispatch_id,
    )
