from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from websockets.asyncio.client import ClientConnection

from app.config import OpenClawSettings
from app.runtime.openclaw.connection import open_gateway_connection
from app.runtime.openclaw.contracts import (
    OpenClawAbortRequest,
    OpenClawAbortResult,
    OpenClawCompatibilityError,
    OpenClawCompatibilityReport,
    OpenClawLaunchRequest,
    OpenClawLaunchResult,
    OpenClawObservedEvent,
    OpenClawProtocolError,
    OpenClawTransportError,
    OpenClawWaitRequest,
    OpenClawWaitResult,
)
from app.runtime.openclaw.protocol import (
    OpenClawAgentAcceptedPayload,
    OpenClawAgentRequest,
    OpenClawAgentWaitPayload,
    OpenClawAgentWaitRequest,
    OpenClawGatewayEventFrame,
    OpenClawGatewayResponseEnvelope,
    OpenClawSessionsAbortRequest,
    parse_response_payload,
)
from app.runtime.openclaw.request_builders import (
    agent_scoped_openclaw_session_key,
    build_openclaw_abort_request,
    build_openclaw_agent_request,
    build_openclaw_wait_request,
    next_openclaw_request_id,
    serialize_openclaw_gateway_request,
)
from app.runtime.openclaw.transport import receive_frame
from app.runtime.openclaw.wait_normalization import normalize_gateway_wait_status

OpenClawGatewayRequest = (
    OpenClawAgentRequest | OpenClawAgentWaitRequest | OpenClawSessionsAbortRequest
)


@dataclass(frozen=True)
class _QueuedGatewayEvent:
    event: OpenClawObservedEvent
    frame_size: int


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
        self._ignored_followup_response_ids: set[str] = set()
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

    async def launch_run(self, request: OpenClawLaunchRequest) -> OpenClawLaunchResult:
        response, _observed_events = await self.send_request(
            build_openclaw_agent_request(
                config=self._config,
                request_id=next_openclaw_request_id("agent"),
                launch_request=request,
            )
        )
        accepted = parse_response_payload(response, OpenClawAgentAcceptedPayload)
        session_key = agent_scoped_openclaw_session_key(request.session_key, self._config.agent_id)
        return OpenClawLaunchResult(
            session_key=session_key,
            run_id=accepted.run_id,
            accepted_at=accepted.accepted_at,
            compatibility=self.require_compatibility(),
            observed_events=(),
        )

    async def wait_for_run(self, request: OpenClawWaitRequest) -> OpenClawWaitResult:
        response, _observed_events = await self.send_request(
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
            observed_events=(),
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
            observed_events=(),
        )

    async def send_request(
        self,
        request: OpenClawGatewayRequest,
    ) -> tuple[OpenClawGatewayResponseEnvelope, tuple[OpenClawObservedEvent, ...]]:
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
        response_future = asyncio.get_running_loop().create_future()
        self._pending_responses[request.id] = response_future
        if request.method == "agent":
            self._ignored_followup_response_ids.add(request.id)
        try:
            await connection.send(serialized_request)
        except Exception:
            self._pending_responses.pop(request.id, None)
            raise
        try:
            response = await response_future
        finally:
            self._pending_responses.pop(request.id, None)
        self._raise_if_terminal_error()
        return response, ()

    def drain_events(self) -> tuple[OpenClawObservedEvent, ...]:
        observed_events: list[OpenClawObservedEvent] = []
        while True:
            try:
                queued_event = self._queued_events.get_nowait()
            except asyncio.QueueEmpty:
                break
            self._queued_event_bytes -= queued_event.frame_size
            observed_events.append(queued_event.event)
        return tuple(observed_events)

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
            future.set_result(frame)
            return True
        return frame.id in self._ignored_followup_response_ids

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

    async def _close_connection(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            await connection.close()


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


__all__ = ["OpenClawGatewayRuntimeHandle"]
