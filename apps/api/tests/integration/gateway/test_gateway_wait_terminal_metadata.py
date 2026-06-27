from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence import DispatchTurnModel, FlowModel, ProviderEventRecordModel
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.post_commit import wait_for_runtime_effects
from sqlalchemy import select
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import (
    bootstrap_parent_runtime,
    prepare_runtime_db,
    runtime_api_context,
)
from tests.helpers.runtime_support.dispatch import delivery_state_path, read_json


@pytest.mark.asyncio
async def test_gateway_wait_terminal_timeout_metadata_fences_as_provider_failure(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_gateway_wait_timeout_terminal_metadata"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(
                status="timeout",
                error="aborted",
                stop_reason="rpc",
                liveness_state="blocked",
            ),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="gateway-wait-timeout-terminal-metadata",
        )

        async with runtime_api_context(config_path) as api:
            await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                dispatch = await session.scalar(
                    select(DispatchTurnModel)
                    .where(DispatchTurnModel.task_id == task_id)
                    .order_by(DispatchTurnModel.rendered_at.desc())
                )
                assert flow is not None
                assert dispatch is not None
                provider_events = list(
                    await session.scalars(
                        select(ProviderEventRecordModel)
                        .where(ProviderEventRecordModel.dispatch_id == dispatch.dispatch_id)
                        .order_by(ProviderEventRecordModel.event_no.asc())
                    )
                )
                assert flow.current_open_dispatch_id is None
                assert dispatch.control_state == "fenced"
                assert dispatch.delivery_status == "provider_failed"
                assert provider_events[-1].event_kind == "response_failed"
                payload = provider_events[-1].event_payload_json
                assert payload is not None
                assert payload["gateway_status"] == "timeout"
                assert payload["stop_reason"] == "rpc"
                assert payload["liveness_state"] == "blocked"

            delivery_state = read_json(
                delivery_state_path(task_root=task_root, dispatch_id=dispatch.dispatch_id)
            )
            assert delivery_state["transport_state"] == "provider_failed"
            assert delivery_state["provider_final_status"] == "error"
            assert delivery_state["provider_error"] == "aborted"
            assert any(
                request.method == "agent.wait" for request in openclaw_gateway_test_server.requests
            )
    finally:
        await dispose_db_engine()
