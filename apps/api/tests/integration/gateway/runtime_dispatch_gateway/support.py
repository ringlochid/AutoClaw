from __future__ import annotations

from collections.abc import Callable

from autoclaw.integrations.openclaw.gateway.contracts import OpenClawAgentLaunchInput
from autoclaw.integrations.openclaw.gateway.fixtures import (
    connect_challenge_fixture,
    hello_ok_fixture,
)
from autoclaw.integrations.openclaw.gateway.protocol import OpenClawAgentRequest
from tests.helpers.openclaw_gateway_support import GatewayRequestRecord, recv_json, send_json
from tests.integration.gateway.dispatch_gateway_support import DispatchGatewaySnapshot
from websockets.asyncio.server import ServerConnection
from websockets.exceptions import ConnectionClosed


def assert_gateway_launch_snapshot(
    snapshot: DispatchGatewaySnapshot,
    *,
    recorded_launch_requests: list[tuple[str, OpenClawAgentLaunchInput]],
    original_builder: Callable[..., OpenClawAgentRequest],
    observed_requests: tuple[GatewayRequestRecord, ...],
) -> None:
    assert snapshot.delivery_state is not None
    assert snapshot.continuity_state is not None
    assert snapshot.node_session is not None
    assert snapshot.dispatch.gateway_session_key is not None
    assert snapshot.dispatch.gateway_run_id == "run-1"
    assert snapshot.node_session.session_key == snapshot.dispatch.gateway_session_key
    assert snapshot.node_session.session_status == "live"
    assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
    assert snapshot.delivery_state.transport_state == "accepted"
    assert snapshot.continuity_state.session_key_present is True
    assert len(snapshot.provider_events) == 1
    assert snapshot.provider_events[0].event_kind == "accepted"
    assert snapshot.provider_events[0].event_payload_json is None

    agent_requests = [request for request in observed_requests if request.method == "agent"]
    assert len(agent_requests) == 1
    assert len(recorded_launch_requests) == 1
    assert agent_requests[0].params["sessionKey"] == snapshot.dispatch.gateway_session_key
    assert "message" in agent_requests[0].params
    request_id, launch_input = recorded_launch_requests[0]
    expected_request = original_builder(
        request_id=request_id,
        launch_input=launch_input,
    )
    assert agent_requests[0].request_id == request_id
    assert (
        agent_requests[0].params
        == expected_request.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )["params"]
    )


async def send_unsequenced_provider_delta_stream(
    connection: ServerConnection,
    *,
    run_id: str = "run-live",
) -> None:
    await send_basic_gateway_handshake(connection)
    launch_request = await recv_json(connection)
    assert launch_request["method"] == "agent"
    accepted = {
        "type": "res",
        "id": launch_request["id"],
        "ok": True,
        "payload": {
            "runId": run_id,
            "status": "accepted",
            "acceptedAt": "2026-05-19T00:00:00+00:00",
        },
    }
    await send_json(connection, accepted)
    await send_gateway_event(
        connection,
        event="response.delta",
        payload={"runId": run_id, "delta": "first", "ts": "2026-05-19T00:00:01+00:00"},
    )
    await send_gateway_event(
        connection,
        event="response.delta",
        payload={"runId": run_id, "delta": "second", "ts": "2026-05-19T00:00:02+00:00"},
    )
    await send_gateway_event(
        connection,
        event="response.completed",
        payload={"runId": run_id, "ts": "2026-05-19T00:00:03+00:00"},
    )
    try:
        await connection.wait_closed()
    except ConnectionClosed:
        return


async def send_basic_gateway_handshake(connection: ServerConnection) -> None:
    await send_json(connection, connect_challenge_fixture())
    connect_request = await recv_json(connection)
    hello_ok = hello_ok_fixture(device_token="device-token-test")
    hello_ok["id"] = connect_request["id"]
    await send_json(connection, hello_ok)


async def send_gateway_event(
    connection: ServerConnection,
    *,
    event: str,
    payload: dict[str, object],
) -> None:
    await send_json(
        connection,
        {
            "type": "event",
            "event": event,
            "payload": payload,
        },
    )
