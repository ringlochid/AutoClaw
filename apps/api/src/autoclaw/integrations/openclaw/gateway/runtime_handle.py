from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from websockets.asyncio.client import ClientConnection

from autoclaw.config import OpenClawSettings
from autoclaw.integrations.openclaw.gateway.connection import open_gateway_connection
from autoclaw.integrations.openclaw.gateway.contracts import (
    OpenClawAbortRequest,
    OpenClawAbortResult,
    OpenClawAgentLaunchInput,
    OpenClawCompatibilityError,
    OpenClawCompatibilityReport,
    OpenClawLaunchResult,
    OpenClawObservedEvent,
    OpenClawProtocolError,
    OpenClawTransportError,
    OpenClawWaitRequest,
    OpenClawWaitResult,
)
from autoclaw.integrations.openclaw.gateway.protocol import (
    OpenClawAgentAcceptedPayload,
    OpenClawAgentRequest,
    OpenClawAgentWaitPayload,
    OpenClawAgentWaitRequest,
    OpenClawGatewayError,
    OpenClawGatewayEventFrame,
    OpenClawGatewayResponseEnvelope,
    OpenClawSessionsAbortRequest,
    parse_response_payload,
)
from autoclaw.integrations.openclaw.gateway.request_builders import (
    build_openclaw_abort_request,
    build_openclaw_agent_request,
    build_openclaw_wait_request,
    next_openclaw_request_id,
    serialize_openclaw_gateway_request,
)
from autoclaw.integrations.openclaw.gateway.transport import receive_frame
from autoclaw.integrations.openclaw.gateway.wait_normalization import normalize_gateway_wait_status

OpenClawGatewayRequest = (
    OpenClawAgentRequest | OpenClawAgentWaitRequest | OpenClawSessionsAbortRequest
)


@dataclass(frozen=True)
class _QueuedGatewayEvent:
    event: OpenClawObservedEvent
    frame_size: int


@dataclass(frozen=True)
class OpenClawRequestDispatchError(Exception):
    error: Exception
    request_sent: bool

    def __str__(self) -> str:
        return str(self.error)


class OpenClawGatewayRuntimeHandle:
    def __init__(
        self,
        *,
        config: OpenClawSettings,
        auth_state_path: Path,
    ) -> None:
        self._config = config
        self._auth_state_path = auth_state_path
        self._connection: ClientConnection | None = None
        self._compatibility: OpenClawCompatibilityReport | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._pending_responses: dict[str, asyncio.Future[OpenClawGatewayResponseEnvelope]] = {}
        self._pending_agent_session_keys: dict[str, str] = {}
        self._ignored_followup_response_ids: set[str] = set()
        self._event_scope_run_id: str | None = None
        self._event_scope_session_key: str | None = None
        self._queued_events: asyncio.Queue[_QueuedGatewayEvent] = asyncio.Queue()
        self._queued_event_bytes = 0
        self._terminal_error: Exception | None = None

    async def open(self) -> None:
        self._connection, self._compatibility = await open_gateway_connection(
            config=self._config,
            auth_state_path=self._auth_state_path,
        )
        self._reader_task = asyncio.create_task(
            self._reader_loop(),
            name="openclaw-gateway-runtime-reader",
        )

    async def close(self) -> None:
        close_error = OpenClawTransportError("OpenClaw gateway runtime handle closed")
        self._fail_pending(close_error)
        reader_task = self._reader_task
        self._reader_task = None
        if reader_task is not None:
            reader_task.cancel()
            with suppress(asyncio.CancelledError):
                await reader_task
        connection = self._connection
        self._connection = None
        if connection is not None:
            await connection.close()

    def require_compatibility(self) -> OpenClawCompatibilityReport:
        if self._compatibility is None:
            raise OpenClawTransportError(
                "OpenClaw gateway session compatibility was not established"
            )
        return self._compatibility

    async def launch_run(self, request: OpenClawAgentLaunchInput) -> OpenClawLaunchResult:
        try:
            response, _request_sent = await self.send_agent_launch_request_with_tracking(request)
        except OpenClawRequestDispatchError as exc:
            raise exc.error from exc
        accepted = parse_response_payload(response, OpenClawAgentAcceptedPayload)
        return OpenClawLaunchResult(
            session_key=request.session_key,
            run_id=accepted.run_id,
            accepted_at=accepted.accepted_at,
            compatibility=self.require_compatibility(),
        )

    async def send_agent_launch_request_with_tracking(
        self,
        request: OpenClawAgentLaunchInput,
    ) -> tuple[OpenClawGatewayResponseEnvelope, bool]:
        response, request_sent = await self.send_request_with_tracking(
            build_openclaw_agent_request(
                request_id=next_openclaw_request_id("agent"),
                launch_input=request,
            )
        )
        if not should_retry_agent_without_extra_system_prompt(
            response,
            launch_input=request,
        ):
            return response, request_sent
        return await self.send_request_with_tracking(
            build_openclaw_agent_request(
                request_id=next_openclaw_request_id("agent"),
                launch_input=legacy_flattened_agent_launch_input(request),
            )
        )

    async def wait_for_run(self, request: OpenClawWaitRequest) -> OpenClawWaitResult:
        response = await self.send_request(
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
        ended_at = payload.ended_at or utc_now()
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
        )

    async def abort_run(self, request: OpenClawAbortRequest) -> OpenClawAbortResult:
        await self.send_request(
            build_openclaw_abort_request(
                request_id=next_openclaw_request_id("abort"),
                abort_request=request,
            )
        )
        return OpenClawAbortResult(
            accepted=True,
            session_key=request.session_key,
            run_id=request.run_id,
            compatibility=self.require_compatibility(),
        )

    async def send_request(
        self,
        request: OpenClawGatewayRequest,
    ) -> OpenClawGatewayResponseEnvelope:
        try:
            response, _request_sent = await self.send_request_with_tracking(request)
        except OpenClawRequestDispatchError as exc:
            raise exc.error from exc
        return response

    async def send_request_with_tracking(
        self,
        request: OpenClawGatewayRequest,
    ) -> tuple[OpenClawGatewayResponseEnvelope, bool]:
        connection = self._require_connection()
        compatibility = self.require_compatibility()
        self._raise_if_terminal_error()
        serialized_request = serialize_openclaw_gateway_request(request)
        max_payload = compatibility.max_payload
        if max_payload is not None and len(serialized_request.encode("utf-8")) > max_payload:
            raise OpenClawCompatibilityError(
                f"OpenClaw request exceeded hello-ok.policy.maxPayload={max_payload}"
            )
        if request.id in self._pending_responses:
            raise OpenClawProtocolError(f"duplicate in-flight gateway request id '{request.id}'")
        agent_session_key = agent_request_session_key(request)
        response_future = asyncio.get_running_loop().create_future()
        self._pending_responses[request.id] = response_future
        if agent_session_key is not None:
            self._event_scope_session_key = agent_session_key
            self._pending_agent_session_keys[request.id] = agent_session_key
            self._ignored_followup_response_ids.add(request.id)
        try:
            await connection.send(serialized_request)
        except Exception as exc:
            self._pending_responses.pop(request.id, None)
            self._pending_agent_session_keys.pop(request.id, None)
            if agent_session_key is not None and self._event_scope_run_id is None:
                self._event_scope_session_key = None
            raise OpenClawRequestDispatchError(error=exc, request_sent=False) from exc
        try:
            response = await response_future
            self._raise_if_terminal_error()
        except Exception as exc:
            raise OpenClawRequestDispatchError(error=exc, request_sent=True) from exc
        finally:
            self._pending_responses.pop(request.id, None)
            self._pending_agent_session_keys.pop(request.id, None)
        return cast(OpenClawGatewayResponseEnvelope, response), True

    async def next_event(
        self,
        *,
        timeout_seconds: float | None = None,
    ) -> OpenClawObservedEvent | None:
        self._raise_if_terminal_error()
        try:
            if timeout_seconds is None:
                queued_event = await self._queued_events.get()
            else:
                queued_event = await asyncio.wait_for(
                    self._queued_events.get(),
                    timeout=timeout_seconds,
                )
        except TimeoutError:
            self._raise_if_terminal_error()
            return None
        self._queued_event_bytes -= queued_event.frame_size
        return queued_event.event

    async def _reader_loop(self) -> None:
        compatibility = self.require_compatibility()
        connection = self._require_connection()
        try:
            while True:
                frame, frame_size = await receive_frame(
                    connection,
                    max_payload=compatibility.max_payload,
                )
                if isinstance(frame, OpenClawGatewayEventFrame):
                    self._queue_event(
                        frame=frame,
                        frame_size=frame_size,
                        compatibility=compatibility,
                    )
                    continue
                if self._deliver_response(frame):
                    continue
                raise OpenClawProtocolError(
                    f"unexpected gateway response id '{frame.id}' with no matching request"
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._terminal_error = exc
            self._fail_pending(exc)
            with suppress(Exception):
                await connection.close()

    def _queue_event(
        self,
        *,
        frame: OpenClawGatewayEventFrame,
        frame_size: int,
        compatibility: OpenClawCompatibilityReport,
    ) -> None:
        if not self._event_matches_bound_run_scope(frame):
            return
        next_buffered_bytes = self._queued_event_bytes + frame_size
        max_buffered_bytes = compatibility.max_buffered_bytes
        if max_buffered_bytes is not None and next_buffered_bytes > max_buffered_bytes:
            raise OpenClawCompatibilityError(
                "OpenClaw event buffering exceeded "
                f"hello-ok.policy.maxBufferedBytes={max_buffered_bytes}"
            )
        observed_event = OpenClawObservedEvent.model_validate(
            {
                "event": frame.event,
                "payload": frame.payload,
                "seq": frame.seq,
                "stateVersion": frame.state_version,
            }
        )
        self._queued_events.put_nowait(
            _QueuedGatewayEvent(event=observed_event, frame_size=frame_size)
        )
        self._queued_event_bytes = next_buffered_bytes

    def _deliver_response(self, frame: OpenClawGatewayResponseEnvelope) -> bool:
        future = self._pending_responses.get(frame.id)
        if future is not None and not future.done():
            self._bind_accepted_run_event_scope(frame)
            future.set_result(frame)
            return True
        return frame.id in self._ignored_followup_response_ids

    def _bind_accepted_run_event_scope(
        self,
        frame: OpenClawGatewayResponseEnvelope,
    ) -> None:
        session_key = self._pending_agent_session_keys.get(frame.id)
        if session_key is None or not frame.ok or frame.payload is None:
            return
        if payload_string(frame.payload, "status") != "accepted":
            return
        run_id = payload_string(frame.payload, "runId", "run_id")
        if run_id is None:
            return
        self._event_scope_run_id = run_id
        self._event_scope_session_key = session_key

    def _event_matches_bound_run_scope(self, frame: OpenClawGatewayEventFrame) -> bool:
        if self._event_scope_run_id is None:
            return False
        frame_run_id = payload_string(frame.payload, "runId", "run_id")
        if frame_run_id != self._event_scope_run_id:
            return False
        frame_session_key = payload_string(frame.payload, "sessionKey", "session_key", "key")
        if frame_session_key is None or self._event_scope_session_key is None:
            return True
        return session_keys_equal(frame_session_key, self._event_scope_session_key)

    def _require_connection(self) -> ClientConnection:
        if self._connection is None:
            raise OpenClawTransportError("OpenClaw gateway session is not connected")
        return self._connection

    def _raise_if_terminal_error(self) -> None:
        if self._terminal_error is None:
            return
        raise self._terminal_error

    def _fail_pending(self, error: Exception) -> None:
        for future in self._pending_responses.values():
            if not future.done():
                future.set_exception(error)
        self._pending_responses.clear()


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def agent_request_session_key(request: OpenClawGatewayRequest) -> str | None:
    if request.method != "agent":
        return None
    return request.params.session_key


def payload_string(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def session_keys_equal(left: str, right: str) -> bool:
    return left.strip().lower() == right.strip().lower()


def should_retry_agent_without_extra_system_prompt(
    response: OpenClawGatewayResponseEnvelope,
    *,
    launch_input: OpenClawAgentLaunchInput,
) -> bool:
    if response.ok or response.error is None:
        return False
    if launch_input.extra_system_prompt is None or launch_input.flattened_message_fallback is None:
        return False
    return gateway_error_rejects_extra_system_prompt(response.error)


def gateway_error_rejects_extra_system_prompt(error: OpenClawGatewayError) -> bool:
    detail_code = "" if error.details is None or error.details.code is None else error.details.code
    text = " ".join(part.lower() for part in (error.code or "", detail_code, error.message) if part)
    return "extrasystemprompt" in text and any(
        marker in text
        for marker in (
            "additional",
            "invalid",
            "not allowed",
            "unexpected",
            "unknown",
            "unrecognized",
            "unsupported",
        )
    )


def legacy_flattened_agent_launch_input(
    request: OpenClawAgentLaunchInput,
) -> OpenClawAgentLaunchInput:
    if request.flattened_message_fallback is None:
        raise OpenClawProtocolError("flattened message fallback is required")
    return request.model_copy(
        update={
            "message": request.flattened_message_fallback,
            "extra_system_prompt": None,
            "flattened_message_fallback": None,
        }
    )


__all__ = ["OpenClawGatewayRuntimeHandle", "OpenClawRequestDispatchError"]
