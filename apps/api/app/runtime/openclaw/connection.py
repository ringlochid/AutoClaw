from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from pydantic import ValidationError
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import WebSocketException
from websockets.typing import Origin

from app.config import OpenClawSettings
from app.runtime.openclaw.auth_state import (
    StoredGatewayAuthState,
    load_gateway_auth_state,
    save_gateway_auth_state,
)
from app.runtime.openclaw.contracts import (
    OpenClawAuthError,
    OpenClawCompatibilityError,
    OpenClawCompatibilityReport,
    OpenClawConfigurationError,
    OpenClawProtocolError,
    OpenClawTransportError,
    gateway_ws_url_from_base_url,
)
from app.runtime.openclaw.discovery import discover_openclaw_host_state
from app.runtime.openclaw.handshake import (
    is_direct_loopback_openclaw_gateway,
    resolve_local_openclaw_gateway_token,
)
from app.runtime.openclaw.protocol import (
    OpenClawGatewayError,
    OpenClawGatewayEventFrame,
    OpenClawGatewayResponseEnvelope,
    OpenClawHelloOkPayload,
    parse_response_payload,
)
from app.runtime.openclaw.request_builders import (
    build_gateway_auth_state,
    build_openclaw_compatibility_report,
    build_openclaw_connect_request,
    next_openclaw_request_id,
    serialize_openclaw_gateway_request,
)
from app.runtime.openclaw.transport import receive_connect_challenge, receive_frame


async def open_gateway_connection(
    *,
    config: OpenClawSettings,
    auth_state_path: Path,
) -> tuple[ClientConnection, OpenClawCompatibilityReport]:
    host_state = discover_openclaw_host_state(config)
    auth_state = load_gateway_auth_state(auth_state_path)
    if host_state.support_status != "supported":
        if (
            auth_state is not None
            and auth_state.primary_token is not None
            and host_state.reason
            in {
                "NO_SUPPORTED_GATEWAY_AUTH",
                "MISSING_GATEWAY_TOKEN",
                "MISSING_GATEWAY_PASSWORD",
                "UNRESOLVED_GATEWAY_TOKEN",
                "UNRESOLVED_GATEWAY_PASSWORD",
                "UNRESOLVED_GATEWAY_SECRET_REF",
            }
        ):
            return await _open_with_retry(
                config=config,
                auth_state_path=auth_state_path,
                ws_url=gateway_ws_url_from_base_url(config.base_url),
                auth_state=auth_state,
            )
        raise OpenClawConfigurationError(
            f"OpenClaw host shape is unsupported for AutoClaw: {host_state.reason or 'unknown'}"
        )
    ws_url = gateway_ws_url_from_base_url(config.base_url)
    return await _open_with_retry(
        config=config,
        auth_state_path=auth_state_path,
        ws_url=ws_url,
        auth_state=auth_state,
    )


async def _open_with_retry(
    *,
    config: OpenClawSettings,
    auth_state_path: Path,
    ws_url: str,
    auth_state: StoredGatewayAuthState | None,
) -> tuple[ClientConnection, OpenClawCompatibilityReport]:
    attempted_shared_gateway_token = bool(config.gateway_token)
    can_retry_with_cached_token = attempted_shared_gateway_token and (
        auth_state is not None and auth_state.primary_token is not None
    )
    local_gateway_token = None
    if is_direct_loopback_openclaw_gateway(config.base_url):
        local_gateway_token = resolve_local_openclaw_gateway_token()

    try:
        return await _connect_and_handshake(
            config=config,
            auth_state_path=auth_state_path,
            ws_url=ws_url,
            use_cached_device_token=False,
            auth_state=auth_state,
        )
    except OpenClawAuthError as exc:
        if not is_auth_token_mismatch(exc):
            raise

    if local_gateway_token and local_gateway_token != config.gateway_token:
        return await _retry_connect(
            config=config,
            auth_state_path=auth_state_path,
            ws_url=ws_url,
            auth_state=auth_state,
            use_cached_device_token=False,
            gateway_token_override=local_gateway_token,
        )
    if not can_retry_with_cached_token:
        raise OpenClawAuthError("AUTH_TOKEN_MISMATCH")
    return await _retry_connect(
        config=config,
        auth_state_path=auth_state_path,
        ws_url=ws_url,
        auth_state=auth_state,
        use_cached_device_token=True,
    )


async def _retry_connect(
    *,
    config: OpenClawSettings,
    auth_state_path: Path,
    ws_url: str,
    auth_state: StoredGatewayAuthState | None,
    use_cached_device_token: bool,
    gateway_token_override: str | None = None,
) -> tuple[ClientConnection, OpenClawCompatibilityReport]:
    return await _connect_and_handshake(
        config=config,
        auth_state_path=auth_state_path,
        ws_url=ws_url,
        use_cached_device_token=use_cached_device_token,
        auth_state=auth_state,
        gateway_token_override=gateway_token_override,
    )


def _loopback_origin(base_url: str) -> str | None:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        return None
    origin = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port is not None:
        origin = f"{origin}:{parsed.port}"
    return origin


async def _connect_and_handshake(
    *,
    config: OpenClawSettings,
    auth_state_path: Path,
    ws_url: str,
    use_cached_device_token: bool,
    auth_state: StoredGatewayAuthState | None,
    gateway_token_override: str | None = None,
) -> tuple[ClientConnection, OpenClawCompatibilityReport]:
    timeout_seconds = config.timeout_ms / 1000
    origin = _loopback_origin(config.base_url)
    try:
        connection = await connect(
            ws_url,
            open_timeout=timeout_seconds,
            close_timeout=timeout_seconds,
            ping_interval=None,
            origin=cast(Origin | None, origin),
        )
    except (OSError, WebSocketException) as exc:
        raise OpenClawTransportError(f"failed to connect to OpenClaw gateway at {ws_url}") from exc
    try:
        challenge = await receive_connect_challenge(connection)
        connect_request = build_openclaw_connect_request(
            config=config,
            challenge=challenge,
            request_id=next_openclaw_request_id("connect"),
            auth_state=auth_state,
            use_cached_device_token=use_cached_device_token,
            gateway_token_override=gateway_token_override,
        )
        response = await _request_during_handshake(
            connection=connection,
            action=lambda: connection.send(serialize_openclaw_gateway_request(connect_request)),
            expected_id=connect_request.id,
        )
        if not response.ok:
            error = response.error or OpenClawGatewayError(message="unknown gateway auth error")
            if error.details and error.details.code == "AUTH_TOKEN_MISMATCH":
                raise OpenClawAuthError("AUTH_TOKEN_MISMATCH")
            raise OpenClawAuthError(error.message)
        try:
            hello_ok = parse_response_payload(response, OpenClawHelloOkPayload)
        except ValidationError as exc:
            raise hello_ok_compatibility_error(exc) from exc
        compatibility = build_openclaw_compatibility_report(
            ws_url=ws_url,
            hello_ok=hello_ok,
            retry_used_cached_device_token=use_cached_device_token,
        )
        persist_gateway_auth_state(
            hello_ok=hello_ok,
            ws_url=ws_url,
            auth_state_path=auth_state_path,
        )
        return connection, compatibility
    except Exception:
        await connection.close()
        raise


async def _request_during_handshake(
    *,
    connection: ClientConnection,
    action: Callable[[], Awaitable[None]],
    expected_id: str,
) -> OpenClawGatewayResponseEnvelope:
    await action()
    while True:
        frame, _frame_size = await receive_frame(connection)
        if isinstance(frame, OpenClawGatewayEventFrame):
            continue
        if frame.id != expected_id:
            raise OpenClawProtocolError(
                f"expected gateway response id '{expected_id}', received '{frame.id}'"
            )
        return frame


def persist_gateway_auth_state(
    *,
    hello_ok: OpenClawHelloOkPayload,
    ws_url: str,
    auth_state_path: Path,
) -> None:
    state = build_gateway_auth_state(hello_ok=hello_ok, ws_url=ws_url)
    if state is None:
        return
    save_gateway_auth_state(auth_state_path, state)


def hello_ok_compatibility_error(exc: ValidationError) -> OpenClawCompatibilityError:
    first_error = exc.errors()[0] if exc.errors() else {"loc": ("payload",)}
    loc = ".".join(str(part) for part in first_error.get("loc", ()) if part != "payload")
    return OpenClawCompatibilityError(f"hello-ok.{loc or 'payload'}")


def is_auth_token_mismatch(exc: OpenClawAuthError) -> bool:
    return bool(exc.args) and "AUTH_TOKEN_MISMATCH" in exc.args[0]


__all__ = ["open_gateway_connection"]
