from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from app.config import OpenClawSettings, get_settings
from app.runtime.openclaw import OpenClawTransportError
from app.runtime.openclaw.contracts import OpenClawLaunchRequest
from app.runtime.openclaw.protocol import OpenClawAgentRequest
from app.runtime.openclaw.request_builders import build_openclaw_agent_request
from pydantic import ValidationError
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase2.bootstrap.support import phase2_runtime_context
from tests.integration.phase4a.dispatch_gateway_support import (
    DispatchGatewaySnapshot,
    load_latest_dispatch_snapshot,
    override_gateway_base_url,
)
from tests.integration.phase4a.support import GatewayRequestRecord, LocalGatewayTestServer


@pytest.mark.asyncio
async def test_launch_runtime_persists_gateway_session_run_and_callback_binding_split(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4a_launch_gateway_success"
    recorded_launch_requests: list[tuple[str, OpenClawLaunchRequest]] = []
    original_builder = build_openclaw_agent_request

    def record_gateway_agent_request(
        *,
        config: OpenClawSettings,
        request_id: str,
        launch_request: OpenClawLaunchRequest,
    ) -> object:
        recorded_launch_requests.append((request_id, launch_request))
        return original_builder(
            config=config,
            request_id=request_id,
            launch_request=launch_request,
        )

    monkeypatch.setattr(
        "app.runtime.control.dispatch.gateway.build_openclaw_agent_request",
        record_gateway_agent_request,
    )

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("minimal-implement-change"),
                compiler_version="phase-4a-launch-success",
            )

        async with runtime.session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

    assert_gateway_launch_snapshot(
        snapshot,
        recorded_launch_requests=recorded_launch_requests,
        original_builder=original_builder,
        observed_requests=openclaw_gateway_test_server.requests,
    )


@pytest.mark.asyncio
async def test_launch_runtime_persists_transport_failure_without_fake_acceptance(
    tmp_path: Path,
) -> None:
    task_id = "task_phase4a_launch_gateway_failure"

    async with phase2_runtime_context(tmp_path) as runtime:
        with override_gateway_base_url("http://127.0.0.1:1"):
            async with runtime.session_factory() as session:
                with pytest.raises(OpenClawTransportError):
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-4a-launch-failure",
                    )

        async with runtime.session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

        assert snapshot.flow.current_open_dispatch_id is None
        assert snapshot.delivery_state is not None
        assert snapshot.continuity_state is not None
        assert snapshot.dispatch.status == "transport_failed"
        assert snapshot.dispatch.delivery_status == "transport_failed"
        assert snapshot.dispatch.control_state == "fenced"
        assert snapshot.dispatch.gateway_session_key is None
        assert snapshot.dispatch.gateway_run_id is None
        assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
        assert snapshot.delivery_state.transport_state == "transport_failed"
        assert snapshot.delivery_state.controller_observation_state == "fenced"
        assert snapshot.delivery_state.provider_error is not None
        assert snapshot.continuity_state.session_key_present is False
        assert snapshot.continuity_state.invalidation_reason == (
            "gateway_launch_failed:OpenClawTransportError"
        )
        assert snapshot.binding is None
        assert snapshot.node_session is None
        assert len(snapshot.provider_events) == 1
        assert snapshot.provider_events[0].event_kind == "transport_failed"


@pytest.mark.asyncio
async def test_launch_runtime_post_send_normalization_failure_marks_dispatch_ambiguous(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4a_launch_gateway_post_send_failure"
    openclaw_gateway_test_server.set_default_method_payload(
        "agent",
        {
            "type": "res",
            "id": "agent-1",
            "ok": True,
            "payload": {
                "acceptedAt": "2026-05-13T00:00:00+00:00",
            },
        },
    )

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            with pytest.raises(ValidationError):
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-4a-post-send-failure",
                )

        async with runtime.session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

        assert snapshot.delivery_state is not None
        assert snapshot.continuity_state is not None
        assert snapshot.dispatch.status == "transport_ambiguous"
        assert snapshot.dispatch.delivery_status == "transport_ambiguous"
        assert snapshot.dispatch.control_state == "ambiguous"
        assert snapshot.dispatch.gateway_session_key is not None
        assert snapshot.dispatch.gateway_run_id is None
        assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
        assert snapshot.delivery_state.transport_state == "transport_ambiguous"
        assert snapshot.delivery_state.controller_observation_state == "ambiguous"
        assert snapshot.delivery_state.provider_error is not None
        assert snapshot.continuity_state.continuity_state == "illegal_same_session"
        assert snapshot.continuity_state.session_key_present is True
        assert snapshot.continuity_state.invalidation_reason == (
            "gateway_launch_post_send_failed:ValidationError"
        )
        assert [event.event_kind for event in snapshot.provider_events] == [
            "transport_failed",
            "tool_event",
        ]
        assert any(
            request.method == "sessions.abort" for request in openclaw_gateway_test_server.requests
        )


@pytest.mark.asyncio
async def test_launch_runtime_post_acceptance_persistence_failure_cleans_up_remote_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4a_launch_gateway_post_acceptance_failure"

    async def fail_callback_binding(*args: object, **kwargs: object) -> object:
        raise RuntimeError("callback binding write failed")

    monkeypatch.setattr(
        "app.runtime.control.dispatch.gateway_launch_state.create_callback_binding",
        fail_callback_binding,
    )

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            with pytest.raises(RuntimeError, match="callback binding write failed"):
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-4a-post-acceptance-failure",
                )

        async with runtime.session_factory() as session:
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)

        assert snapshot.flow.current_open_dispatch_id is None
        assert snapshot.delivery_state is not None
        assert snapshot.continuity_state is not None
        assert snapshot.dispatch.status == "provider_completed"
        assert snapshot.dispatch.delivery_status == "provider_completed"
        assert snapshot.dispatch.control_state == "fenced"
        assert snapshot.dispatch.gateway_session_key is not None
        assert snapshot.dispatch.gateway_run_id == "run-1"
        assert snapshot.dispatch.fenced_at is not None
        assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
        assert snapshot.delivery_state.transport_state == "provider_completed"
        assert snapshot.delivery_state.controller_observation_state == "fenced"
        assert snapshot.delivery_state.accepted_at is not None
        assert snapshot.continuity_state.continuity_state == "illegal_same_session"
        assert snapshot.continuity_state.session_key_present is True
        assert snapshot.continuity_state.invalidation_reason == (
            "gateway_acceptance_persist_failed:RuntimeError"
        )
        assert snapshot.binding is None
        assert snapshot.node_session is None
        assert [event.event_kind for event in snapshot.provider_events] == [
            "accepted",
            "tool_event",
            "response_completed",
        ]
        assert {request.method for request in openclaw_gateway_test_server.requests} >= {
            "agent",
            "agent.wait",
            "sessions.abort",
        }


def assert_gateway_launch_snapshot(
    snapshot: DispatchGatewaySnapshot,
    *,
    recorded_launch_requests: list[tuple[str, OpenClawLaunchRequest]],
    original_builder: Callable[..., OpenClawAgentRequest],
    observed_requests: tuple[GatewayRequestRecord, ...],
) -> None:
    assert snapshot.delivery_state is not None
    assert snapshot.continuity_state is not None
    assert snapshot.binding is not None
    assert snapshot.node_session is not None
    assert snapshot.dispatch.gateway_session_key is not None
    assert snapshot.dispatch.gateway_run_id == "run-1"
    assert snapshot.binding.session_key != snapshot.dispatch.gateway_session_key
    assert snapshot.node_session.session_key == snapshot.dispatch.gateway_session_key
    assert snapshot.node_session.session_status == "live"
    assert snapshot.delivery_state.transport_family == "openclaw_gateway_ws_rpc"
    assert snapshot.delivery_state.transport_state == "accepted"
    assert snapshot.delivery_state.controller_observation_state == "live"
    assert snapshot.continuity_state.session_key_present is True
    assert len(snapshot.provider_events) == 1
    assert snapshot.provider_events[0].event_kind == "accepted"
    assert snapshot.provider_events[0].event_payload_json == {
        "transport_family": "openclaw_gateway_ws_rpc",
        "send_mode": "full_prompt",
    }

    agent_requests = [request for request in observed_requests if request.method == "agent"]
    assert len(agent_requests) == 1
    assert len(recorded_launch_requests) == 1
    assert agent_requests[0].params["sessionKey"] == snapshot.dispatch.gateway_session_key
    assert "message" in agent_requests[0].params
    request_id, launch_request = recorded_launch_requests[0]
    expected_request = original_builder(
        config=get_settings().openclaw,
        request_id=request_id,
        launch_request=launch_request,
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
