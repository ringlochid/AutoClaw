from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import WebSocketException

from app.config import OpenClawSettings, Settings, get_settings
from app.runtime.openclaw.auth_state import (
    StoredGatewayAuthState,
    load_gateway_auth_state,
    save_gateway_auth_state,
)
from app.runtime.openclaw.contracts import (
    OpenClawAbortRequest,
    OpenClawAbortResult,
    OpenClawAuthError,
    OpenClawCompatibilityError,
    OpenClawCompatibilityReport,
    OpenClawLaunchRequest,
    OpenClawLaunchResult,
    OpenClawObservedEvent,
    OpenClawProtocolError,
    OpenClawTransportError,
    OpenClawWaitRequest,
    OpenClawWaitResult,
    gateway_ws_url_from_base_url,
)
from app.runtime.openclaw.handshake import (
    is_direct_loopback_openclaw_gateway,
    resolve_local_openclaw_gateway_token,
)
from app.runtime.openclaw.protocol import (
    OpenClawAgentAcceptedPayload,
    OpenClawAgentRequest,
    OpenClawAgentWaitPayload,
    OpenClawAgentWaitRequest,
    OpenClawGatewayError,
    OpenClawGatewayResponseEnvelope,
    OpenClawHelloOkPayload,
    OpenClawSessionsAbortRequest,
    parse_response_payload,
)
from app.runtime.openclaw.request_builders import (
    agent_scoped_openclaw_session_key,
    build_gateway_auth_state,
    build_openclaw_abort_request,
    build_openclaw_agent_request,
    build_openclaw_compatibility_report,
    build_openclaw_connect_request,
    build_openclaw_wait_request,
    next_openclaw_request_id,
    serialize_openclaw_gateway_request,
)
from app.runtime.openclaw.transport import receive_connect_challenge, receive_response
from app.runtime.openclaw.wait_normalization import normalize_gateway_wait_status


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
        async with self.gateway_session() as session:
            return session.require_compatibility()

    async def launch_run(self, request: OpenClawLaunchRequest) -> OpenClawLaunchResult:
        async with self.gateway_session() as session:
            response, observed_events = await session.send_request(
                build_openclaw_agent_request(
                    config=self._config,
                    request_id=next_openclaw_request_id("agent"),
                    launch_request=request,
                )
            )
            accepted = parse_response_payload(response, OpenClawAgentAcceptedPayload)
            session_key = agent_scoped_openclaw_session_key(
                request.session_key,
                self._config.agent_id,
            )
            return OpenClawLaunchResult(
                session_key=session_key,
                run_id=accepted.run_id,
                accepted_at=accepted.accepted_at,
                compatibility=session.require_compatibility(),
                observed_events=tuple(observed_events),
            )

    async def wait_for_run(self, request: OpenClawWaitRequest) -> OpenClawWaitResult:
        async with self.gateway_session() as session:
            response, observed_events = await session.send_request(
                build_openclaw_wait_request(
                    request_id=next_openclaw_request_id("wait"),
                    wait_request=request,
                )
            )
            payload = parse_response_payload(response, OpenClawAgentWaitPayload)
            if payload.run_id != request.run_id:
                raise OpenClawProtocolError(
                    f"expected gateway wait runId '{request.run_id}', received '{payload.run_id}'"
                )
            ended_at = payload.ended_at or datetime.now(tz=UTC)
            normalized_status = normalize_gateway_wait_status(payload)
            return OpenClawWaitResult(
                status=normalized_status,
                started_at=payload.started_at or ended_at,
                ended_at=ended_at,
                error=payload.error,
                gateway_status=payload.status,
                stop_reason=payload.stop_reason,
                liveness_state=payload.liveness_state,
                aborted=payload.aborted,
                yielded=payload.yielded,
                observed_events=tuple(observed_events),
            )

    async def abort_run(self, request: OpenClawAbortRequest) -> OpenClawAbortResult:
        async with self.gateway_session() as session:
            await session.send_request(
                build_openclaw_abort_request(
                    request_id=next_openclaw_request_id("abort"),
                    abort_request=request,
                )
            )
            return OpenClawAbortResult(
                accepted=True,
                session_key=request.session_key,
                run_id=request.run_id,
                compatibility=session.require_compatibility(),
            )

    @asynccontextmanager
    async def gateway_session(self) -> AsyncIterator[_GatewaySession]:
        session = _GatewaySession(
            config=self._config,
            auth_state_path=self._auth_state_path,
        )
        try:
            await session.open()
            yield session
        finally:
            await session.close()


class _GatewaySession:
    def __init__(
        self,
        *,
        config: OpenClawSettings,
        auth_state_path: Path,
    ) -> None:
        self._config = config
        self._auth_state_path = auth_state_path
        self._connection: ClientConnection | None = None
        self.compatibility: OpenClawCompatibilityReport | None = None

    async def open(self) -> None:
        ws_url = gateway_ws_url_from_base_url(self._config.base_url)
        auth_state = load_gateway_auth_state(self._auth_state_path)
        compatibility = await self._open_with_retry(ws_url=ws_url, auth_state=auth_state)
        self.compatibility = compatibility

    async def close(self) -> None:
        if self._connection is None:
            return
        await self._connection.close()
        self._connection = None

    async def send_request(
        self,
        request: OpenClawAgentRequest | OpenClawAgentWaitRequest | OpenClawSessionsAbortRequest,
    ) -> tuple[OpenClawGatewayResponseEnvelope, tuple[OpenClawObservedEvent, ...]]:
        connection = self._require_connection()
        compatibility = self.require_compatibility()
        serialized_request = serialize_openclaw_gateway_request(request)
        max_payload = compatibility.max_payload
        if max_payload is not None and len(serialized_request.encode("utf-8")) > max_payload:
            raise OpenClawCompatibilityError(
                f"OpenClaw request exceeded hello-ok.policy.maxPayload={max_payload}"
            )
        await connection.send(serialized_request)
        response, observed_events = await receive_response(
            connection,
            expected_id=request.id,
            compatibility=compatibility,
        )
        return response, tuple(observed_events)

    async def _open_with_retry(
        self,
        *,
        ws_url: str,
        auth_state: StoredGatewayAuthState | None,
    ) -> OpenClawCompatibilityReport:
        attempted_shared_gateway_token = bool(self._config.gateway_token)
        can_retry_with_cached_token = attempted_shared_gateway_token and (
            auth_state is not None and auth_state.primary_token is not None
        )
        local_gateway_token = None
        if is_direct_loopback_openclaw_gateway(self._config.base_url):
            local_gateway_token = resolve_local_openclaw_gateway_token()

        try:
            return await self._connect_and_handshake(
                ws_url=ws_url,
                use_cached_device_token=False,
                auth_state=auth_state,
            )
        except OpenClawAuthError as exc:
            await self.close()
            if not is_auth_token_mismatch(exc):
                raise

        if local_gateway_token and local_gateway_token != self._config.gateway_token:
            return await self._retry_connect(
                ws_url=ws_url,
                auth_state=auth_state,
                use_cached_device_token=False,
                gateway_token_override=local_gateway_token,
            )
        if not can_retry_with_cached_token:
            raise OpenClawAuthError("AUTH_TOKEN_MISMATCH")
        return await self._retry_connect(
            ws_url=ws_url,
            auth_state=auth_state,
            use_cached_device_token=True,
        )

    async def _retry_connect(
        self,
        *,
        ws_url: str,
        auth_state: StoredGatewayAuthState | None,
        use_cached_device_token: bool,
        gateway_token_override: str | None = None,
    ) -> OpenClawCompatibilityReport:
        try:
            return await self._connect_and_handshake(
                ws_url=ws_url,
                use_cached_device_token=use_cached_device_token,
                auth_state=auth_state,
                gateway_token_override=gateway_token_override,
            )
        except OpenClawAuthError:
            await self.close()
            raise

    async def _connect_and_handshake(
        self,
        *,
        ws_url: str,
        use_cached_device_token: bool,
        auth_state: StoredGatewayAuthState | None,
        gateway_token_override: str | None = None,
    ) -> OpenClawCompatibilityReport:
        timeout_seconds = self._config.timeout_ms / 1000
        try:
            connection = await connect(
                ws_url,
                open_timeout=timeout_seconds,
                close_timeout=timeout_seconds,
                ping_interval=None,
            )
        except (OSError, WebSocketException) as exc:
            raise OpenClawTransportError(
                f"failed to connect to OpenClaw gateway at {ws_url}"
            ) from exc
        self._connection = connection
        try:
            challenge = await receive_connect_challenge(connection)
            connect_request = build_openclaw_connect_request(
                config=self._config,
                challenge=challenge,
                request_id=next_openclaw_request_id("connect"),
                auth_state=auth_state,
                use_cached_device_token=use_cached_device_token,
                gateway_token_override=gateway_token_override,
            )
            await connection.send(serialize_openclaw_gateway_request(connect_request))
            envelope, _observed_events = await receive_response(
                connection,
                expected_id=connect_request.id,
            )
            if not envelope.ok:
                error = envelope.error or OpenClawGatewayError(message="unknown gateway auth error")
                if error.details and error.details.code == "AUTH_TOKEN_MISMATCH":
                    raise OpenClawAuthError("AUTH_TOKEN_MISMATCH")
                raise OpenClawAuthError(error.message)
            try:
                hello_ok = parse_response_payload(envelope, OpenClawHelloOkPayload)
            except ValidationError as exc:
                raise hello_ok_compatibility_error(exc) from exc
            compatibility = build_openclaw_compatibility_report(
                ws_url=ws_url,
                hello_ok=hello_ok,
                retry_used_cached_device_token=use_cached_device_token,
            )
            self._persist_auth_state(hello_ok, ws_url)
            return compatibility
        except Exception:
            await connection.close()
            self._connection = None
            raise

    def _persist_auth_state(self, hello_ok: OpenClawHelloOkPayload, ws_url: str) -> None:
        state = build_gateway_auth_state(hello_ok=hello_ok, ws_url=ws_url)
        if state is None:
            return
        save_gateway_auth_state(self._auth_state_path, state)

    def _require_connection(self) -> ClientConnection:
        if self._connection is None:
            raise OpenClawTransportError("OpenClaw gateway session is not connected")
        self.require_compatibility()
        return self._connection

    def require_compatibility(self) -> OpenClawCompatibilityReport:
        if self.compatibility is None:
            raise OpenClawTransportError(
                "OpenClaw gateway session compatibility was not established"
            )
        return self.compatibility


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


def hello_ok_compatibility_error(exc: ValidationError) -> OpenClawCompatibilityError:
    first_error = exc.errors()[0] if exc.errors() else {"loc": ("payload",)}
    loc = ".".join(str(part) for part in first_error.get("loc", ()) if part != "payload")
    return OpenClawCompatibilityError(f"hello-ok.{loc or 'payload'}")


def is_auth_token_mismatch(exc: OpenClawAuthError) -> bool:
    return bool(exc.args) and "AUTH_TOKEN_MISMATCH" in exc.args[0]


__all__ = [
    "OpenClawGatewayAdapter",
    "build_openclaw_gateway_adapter",
    "openclaw_startup_compatibility_required",
]
