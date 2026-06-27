from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import autoclaw.interfaces.cli as cli
from autoclaw.config import get_settings
from autoclaw.main import create_app
from autoclaw.persistence.session import dispose_db_engine, get_session_factory
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.operator_auth_headers import (
    DEFAULT_OPERATOR_ACTOR_REF,
    current_operator_headers,
)
from tests.helpers.runtime_route_seed_support import (
    SeededRuntimeRouteTask,
    seed_runtime_route_task_rows,
)
from tests.integration.runtime_schema_contract.support import initialize_runtime_schema_database


@asynccontextmanager
async def seeded_runtime_route_context(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncClient, SeededRuntimeRouteTask, async_sessionmaker[AsyncSession]]]:
    config_path = tmp_path / "autoclaw-config.toml"
    database_path = await initialize_runtime_schema_database(tmp_path)
    await dispose_db_engine()
    seeded_task = seed_runtime_route_task_rows(
        database_path,
        task_root=tmp_path / "autoclaw-data" / "tasks" / "task.alpha.a",
    )

    try:
        with cli.command_env(config_path=config_path, env="test"):
            get_settings.cache_clear()
            app = create_app(should_enable_mcp_mounts=False)
            async with app.router.lifespan_context(app):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    yield client, seeded_task, get_session_factory()
    finally:
        await dispose_db_engine()


async def test_runtime_write_alias_preserves_control_actor_provenance(
    tmp_path: Path,
) -> None:
    async with seeded_runtime_route_context(tmp_path) as context:
        client, task, _session_factory = context
        pause_response = await client.post(
            f"/runtime/tasks/{task.task_id}/pause",
            headers=current_operator_headers(),
            params={"expected_active_flow_revision_id": task.active_flow_revision_id},
        )

        assert pause_response.status_code == 200
        assert pause_response.json()["flow"]["status"] == "paused"

        paused_events = await _control_task_events(
            client,
            task_id=task.task_id,
            event_types={"task_paused"},
        )
        assert len(paused_events) == 1
        assert paused_events[0]["event_source"] == "control_api"
        assert paused_events[0]["actor_ref"] == DEFAULT_OPERATOR_ACTOR_REF


async def test_control_actor_ref_boundary_rejects_overlong_trimmed_value(
    tmp_path: Path,
) -> None:
    async with seeded_runtime_route_context(tmp_path) as context:
        client, task, _session_factory = context
        overlong_actor_ref = "x" * 256

        pause_response = await client.post(
            f"/control/tasks/{task.task_id}/pause",
            headers=current_operator_headers(actor_ref=overlong_actor_ref),
            params={"expected_active_flow_revision_id": task.active_flow_revision_id},
        )

        assert pause_response.status_code == 400
        assert pause_response.json()["code"] == "invalid_request_shape"
        assert pause_response.json()["field_path"] == "header.X-AutoClaw-Actor-Ref"

        readback_response = await client.get(
            f"/control/tasks/{task.task_id}",
            headers=current_operator_headers(),
        )
        assert readback_response.status_code == 200
        assert readback_response.json()["status"] == "running"
        assert await _control_task_events(
            client,
            task_id=task.task_id,
            event_types={"task_paused", "task_resumed", "task_cancelled"},
        ) == []


async def test_runtime_cancel_alias_preserves_plain_task_cancelled_actor_provenance(
    tmp_path: Path,
) -> None:
    async with seeded_runtime_route_context(tmp_path) as context:
        client, task, _session_factory = context

        cancel_response = await client.post(
            f"/runtime/tasks/{task.task_id}/cancel",
            headers=current_operator_headers(),
            params={"expected_active_flow_revision_id": task.active_flow_revision_id},
        )

        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"
        cancelled_events = await _control_task_events(
            client,
            task_id=task.task_id,
            event_types={"task_cancelled"},
        )
        assert len(cancelled_events) == 1
        assert cancelled_events[0]["event_source"] == "control_api"
        assert cancelled_events[0]["actor_ref"] == DEFAULT_OPERATOR_ACTOR_REF
        assert cancelled_events[0]["payload"] == {"status": "cancelled"}


async def _control_task_events(
    client: AsyncClient,
    *,
    task_id: str,
    event_types: set[str],
) -> list[dict[str, object]]:
    events_response = await client.get(
        f"/control/tasks/{task_id}/events",
        headers=current_operator_headers(),
    )
    assert events_response.status_code == 200
    return [
        event for event in events_response.json()["items"] if event["event_type"] in event_types
    ]
