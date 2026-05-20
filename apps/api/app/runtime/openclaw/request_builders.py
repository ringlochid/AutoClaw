from __future__ import annotations

import json
from typing import TypedDict
from uuid import uuid4

from app.config import OpenClawSettings
from app.runtime.openclaw.auth_state import StoredDeviceToken, StoredGatewayAuthState
from app.runtime.openclaw.contracts import (
    OpenClawAbortRequest,
    OpenClawAgentLaunchInput,
    OpenClawCompatibilityError,
    OpenClawCompatibilityReport,
    OpenClawWaitRequest,
)
from app.runtime.openclaw.handshake import (
    OpenClawConnectParamsPayload,
    autoclaw_client_version,
    build_openclaw_connect_auth_and_scopes,
    build_openclaw_connect_client,
    build_openclaw_connect_device,
    default_gateway_scopes,
    require_hello_auth,
    validate_gateway_policy,
)
from app.runtime.openclaw.protocol import (
    OPENCLAW_PROTOCOL_VERSION,
    REQUIRED_GATEWAY_EVENTS,
    REQUIRED_GATEWAY_METHODS,
    REQUIRED_GATEWAY_ROLE,
    OpenClawAgentParams,
    OpenClawAgentRequest,
    OpenClawAgentWaitParams,
    OpenClawAgentWaitRequest,
    OpenClawConnectChallengeEvent,
    OpenClawConnectParams,
    OpenClawConnectRequest,
    OpenClawHelloFeatures,
    OpenClawHelloOkPayload,
    OpenClawSessionsAbortParams,
    OpenClawSessionsAbortRequest,
)

OpenClawGatewayRequest = (
    OpenClawAgentRequest
    | OpenClawAgentWaitRequest
    | OpenClawConnectRequest
    | OpenClawSessionsAbortRequest
)


class OpenClawAgentParamsPayload(TypedDict):
    sessionKey: str
    message: str
    idempotencyKey: str


class OpenClawAgentWaitParamsPayload(TypedDict):
    runId: str
    timeoutMs: int | None


class OpenClawSessionsAbortParamsPayload(TypedDict):
    key: str
    runId: str | None


def build_openclaw_agent_request(
    *,
    request_id: str,
    launch_input: OpenClawAgentLaunchInput,
) -> OpenClawAgentRequest:
    payload: OpenClawAgentParamsPayload = {
        "sessionKey": launch_input.session_key,
        "message": launch_input.message,
        "idempotencyKey": launch_input.idempotency_key,
    }
    return OpenClawAgentRequest(
        id=request_id,
        method="agent",
        params=OpenClawAgentParams.model_validate(payload),
    )


def build_openclaw_wait_request(
    *,
    request_id: str,
    wait_request: OpenClawWaitRequest,
) -> OpenClawAgentWaitRequest:
    payload: OpenClawAgentWaitParamsPayload = {
        "runId": wait_request.run_id,
        "timeoutMs": wait_request.timeout_ms,
    }
    return OpenClawAgentWaitRequest(
        id=request_id,
        method="agent.wait",
        params=OpenClawAgentWaitParams.model_validate(payload),
    )


def build_openclaw_abort_request(
    *,
    request_id: str,
    abort_request: OpenClawAbortRequest,
) -> OpenClawSessionsAbortRequest:
    payload: OpenClawSessionsAbortParamsPayload = {
        "key": abort_request.session_key,
        "runId": abort_request.run_id,
    }
    return OpenClawSessionsAbortRequest(
        id=request_id,
        method="sessions.abort",
        params=OpenClawSessionsAbortParams.model_validate(payload),
    )


def build_openclaw_connect_request(
    *,
    config: OpenClawSettings,
    challenge: OpenClawConnectChallengeEvent,
    request_id: str,
    auth_state: StoredGatewayAuthState | None,
    use_cached_device_token: bool,
    gateway_token_override: str | None = None,
) -> OpenClawConnectRequest:
    auth_payload, scopes = build_openclaw_connect_auth_and_scopes(
        gateway_token=config.gateway_token,
        auth_state=auth_state,
        use_cached_device_token=use_cached_device_token,
        gateway_token_override=gateway_token_override,
    )
    client_version = autoclaw_client_version()
    client_payload, user_agent = build_openclaw_connect_client(
        base_url=config.base_url,
        client_version=client_version,
    )
    payload: OpenClawConnectParamsPayload = {
        "minProtocol": OPENCLAW_PROTOCOL_VERSION,
        "maxProtocol": OPENCLAW_PROTOCOL_VERSION,
        "client": client_payload,
        "role": "operator",
        "scopes": scopes,
        "auth": auth_payload,
        "locale": "en-US",
        "userAgent": user_agent,
        "device": build_openclaw_connect_device(
            base_url=config.base_url,
            challenge=challenge,
        ),
    }
    return OpenClawConnectRequest(
        id=request_id,
        method="connect",
        params=OpenClawConnectParams.model_validate(payload),
    )


def build_openclaw_compatibility_report(
    *,
    ws_url: str,
    hello_ok: OpenClawHelloOkPayload,
    retry_used_cached_device_token: bool,
) -> OpenClawCompatibilityReport:
    if hello_ok.protocol != OPENCLAW_PROTOCOL_VERSION:
        raise OpenClawCompatibilityError(
            "OpenClaw protocol mismatch: "
            f"expected {OPENCLAW_PROTOCOL_VERSION}, got {hello_ok.protocol}"
        )
    auth = require_hello_auth(hello_ok)
    role = auth.role
    if role is None:
        raise AssertionError("validated hello-ok auth must include a role")
    scopes = tuple(auth.scopes)
    if not set(scopes).issuperset(default_gateway_scopes()):
        raise OpenClawCompatibilityError(
            "OpenClaw scopes do not satisfy operator.read/operator.write"
        )
    features = hello_ok.features
    available_methods = () if features is None else features.methods
    if hello_feature_is_advertised(features, "methods") and not REQUIRED_GATEWAY_METHODS.issubset(
        available_methods
    ):
        raise OpenClawCompatibilityError(
            "OpenClaw gateway does not advertise the required "
            "agent/agent.wait/sessions.abort subset"
        )
    available_events = () if features is None else features.events
    if not available_events or not REQUIRED_GATEWAY_EVENTS.issubset(available_events):
        raise OpenClawCompatibilityError(
            "OpenClaw gateway hello-ok is missing the required event subset"
        )
    validate_gateway_policy(hello_ok)
    return OpenClawCompatibilityReport(
        ws_url=ws_url,
        protocol_version=hello_ok.protocol,
        role=role,
        scopes=scopes,
        available_methods=available_methods,
        available_events=available_events,
        tick_interval_ms=hello_ok.policy.tick_interval_ms,
        max_payload=hello_ok.policy.max_payload,
        max_buffered_bytes=hello_ok.policy.max_buffered_bytes,
        issued_device_token=auth.device_token,
        retry_used_cached_device_token=retry_used_cached_device_token,
    )


def build_gateway_auth_state(
    *,
    hello_ok: OpenClawHelloOkPayload,
    ws_url: str,
) -> StoredGatewayAuthState | None:
    auth = hello_ok.auth
    if auth is None or auth.device_token is None:
        return None
    bootstrap_tokens: tuple[StoredDeviceToken, ...] = ()
    if gateway_transport_is_trusted(ws_url):
        bootstrap_tokens = tuple(
            StoredDeviceToken(
                device_token=token.device_token,
                role=token.role,
                scopes=token.scopes,
            )
            for token in auth.device_tokens
        )
    return StoredGatewayAuthState(
        primary_token=StoredDeviceToken(
            device_token=auth.device_token,
            role=auth.role or REQUIRED_GATEWAY_ROLE,
            scopes=auth.scopes or default_gateway_scopes(),
        ),
        bootstrap_tokens=bootstrap_tokens,
    )


def hello_feature_is_advertised(
    features: OpenClawHelloFeatures | None,
    field_name: str,
) -> bool:
    return features is not None and field_name in features.model_fields_set


def next_openclaw_request_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def serialize_openclaw_gateway_request(request: OpenClawGatewayRequest) -> str:
    return json.dumps(request.model_dump(mode="json", by_alias=True, exclude_none=True))


def gateway_transport_is_trusted(ws_url: str) -> bool:
    from urllib.parse import urlparse

    parsed = urlparse(ws_url)
    return parsed.scheme == "wss" or (parsed.hostname or "") in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


__all__ = [
    "build_gateway_auth_state",
    "build_openclaw_abort_request",
    "build_openclaw_agent_request",
    "build_openclaw_compatibility_report",
    "build_openclaw_connect_request",
    "build_openclaw_wait_request",
    "next_openclaw_request_id",
    "serialize_openclaw_gateway_request",
]
