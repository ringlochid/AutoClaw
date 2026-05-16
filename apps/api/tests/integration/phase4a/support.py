from __future__ import annotations

import asyncio
import copy
import json
import os
import threading
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from app.config import OpenClawSettings, get_settings
from app.runtime.contracts import PromptFamily, PromptSendMode, PromptTransportRequest
from app.runtime.openclaw import OpenClawGatewayAdapter, OpenClawLaunchRequest
from app.runtime.openclaw.fixtures import (
    agent_accepted_fixture,
    agent_wait_fixture,
    connect_challenge_fixture,
    hello_ok_fixture,
    sessions_abort_fixture,
)
from app.runtime.openclaw.request_builders import agent_scoped_openclaw_session_key
from pytest import MonkeyPatch
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed


@dataclass(frozen=True)
class GatewayRequestRecord:
    method: str
    params: dict[str, Any]
    request_id: str


class LocalGatewayTestServer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: list[GatewayRequestRecord] = []
        self._default_method_payloads: dict[str, dict[str, Any]] = {}
        self._queued_method_payloads: dict[str, list[dict[str, Any]]] = {}
        self._run_counter = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_future: asyncio.Future[None] | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._base_url = ""

    @property
    def base_url(self) -> str:
        if not self._base_url:
            raise RuntimeError("gateway test server is not started")
        return self._base_url

    @property
    def requests(self) -> tuple[GatewayRequestRecord, ...]:
        with self._lock:
            return tuple(self._requests)

    def clear_requests(self) -> None:
        with self._lock:
            self._requests.clear()
            self._default_method_payloads.clear()
            self._queued_method_payloads.clear()
            self._run_counter = 0

    def set_default_method_payload(self, method: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._default_method_payloads[method] = copy.deepcopy(payload)

    def clear_default_method_payload(self, method: str) -> None:
        with self._lock:
            self._default_method_payloads.pop(method, None)

    def queue_method_payloads(self, method: str, *payloads: dict[str, Any]) -> None:
        with self._lock:
            queue = self._queued_method_payloads.setdefault(method, [])
            queue.extend(copy.deepcopy(payload) for payload in payloads)

    def start(self) -> None:
        if self._thread is not None:
            return
        thread = threading.Thread(target=self._run, name="openclaw-test-gateway", daemon=True)
        thread.start()
        self._thread = thread
        if not self._started.wait(timeout=5):
            raise RuntimeError("gateway test server did not start")

    def close(self) -> None:
        if self._thread is None or self._loop is None or self._stop_future is None:
            return
        if not self._stop_future.done():
            self._loop.call_soon_threadsafe(self._stop_future.set_result, None)
        self._thread.join(timeout=5)
        self._thread = None
        self._loop = None
        self._stop_future = None
        self._base_url = ""
        self._started.clear()

    @contextmanager
    def configured_env(self) -> Iterator[None]:
        overrides = {
            "AUTOCLAW_OPENCLAW__BASE_URL": self.base_url,
            "AUTOCLAW_OPENCLAW__GATEWAY_TOKEN": "gateway-config-token",
            "AUTOCLAW_OPENCLAW__AGENT_ID": "autoclaw-worker",
        }
        previous: dict[str, str | None] = {key: os.environ.get(key) for key in overrides}
        try:
            for key, value in overrides.items():
                os.environ[key] = value
            get_settings.cache_clear()
            yield
        finally:
            for key, previous_value in previous.items():
                if previous_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = previous_value
            get_settings.cache_clear()

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._serve())
        loop.close()

    async def _serve(self) -> None:
        async with serve(self._handle_connection, "127.0.0.1", 0) as server:
            sockets = server.server.sockets
            if sockets is None:
                raise RuntimeError("gateway test server did not bind a socket")
            host, port = sockets[0].getsockname()[:2]
            self._base_url = f"http://{host}:{port}"
            self._stop_future = asyncio.get_running_loop().create_future()
            self._started.set()
            await self._stop_future

    async def _handle_connection(self, connection: ServerConnection) -> None:
        await self._send_json(connection, connect_challenge_fixture())
        connect_request = await self._recv_json(connection)
        hello_ok = hello_ok_fixture(device_token="device-token-test")
        hello_ok["id"] = connect_request["id"]
        await self._send_json(connection, hello_ok)

        try:
            request = await self._recv_json(connection)
        except ConnectionClosed:
            return
        self._record_request(request)
        response = self._response_for_request(request)
        if response is not None:
            response["id"] = request["id"]
            await self._send_json(connection, response)
            return
        raise AssertionError(f"unexpected gateway method '{request['method']}'")

    def _next_run_id(self) -> str:
        with self._lock:
            self._run_counter += 1
            return f"run-{self._run_counter}"

    def _record_request(self, request: dict[str, Any]) -> None:
        with self._lock:
            self._requests.append(
                GatewayRequestRecord(
                    method=str(request["method"]),
                    params=dict(request["params"]),
                    request_id=str(request["id"]),
                )
            )

    def _response_for_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = str(request["method"])
        with self._lock:
            queued = self._queued_method_payloads.get(method)
            if queued:
                return self._normalize_method_payload(
                    method,
                    request,
                    copy.deepcopy(queued.pop(0)),
                )
            default = self._default_method_payloads.get(method)
            if default is not None:
                return self._normalize_method_payload(
                    method,
                    request,
                    copy.deepcopy(default),
                )
        if method == "agent":
            response = agent_accepted_fixture()
            response["payload"]["runId"] = self._next_run_id()
            return response
        if method == "agent.wait":
            params = cast(dict[str, Any], request["params"])
            return agent_wait_fixture(status="ok", run_id=str(params["runId"]))
        if method == "sessions.abort":
            return sessions_abort_fixture()
        return None

    def _normalize_method_payload(
        self,
        method: str,
        request: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if method != "agent.wait":
            return payload
        request_run_id = str(cast(dict[str, Any], request["params"])["runId"])
        response_payload = payload.get("payload")
        if not isinstance(response_payload, dict):
            return payload
        response_run_id = response_payload.get("runId")
        if response_run_id in {None, "run-123"}:
            response_payload["runId"] = request_run_id
        return payload

    async def _send_json(self, connection: ServerConnection, payload: dict[str, Any]) -> None:
        await connection.send(json.dumps(payload))

    async def _recv_json(self, connection: ServerConnection) -> dict[str, Any]:
        message = await connection.recv()
        assert isinstance(message, str)
        payload = json.loads(message)
        assert isinstance(payload, dict)
        return payload


@asynccontextmanager
async def gateway_server(
    handler: Callable[[ServerConnection], Awaitable[None]],
) -> AsyncIterator[str]:
    async with serve(handler, "127.0.0.1", 0) as server:
        sockets = server.server.sockets
        assert sockets is not None
        host, port = sockets[0].getsockname()[:2]
        yield f"http://{host}:{port}"


async def recv_json(connection: ServerConnection) -> dict[str, Any]:
    message = await connection.recv()
    assert isinstance(message, str)
    return cast(dict[str, Any], json.loads(message))


async def send_json(connection: ServerConnection, payload: dict[str, Any]) -> None:
    await connection.send(json.dumps(payload))


def hello_ok_without(*path: str) -> dict[str, Any]:
    payload = hello_ok_fixture()
    current: dict[str, Any] = payload
    for key in path[:-1]:
        current = cast(dict[str, Any], current[key])
    current.pop(path[-1], None)
    return payload


def build_test_adapter(
    *,
    base_url: str,
    data_dir: Path,
    gateway_token: str | None = "gateway-config-token",
    agent_id: str | None = "worker-agent",
) -> OpenClawGatewayAdapter:
    settings_kwargs: dict[str, Any] = {
        "base_url": base_url,
        "timeout_ms": 5000,
    }
    if gateway_token is not None:
        settings_kwargs["gateway_token"] = gateway_token
    if agent_id is not None:
        settings_kwargs["agent_id"] = agent_id
    return OpenClawGatewayAdapter(
        config=OpenClawSettings.model_validate(settings_kwargs),
        data_dir=data_dir,
    )


def build_test_launch_request(
    *,
    instructions_text: str = "system",
    input_text: str = "body",
) -> OpenClawLaunchRequest:
    session_key = agent_scoped_openclaw_session_key("session-123", "worker-agent")
    return OpenClawLaunchRequest(
        task_id="task-123",
        dispatch_id="dispatch-123",
        assignment_key="assignment-123",
        attempt_id="attempt-123",
        node_key="worker-node",
        session_key=session_key,
        prompt_name=PromptFamily.WORKER_DISPATCH,
        transport_request=PromptTransportRequest(
            send_mode=PromptSendMode.FULL_PROMPT,
            instructions_text=instructions_text,
            input_text=input_text,
        ),
        idempotency_key="dispatch:dispatch-123",
    )


def configure_gateway_env(
    monkeypatch: MonkeyPatch,
    *,
    tmp_path: Path,
    base_url: str,
) -> None:
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", base_url)
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__GATEWAY_TOKEN", "gateway-config-token")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__AGENT_ID", "autoclaw-worker")
    monkeypatch.setenv("AUTOCLAW_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()


def save_cached_auth_state(auth_state_path: Path) -> None:
    from app.runtime.openclaw.auth_state import (
        StoredDeviceToken,
        StoredGatewayAuthState,
        save_gateway_auth_state,
    )

    save_gateway_auth_state(
        auth_state_path,
        StoredGatewayAuthState(
            primary_token=StoredDeviceToken(
                device_token="device-token-cached",
                role="operator",
                scopes=("operator.read", "operator.write"),
            )
        ),
    )


__all__ = [
    "GatewayRequestRecord",
    "LocalGatewayTestServer",
    "build_test_adapter",
    "build_test_launch_request",
    "configure_gateway_env",
    "gateway_server",
    "hello_ok_without",
    "recv_json",
    "save_cached_auth_state",
    "send_json",
]
