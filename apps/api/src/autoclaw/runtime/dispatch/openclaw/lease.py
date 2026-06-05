from __future__ import annotations

from autoclaw.integrations.openclaw.gateway import build_openclaw_gateway_adapter
from autoclaw.runtime.dispatch.openclaw.models import OpenClawDispatchLaunchLease


async def open_dispatch_launch_lease() -> OpenClawDispatchLaunchLease:
    session_manager = build_openclaw_gateway_adapter().dispatch_handle()
    handle = await session_manager.__aenter__()
    return OpenClawDispatchLaunchLease(session_manager=session_manager, handle=handle)


async def close_dispatch_launch_lease(lease: OpenClawDispatchLaunchLease) -> None:
    if lease.is_closed:
        return
    lease.is_closed = True
    await lease.session_manager.__aexit__(None, None, None)
