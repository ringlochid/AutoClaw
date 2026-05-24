from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import OpenClawSettings, Settings, get_settings
from app.runtime.openclaw.contracts import (
    OpenClawAbortRequest,
    OpenClawAbortResult,
    OpenClawAgentLaunchInput,
    OpenClawCompatibilityReport,
    OpenClawLaunchResult,
    OpenClawWaitRequest,
    OpenClawWaitResult,
)
from app.runtime.openclaw.runtime_handle import OpenClawGatewayRuntimeHandle
from app.runtime.openclaw.session_keys import normalize_agent_launch_input


class OpenClawGatewayAdapter:
    def __init__(
        self,
        *,
        config: OpenClawSettings,
        data_dir: Path,
    ) -> None:
        self._config = config
        self._auth_state_path = data_dir / "openclaw" / "gateway-device-auth.json"

    async def check_compatibility(self) -> OpenClawCompatibilityReport:
        async with self.dispatch_handle() as handle:
            return handle.require_compatibility()

    async def launch_run(self, request: OpenClawAgentLaunchInput) -> OpenClawLaunchResult:
        normalized_request = normalize_agent_launch_input(request, self._config.agent_id)
        async with self.dispatch_handle() as handle:
            return await handle.launch_run(normalized_request)

    async def wait_for_run(self, request: OpenClawWaitRequest) -> OpenClawWaitResult:
        async with self.dispatch_handle() as handle:
            return await handle.wait_for_run(request)

    async def abort_run(self, request: OpenClawAbortRequest) -> OpenClawAbortResult:
        async with self.dispatch_handle() as handle:
            return await handle.abort_run(request)

    @asynccontextmanager
    async def dispatch_handle(self) -> AsyncIterator[OpenClawGatewayRuntimeHandle]:
        handle = OpenClawGatewayRuntimeHandle(
            config=self._config,
            auth_state_path=self._auth_state_path,
        )
        try:
            await handle.open()
            yield handle
        finally:
            await handle.close()


def build_openclaw_gateway_adapter(settings: Settings | None = None) -> OpenClawGatewayAdapter:
    loaded = settings or get_settings()
    return OpenClawGatewayAdapter(
        config=loaded.openclaw,
        data_dir=loaded.data_dir,
    )


def openclaw_startup_compatibility_required(settings: Settings | None = None) -> bool:
    loaded = settings or get_settings()
    if loaded.openclaw.gateway_token:
        return True
    return (loaded.data_dir / "openclaw" / "gateway-device-auth.json").is_file()


__all__ = [
    "OpenClawGatewayAdapter",
    "build_openclaw_gateway_adapter",
    "openclaw_startup_compatibility_required",
]
