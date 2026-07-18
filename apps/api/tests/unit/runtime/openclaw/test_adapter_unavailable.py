from __future__ import annotations

import pytest
from autoclaw.config import OpenClawSettings
from autoclaw.integrations.openclaw.gateway import (
    OpenClawAdapterUnavailableError,
    OpenClawGatewayAdapter,
)


@pytest.mark.asyncio
async def test_openclaw_adapter_seam_reports_nonretryable_unavailable_capability() -> None:
    config = OpenClawSettings(
        enabled=True,
        gateway_url="ws://127.0.0.1:18789",
        gateway_profile="experimental",
    )
    adapter = OpenClawGatewayAdapter(config=config)

    assert adapter.config is config

    message = (
        "OpenClaw provider execution is not available in this build; retrying the "
        "same operation will not succeed"
    )
    with pytest.raises(OpenClawAdapterUnavailableError, match=message):
        await adapter.start(object())
    with pytest.raises(OpenClawAdapterUnavailableError, match=message):
        await adapter.stop("dispatch-1")
    with pytest.raises(OpenClawAdapterUnavailableError, match=message):
        await adapter.check()
