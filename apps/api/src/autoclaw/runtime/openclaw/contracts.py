"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.contracts as _owner

OpenClawAbortRequest = _owner.OpenClawAbortRequest
OpenClawAbortResult = _owner.OpenClawAbortResult
OpenClawAdapterError = _owner.OpenClawAdapterError
OpenClawAgentLaunchInput = _owner.OpenClawAgentLaunchInput
OpenClawAuthError = _owner.OpenClawAuthError
OpenClawCompatibilityError = _owner.OpenClawCompatibilityError
OpenClawCompatibilityReport = _owner.OpenClawCompatibilityReport
OpenClawConfigurationError = _owner.OpenClawConfigurationError
OpenClawLaunchResult = _owner.OpenClawLaunchResult
OpenClawObservedEvent = _owner.OpenClawObservedEvent
OpenClawProtocolError = _owner.OpenClawProtocolError
OpenClawTransportError = _owner.OpenClawTransportError
OpenClawWaitRequest = _owner.OpenClawWaitRequest
OpenClawWaitResult = _owner.OpenClawWaitResult
OpenClawWaitStatus = _owner.OpenClawWaitStatus
gateway_ws_url_from_base_url = _owner.gateway_ws_url_from_base_url

__all__ = [
    "OpenClawAbortRequest",
    "OpenClawAbortResult",
    "OpenClawAdapterError",
    "OpenClawAgentLaunchInput",
    "OpenClawAuthError",
    "OpenClawCompatibilityError",
    "OpenClawCompatibilityReport",
    "OpenClawConfigurationError",
    "OpenClawLaunchResult",
    "OpenClawObservedEvent",
    "OpenClawProtocolError",
    "OpenClawTransportError",
    "OpenClawWaitRequest",
    "OpenClawWaitResult",
    "OpenClawWaitStatus",
    "gateway_ws_url_from_base_url",
]
