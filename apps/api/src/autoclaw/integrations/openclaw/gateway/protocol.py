from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

OPENCLAW_RELEASE_FAMILY = "2026.5.x"
OPENCLAW_PROTOCOL_VERSION = 4
REQUIRED_GATEWAY_ROLE = "operator"
REQUIRED_GATEWAY_SCOPES = frozenset({"operator.read", "operator.write"})
REQUIRED_GATEWAY_METHODS = frozenset({"agent", "agent.wait", "sessions.abort"})
REQUIRED_GATEWAY_EVENTS = frozenset({"agent"})


class OpenClawProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class OpenClawGatewayFrameType(StrEnum):
    REQUEST = "req"
    RESPONSE = "res"
    EVENT = "event"


class OpenClawGatewayErrorDetails(OpenClawProtocolModel):
    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)

    code: str | None = None
    can_retry_with_device_token: bool | None = Field(
        default=None,
        alias="canRetryWithDeviceToken",
    )
    recommended_next_step: str | None = Field(default=None, alias="recommendedNextStep")


class OpenClawGatewayError(OpenClawProtocolModel):
    code: str | None = None
    message: str
    details: OpenClawGatewayErrorDetails | None = None


class OpenClawGatewayEventFrame(OpenClawProtocolModel):
    type: Literal[OpenClawGatewayFrameType.EVENT] = OpenClawGatewayFrameType.EVENT
    event: str
    payload: dict[str, Any]
    seq: int | None = None
    state_version: int | dict[str, Any] | None = Field(default=None, alias="stateVersion")


class OpenClawGatewayResponseEnvelope(OpenClawProtocolModel):
    type: Literal[OpenClawGatewayFrameType.RESPONSE] = OpenClawGatewayFrameType.RESPONSE
    id: str
    ok: bool
    payload: dict[str, Any] | None = None
    error: OpenClawGatewayError | None = None

    @model_validator(mode="after")
    def validate_payload_or_error(self) -> OpenClawGatewayResponseEnvelope:
        if self.ok and self.payload is None:
            raise ValueError("successful gateway responses require payload")
        if not self.ok and self.error is None:
            raise ValueError("failed gateway responses require error")
        return self


class OpenClawConnectChallengePayload(OpenClawProtocolModel):
    nonce: str
    ts: int


class OpenClawConnectChallengeEvent(OpenClawProtocolModel):
    type: Literal[OpenClawGatewayFrameType.EVENT] = OpenClawGatewayFrameType.EVENT
    event: Literal["connect.challenge"]
    payload: OpenClawConnectChallengePayload


class OpenClawConnectClient(OpenClawProtocolModel):
    id: str
    version: str
    platform: str
    mode: Literal["webchat", "cli", "ui", "backend", "node", "probe", "test"]


class OpenClawConnectDevice(OpenClawProtocolModel):
    id: str
    public_key: str = Field(alias="publicKey")
    signature: str
    signed_at: int = Field(alias="signedAt")
    nonce: str


class OpenClawConnectAuth(OpenClawProtocolModel):
    token: str | None = None
    password: str | None = None
    device_token: str | None = Field(default=None, alias="deviceToken")

    @model_validator(mode="after")
    def validate_auth_choice(self) -> OpenClawConnectAuth:
        provided = [value for value in (self.token, self.password, self.device_token) if value]
        if len(provided) != 1:
            raise ValueError("connect auth requires exactly one of token, password, or deviceToken")
        return self


class OpenClawConnectParams(OpenClawProtocolModel):
    min_protocol: int = Field(alias="minProtocol")
    max_protocol: int = Field(alias="maxProtocol")
    client: OpenClawConnectClient
    role: Literal["operator"]
    scopes: tuple[str, ...]
    caps: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    permissions: dict[str, bool] = Field(default_factory=dict)
    auth: OpenClawConnectAuth | None = None
    locale: str = "en-US"
    user_agent: str = Field(alias="userAgent")
    device: OpenClawConnectDevice | None = None


class OpenClawConnectRequest(OpenClawProtocolModel):
    type: Literal[OpenClawGatewayFrameType.REQUEST] = OpenClawGatewayFrameType.REQUEST
    id: str
    method: Literal["connect"]
    params: OpenClawConnectParams


class OpenClawHelloOkPolicy(OpenClawProtocolModel):
    tick_interval_ms: int = Field(alias="tickIntervalMs")
    max_payload: int | None = Field(default=None, alias="maxPayload")
    max_buffered_bytes: int | None = Field(default=None, alias="maxBufferedBytes")


class OpenClawHelloAuthToken(OpenClawProtocolModel):
    device_token: str = Field(alias="deviceToken")
    role: str
    scopes: tuple[str, ...]
    issued_at_ms: int | None = Field(default=None, alias="issuedAtMs")


class OpenClawHelloAuth(OpenClawProtocolModel):
    device_token: str | None = Field(default=None, alias="deviceToken")
    role: str | None = None
    scopes: tuple[str, ...] = ()
    issued_at_ms: int | None = Field(default=None, alias="issuedAtMs")
    device_tokens: tuple[OpenClawHelloAuthToken, ...] = Field(
        default=(),
        alias="deviceTokens",
    )


class OpenClawHelloFeatures(OpenClawProtocolModel):
    methods: tuple[str, ...] = ()
    events: tuple[str, ...] = ()


class OpenClawHelloServer(OpenClawProtocolModel):
    version: str
    conn_id: str = Field(alias="connId")


class OpenClawHelloOkPayload(OpenClawProtocolModel):
    type: Literal["hello-ok"]
    protocol: int
    server: OpenClawHelloServer
    snapshot: dict[str, Any]
    plugin_surface_urls: dict[str, str] | None = Field(
        default=None,
        alias="pluginSurfaceUrls",
    )
    policy: OpenClawHelloOkPolicy
    auth: OpenClawHelloAuth | None = None
    features: OpenClawHelloFeatures | None = None


class OpenClawAgentParams(OpenClawProtocolModel):
    session_key: str = Field(alias="sessionKey")
    message: str
    channel: str | None = None
    extra_system_prompt: str | None = Field(default=None, alias="extraSystemPrompt")
    idempotency_key: str = Field(alias="idempotencyKey")


class OpenClawAgentRequest(OpenClawProtocolModel):
    type: Literal[OpenClawGatewayFrameType.REQUEST] = OpenClawGatewayFrameType.REQUEST
    id: str
    method: Literal["agent"]
    params: OpenClawAgentParams


class OpenClawAgentAcceptedPayload(OpenClawProtocolModel):
    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)

    run_id: str = Field(alias="runId")
    status: Literal["accepted"]
    accepted_at: datetime = Field(alias="acceptedAt")
    session_key: str | None = Field(default=None, alias="sessionKey")


class OpenClawAgentWaitParams(OpenClawProtocolModel):
    run_id: str = Field(alias="runId")
    timeout_ms: int | None = Field(default=None, alias="timeoutMs")


class OpenClawAgentWaitRequest(OpenClawProtocolModel):
    type: Literal[OpenClawGatewayFrameType.REQUEST] = OpenClawGatewayFrameType.REQUEST
    id: str
    method: Literal["agent.wait"]
    params: OpenClawAgentWaitParams


class OpenClawAgentWaitPayload(OpenClawProtocolModel):
    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)

    run_id: str = Field(alias="runId")
    status: str
    started_at: datetime | None = Field(default=None, alias="startedAt")
    ended_at: datetime | None = Field(default=None, alias="endedAt")
    error: OpenClawGatewayError | None = None
    stop_reason: str | None = Field(default=None, alias="stopReason")
    liveness_state: str | None = Field(default=None, alias="livenessState")
    aborted: bool | None = None
    yielded: bool | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("agent.wait status must not be blank")
        return stripped

    @field_validator("error", mode="before")
    @classmethod
    def normalize_string_error(cls, value: object) -> object:
        if isinstance(value, str):
            message = value.strip()
            if not message:
                return None
            return {"message": message}
        return value


class OpenClawSessionsAbortParams(OpenClawProtocolModel):
    key: str
    run_id: str | None = Field(default=None, alias="runId")


class OpenClawSessionsAbortRequest(OpenClawProtocolModel):
    type: Literal[OpenClawGatewayFrameType.REQUEST] = OpenClawGatewayFrameType.REQUEST
    id: str
    method: Literal["sessions.abort"]
    params: OpenClawSessionsAbortParams


GatewayFrame = OpenClawGatewayEventFrame | OpenClawGatewayResponseEnvelope
GatewayFrameAdapter: TypeAdapter[GatewayFrame] = TypeAdapter(GatewayFrame)
ProtocolPayloadT = TypeVar("ProtocolPayloadT", bound=OpenClawProtocolModel)


def parse_gateway_frame(
    payload: dict[str, Any],
) -> OpenClawGatewayEventFrame | OpenClawGatewayResponseEnvelope:
    return GatewayFrameAdapter.validate_python(payload)


def parse_connect_challenge(payload: dict[str, Any]) -> OpenClawConnectChallengeEvent:
    return OpenClawConnectChallengeEvent.model_validate(payload)


def parse_response_payload(
    envelope: OpenClawGatewayResponseEnvelope,
    model: type[ProtocolPayloadT],
) -> ProtocolPayloadT:
    if not envelope.ok or envelope.payload is None:
        raise ValueError("gateway response envelope is not successful")
    return model.model_validate(envelope.payload)


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
