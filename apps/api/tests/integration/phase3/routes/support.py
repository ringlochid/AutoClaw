from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from app import cli
from app.config import get_settings
from app.db import DispatchTurnModel, FlowModel, NodeSessionModel
from app.db.session import dispose_db_engine, get_session_factory
from app.main import create_app
from app.runtime import TaskComposeInput
from app.runtime.effects import wait_for_runtime_effects
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload

EXPECTED_OPERATOR_CURRENT_PATHS = (
    ("manifest", "workflow-manifest.md", "Whole-workflow visible contract for the current task."),
    ("delivery_state", "delivery-state.json", "Latest task-scoped delivery-state projection."),
    (
        "continuity_state",
        "continuity-state.json",
        "Latest task-scoped continuity-state projection.",
    ),
    ("watchdog_state", "watchdog-state.json", "Latest task-scoped watchdog-state projection."),
    (
        "provider_events",
        "provider-events.ndjson",
        "Normalized provider-event history for the selected task.",
    ),
)


@dataclass(frozen=True)
class Phase3RouteContext:
    client: AsyncClient
    operator_headers: dict[str, str]
    session_factory: async_sessionmaker[AsyncSession]
    tmp_path: Path


@dataclass(frozen=True)
class SeededRouteTask:
    task_id: str
    task_root: Path
    session_key: str
    active_flow_revision_id: str
    current_open_dispatch_id: str


def assert_operator_current_paths(entries: list[dict[str, object]]) -> None:
    assert [
        (
            entry["kind"],
            Path(str(entry["path"])).name,
            entry["description"],
            entry["slot"],
            entry["version"],
        )
        for entry in entries
    ] == [
        (kind, name, description, None, None)
        for kind, name, description in EXPECTED_OPERATOR_CURRENT_PATHS
    ]


async def assert_operator_paths_exist(entries: list[dict[str, object]]) -> None:
    paths = [Path(str(entry["path"])) for entry in entries]
    for path in paths:
        await wait_for_runtime_effects(max_wait_seconds=5.0)
        assert await asyncio.to_thread(path.is_file)


def build_route_task_compose(
    *,
    task_key: str,
    task_title: str,
    task_summary: str,
) -> TaskComposeInput:
    base_compose = task_compose_payload("normal-parent-first-release")
    return base_compose.model_copy(
        update={
            "task": base_compose.task.model_copy(
                update={
                    "key": task_key,
                    "title": task_title,
                    "summary": task_summary,
                }
            )
        }
    )


@asynccontextmanager
async def phase3_route_context(tmp_path: Path) -> AsyncIterator[Phase3RouteContext]:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    await cli._cmd_init(
        argparse.Namespace(
            config=str(config_path),
            data_dir=str(data_dir),
            database_url=None,
            host="127.0.0.1",
            port=8123,
            log_level="INFO",
            api_key="api-test-key",
            internal_api_key="internal-test-key",
            force=True,
            skip_db_upgrade=False,
            json=False,
        )
    )
    try:
        with cli._command_env(config_path=config_path):
            get_settings.cache_clear()
            app = create_app()
            async with app.router.lifespan_context(app):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    yield Phase3RouteContext(
                        client=client,
                        operator_headers={"X-AutoClaw-API-Key": "api-test-key"},
                        session_factory=get_session_factory(),
                        tmp_path=tmp_path,
                    )
    finally:
        await dispose_db_engine()


async def launch_route_task(
    context: Phase3RouteContext,
    *,
    task_id: str,
    task_root_name: str,
    task_compose: TaskComposeInput | None = None,
) -> SeededRouteTask:
    task_root = context.tmp_path / task_root_name
    async with context.session_factory() as session:
        await launch_seeded_runtime(
            session,
            task_id=task_id,
            task_root=task_root,
            task_compose=task_compose or task_compose_payload("normal-parent-first-release"),
            compiler_version="phase-3-runtime-routes",
        )
    await wait_for_runtime_effects(task_id=task_id)
    return await refresh_route_task(context, task_id=task_id, task_root=task_root)


async def refresh_route_task(
    context: Phase3RouteContext,
    *,
    task_id: str,
    task_root: Path,
) -> SeededRouteTask:
    async with context.session_factory() as session:
        flow = await session.get(FlowModel, f"flow.{task_id}")
        assert flow is not None
        assert flow.active_flow_revision_id is not None
        dispatch_id = flow.current_open_dispatch_id
        assert dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        session_key = await session.scalar(
            select(NodeSessionModel.session_key)
            .where(
                NodeSessionModel.dispatch_id == dispatch_id,
                NodeSessionModel.session_status == "live",
                NodeSessionModel.closed_at.is_(None),
            )
            .order_by(NodeSessionModel.opened_at.desc())
            .limit(1)
        )
        assert session_key is not None
    return SeededRouteTask(
        task_id=task_id,
        task_root=task_root,
        session_key=session_key,
        active_flow_revision_id=flow.active_flow_revision_id,
        current_open_dispatch_id=dispatch_id,
    )


async def assign_child(
    context: Phase3RouteContext,
    task: SeededRouteTask,
) -> Response:
    return await context.client.post(
        f"/callback/tasks/{task.task_id}/tools/assign_child",
        params={"session_key": task.session_key},
        json={
            "tool_name": "assign_child",
            "payload": {
                "child_node_key": "implementation_subtree",
                "assignment_intent": {
                    "summary": "Start the implementation subtree.",
                    "instruction": "Stage only the current implementation subtree.",
                },
            },
            "expected_structural_revision_id": task.active_flow_revision_id,
        },
    )


async def yield_boundary(
    context: Phase3RouteContext,
    task: SeededRouteTask,
) -> Response:
    return await context.client.post(
        f"/callback/tasks/{task.task_id}/boundary",
        params={"session_key": task.session_key},
        json={"boundary": "yield"},
    )


async def mark_current_dispatch_delivery_status(
    context: Phase3RouteContext,
    *,
    task_id: str,
    delivery_status: str,
) -> None:
    async with context.session_factory() as session:
        flow = await session.get(FlowModel, f"flow.{task_id}")
        assert flow is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        dispatch.delivery_status = delivery_status
        await session.commit()


async def continue_into_child_dispatch(
    context: Phase3RouteContext,
    task: SeededRouteTask,
) -> SeededRouteTask:
    await mark_current_dispatch_delivery_status(
        context,
        task_id=task.task_id,
        delivery_status="provider_completed",
    )
    continued = await context.client.post(
        f"/runtime/tasks/{task.task_id}/continue",
        headers=context.operator_headers,
        params={"expected_active_flow_revision_id": task.active_flow_revision_id},
    )
    assert continued.status_code == 200
    await wait_for_runtime_effects(task_id=task.task_id)
    return await refresh_route_task(context, task_id=task.task_id, task_root=task.task_root)
