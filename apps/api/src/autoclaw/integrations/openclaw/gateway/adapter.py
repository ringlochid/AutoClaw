from __future__ import annotations

from typing import NoReturn

from autoclaw.config import OpenClawSettings, Settings, get_settings


class OpenClawAdapterUnavailableError(RuntimeError):
    """OpenClaw provider execution is not implemented in this build."""


class OpenClawGatewayAdapter:
    """Compile-safe provider seam for an unavailable OpenClaw adapter."""

    def __init__(self, *, config: OpenClawSettings) -> None:
        self.config = config

    async def start(self, _request: object) -> NoReturn:
        _raise_unavailable()

    async def stop(self, _dispatch_id: str) -> NoReturn:
        _raise_unavailable()

    async def check(self) -> NoReturn:
        _raise_unavailable()


def build_openclaw_gateway_adapter(settings: Settings | None = None) -> OpenClawGatewayAdapter:
    loaded = settings or get_settings()
    return OpenClawGatewayAdapter(config=loaded.openclaw)


def _raise_unavailable() -> NoReturn:
    raise OpenClawAdapterUnavailableError(
        "OpenClaw provider execution is not available in this build; retrying the "
        "same operation will not succeed"
    )


__all__ = [
    "OpenClawAdapterUnavailableError",
    "OpenClawGatewayAdapter",
    "build_openclaw_gateway_adapter",
]
