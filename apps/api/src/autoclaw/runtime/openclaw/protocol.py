"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.protocol as _owner

OPENCLAW_PROTOCOL_VERSION = _owner.OPENCLAW_PROTOCOL_VERSION
OPENCLAW_RELEASE_FAMILY = _owner.OPENCLAW_RELEASE_FAMILY
REQUIRED_GATEWAY_EVENTS = _owner.REQUIRED_GATEWAY_EVENTS
REQUIRED_GATEWAY_METHODS = _owner.REQUIRED_GATEWAY_METHODS
REQUIRED_GATEWAY_ROLE = _owner.REQUIRED_GATEWAY_ROLE
REQUIRED_GATEWAY_SCOPES = _owner.REQUIRED_GATEWAY_SCOPES
OpenClawAgentAcceptedPayload = _owner.OpenClawAgentAcceptedPayload
OpenClawAgentParams = _owner.OpenClawAgentParams
OpenClawAgentRequest = _owner.OpenClawAgentRequest
OpenClawAgentWaitParams = _owner.OpenClawAgentWaitParams
OpenClawAgentWaitPayload = _owner.OpenClawAgentWaitPayload
OpenClawAgentWaitRequest = _owner.OpenClawAgentWaitRequest
OpenClawConnectAuth = _owner.OpenClawConnectAuth
OpenClawConnectChallengeEvent = _owner.OpenClawConnectChallengeEvent
OpenClawConnectChallengePayload = _owner.OpenClawConnectChallengePayload
OpenClawConnectClient = _owner.OpenClawConnectClient
OpenClawConnectDevice = _owner.OpenClawConnectDevice
OpenClawConnectParams = _owner.OpenClawConnectParams
OpenClawConnectRequest = _owner.OpenClawConnectRequest
OpenClawGatewayError = _owner.OpenClawGatewayError
OpenClawGatewayErrorDetails = _owner.OpenClawGatewayErrorDetails
OpenClawGatewayEventFrame = _owner.OpenClawGatewayEventFrame
OpenClawGatewayResponseEnvelope = _owner.OpenClawGatewayResponseEnvelope
OpenClawHelloAuth = _owner.OpenClawHelloAuth
OpenClawHelloAuthToken = _owner.OpenClawHelloAuthToken
OpenClawHelloFeatures = _owner.OpenClawHelloFeatures
OpenClawHelloOkPayload = _owner.OpenClawHelloOkPayload
OpenClawHelloOkPolicy = _owner.OpenClawHelloOkPolicy
OpenClawHelloServer = _owner.OpenClawHelloServer
OpenClawProtocolModel = _owner.OpenClawProtocolModel
OpenClawSessionsAbortParams = _owner.OpenClawSessionsAbortParams
OpenClawSessionsAbortRequest = _owner.OpenClawSessionsAbortRequest
parse_connect_challenge = _owner.parse_connect_challenge
parse_gateway_frame = _owner.parse_gateway_frame
parse_response_payload = _owner.parse_response_payload

__all__ = [
    "OPENCLAW_PROTOCOL_VERSION",
    "OPENCLAW_RELEASE_FAMILY",
    "REQUIRED_GATEWAY_EVENTS",
    "REQUIRED_GATEWAY_METHODS",
    "REQUIRED_GATEWAY_ROLE",
    "REQUIRED_GATEWAY_SCOPES",
    "OpenClawAgentAcceptedPayload",
    "OpenClawAgentParams",
    "OpenClawAgentRequest",
    "OpenClawAgentWaitParams",
    "OpenClawAgentWaitPayload",
    "OpenClawAgentWaitRequest",
    "OpenClawConnectAuth",
    "OpenClawConnectChallengeEvent",
    "OpenClawConnectChallengePayload",
    "OpenClawConnectClient",
    "OpenClawConnectDevice",
    "OpenClawConnectParams",
    "OpenClawConnectRequest",
    "OpenClawGatewayError",
    "OpenClawGatewayErrorDetails",
    "OpenClawGatewayEventFrame",
    "OpenClawGatewayResponseEnvelope",
    "OpenClawHelloAuth",
    "OpenClawHelloAuthToken",
    "OpenClawHelloFeatures",
    "OpenClawHelloOkPayload",
    "OpenClawHelloOkPolicy",
    "OpenClawHelloServer",
    "OpenClawProtocolModel",
    "OpenClawSessionsAbortParams",
    "OpenClawSessionsAbortRequest",
    "parse_connect_challenge",
    "parse_gateway_frame",
    "parse_response_payload",
]
