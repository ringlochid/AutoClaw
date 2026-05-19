from __future__ import annotations

from app.runtime.control.dispatch.openclaw_runtime.models import OpenClawDispatchLaunchLease
from app.runtime.openclaw import build_openclaw_gateway_adapter


async def open_dispatch_launch_lease() -> OpenClawDispatchLaunchLease:
    session_manager = build_openclaw_gateway_adapter().dispatch_handle()
    handle = await session_manager.__aenter__()
    return OpenClawDispatchLaunchLease(session_manager=session_manager, handle=handle)


async def close_dispatch_launch_lease(lease: OpenClawDispatchLaunchLease) -> None:
    if lease.closed:
        return
    lease.closed = True
    await lease.session_manager.__aexit__(None, None, None)
