from __future__ import annotations

import json

from websockets.asyncio.client import ClientConnection
from websockets.exceptions import WebSocketException

from app.runtime.openclaw.contracts import (
    OpenClawCompatibilityError,
    OpenClawProtocolError,
    OpenClawTransportError,
)
from app.runtime.openclaw.protocol import (
    OpenClawConnectChallengeEvent,
    OpenClawGatewayEventFrame,
    OpenClawGatewayResponseEnvelope,
    parse_connect_challenge,
    parse_gateway_frame,
)


async def receive_connect_challenge(
    connection: ClientConnection,
) -> OpenClawConnectChallengeEvent:
    frame, _frame_size = await receive_frame(connection)
    if not isinstance(frame, OpenClawGatewayEventFrame):
        raise OpenClawProtocolError("expected connect.challenge event before connect request")
    if frame.event != "connect.challenge":
        raise OpenClawProtocolError(f"expected connect.challenge event, received '{frame.event}'")
    return parse_connect_challenge(frame.model_dump(by_alias=True, mode="json", exclude_none=True))


async def receive_frame(
    connection: ClientConnection,
    *,
    max_payload: int | None = None,
) -> tuple[OpenClawGatewayEventFrame | OpenClawGatewayResponseEnvelope, int]:
    try:
        raw_message = await connection.recv()
    except WebSocketException as exc:
        raise OpenClawTransportError("failed while reading from OpenClaw gateway") from exc
    if isinstance(raw_message, bytes):
        raw_bytes = raw_message
        message_text = raw_message.decode("utf-8")
    else:
        raw_bytes = raw_message.encode("utf-8")
        message_text = raw_message
    message_size = len(raw_bytes)
    if max_payload is not None and message_size > max_payload:
        raise OpenClawCompatibilityError(
            f"OpenClaw frame exceeded hello-ok.policy.maxPayload={max_payload}"
        )
    try:
        payload = json.loads(message_text)
    except json.JSONDecodeError as exc:
        raise OpenClawProtocolError("OpenClaw gateway sent invalid JSON") from exc
    return parse_gateway_frame(payload), message_size


__all__ = [
    "receive_connect_challenge",
    "receive_frame",
]
