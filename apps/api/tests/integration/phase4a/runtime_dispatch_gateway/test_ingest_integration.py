from __future__ import annotations

from pathlib import Path

import pytest
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase2.bootstrap.support import phase2_runtime_context
from tests.integration.phase4a.dispatch_gateway_support import (
    override_gateway_base_url,
    wait_for_latest_dispatch_snapshot,
)
from tests.integration.phase4a.runtime_dispatch_gateway.support import (
    send_unsequenced_provider_delta_stream,
)
from tests.integration.phase4a.support import gateway_server


@pytest.mark.asyncio
async def test_runtime_ingest_persists_distinct_unsequenced_provider_deltas(
    tmp_path: Path,
) -> None:
    task_id = "task_phase4a_unsequenced_provider_deltas"

    async with gateway_server(send_unsequenced_provider_delta_stream) as base_url:
        async with phase2_runtime_context(tmp_path) as runtime:
            with override_gateway_base_url(base_url):
                async with runtime.session_factory() as session:
                    await launch_seeded_runtime(
                        session,
                        task_id=task_id,
                        task_root=runtime.paths.task_root,
                        task_compose=task_compose_payload("minimal-implement-change"),
                        compiler_version="phase-4a-unsequenced-provider-deltas",
                    )

            snapshot = await wait_for_latest_dispatch_snapshot(
                runtime.session_factory,
                task_id=task_id,
                predicate=lambda current: (
                    len(current.provider_events) >= 4
                    and [event.event_kind for event in current.provider_events[:4]]
                    == ["accepted", "first_data", "output_delta", "response_completed"]
                    and current.delivery_state is not None
                    and current.delivery_state.last_provider_event_kind == "response_completed"
                    and current.dispatch.delivery_status == "provider_completed"
                ),
                timeout_seconds=10.0,
            )

    assert snapshot.delivery_state is not None
    assert snapshot.delivery_state.last_provider_event_kind == "response_completed"
    assert snapshot.dispatch.delivery_status == "provider_completed"
