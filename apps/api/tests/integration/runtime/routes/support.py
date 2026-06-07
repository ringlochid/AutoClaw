from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import autoclaw.interfaces.cli as cli
from autoclaw.config import get_settings
from autoclaw.main import create_app
from autoclaw.persistence import DispatchTurnModel, FlowModel, NodeSessionModel
from autoclaw.persistence.session import dispose_db_engine, get_session_factory
from autoclaw.runtime import TaskComposeInput
from autoclaw.runtime.post_commit import drive_runtime_until
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.operator_auth_headers import OPERATOR_HEADERS
from tests.helpers.runtime_support import (
    initialize_runtime_from_template,
    set_dispatch_drain_timeout,
)
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload

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
class RuntimeRouteContext:
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


def assert_operator_current_paths(
    entries: list[dict[str, object]],
    *,
    include_dispatch_support: bool = True,
) -> None:
    expected_entries = (
        EXPECTED_OPERATOR_CURRENT_PATHS
        if include_dispatch_support
        else EXPECTED_OPERATOR_CURRENT_PATHS[:1]
    )
    assert [
        (
            entry["kind"],
            Path(str(entry["path"])).name,
            entry["description"],
            entry["slot"],
            entry["version"],
        )
        for entry in entries
    ] == [(kind, name, description, None, None) for kind, name, description in expected_entries]


async def assert_operator_paths_exist(entries: list[dict[str, object]]) -> None:
    paths = [Path(str(entry["path"])) for entry in entries]
    await drive_runtime_until(
        lambda: _all_operator_paths_exist(paths),
        max_cycles=20,
    )
    assert await _all_operator_paths_exist(paths)


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
async def runtime_route_context(
    tmp_path: Path,
    *,
    dispatch_drain_timeout_seconds: int | None = None,
) -> AsyncIterator[RuntimeRouteContext]:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    await initialize_runtime_from_template(
        config_path=config_path,
        data_dir=data_dir,
        log_level="WARNING",
        api_key="api-test-key",
        internal_api_key="internal-test-key",
        host="127.0.0.1",
        port=8123,
    )
    if dispatch_drain_timeout_seconds is not None:
        set_dispatch_drain_timeout(
            config_path,
            timeout_seconds=dispatch_drain_timeout_seconds,
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
                    yield RuntimeRouteContext(
                        client=client,
                        operator_headers=OPERATOR_HEADERS,
                        session_factory=get_session_factory(),
                        tmp_path=tmp_path,
                    )
    finally:
        await dispose_db_engine()


async def launch_route_task(
    context: RuntimeRouteContext,
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
            compiler_version="runtime-route-support",
        )
    return await refresh_route_task(
        context,
        task_id=task_id,
        task_root=task_root,
        expected_dispatch_node_key="root",
    )


async def refresh_route_task(
    context: RuntimeRouteContext,
    *,
    task_id: str,
    task_root: Path,
    expected_dispatch_node_key: str | None = None,
    require_live_session: bool = True,
) -> SeededRouteTask:
    seeded_task: SeededRouteTask | None = None

    async def route_task_ready() -> bool:
        nonlocal seeded_task
        async with context.session_factory() as session:
            flow = await session.get(FlowModel, f"flow.{task_id}")
            assert flow is not None
            assert flow.active_flow_revision_id is not None
            dispatch_id = flow.current_open_dispatch_id
            if dispatch_id is None:
                return False
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert dispatch is not None
            if (
                expected_dispatch_node_key is not None
                and dispatch.node_key != expected_dispatch_node_key
            ):
                return False
            if not require_live_session:
                session_key = dispatch.gateway_session_key
                seeded_task = SeededRouteTask(
                    task_id=task_id,
                    task_root=task_root,
                    session_key="" if session_key is None else session_key,
                    active_flow_revision_id=flow.active_flow_revision_id,
                    current_open_dispatch_id=dispatch_id,
                )
                return True
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
            if session_key is None:
                return False
            seeded_task = SeededRouteTask(
                task_id=task_id,
                task_root=task_root,
                session_key=session_key,
                active_flow_revision_id=flow.active_flow_revision_id,
                current_open_dispatch_id=dispatch_id,
            )
            return True

    await drive_runtime_until(
        route_task_ready,
        task_id=task_id,
        max_cycles=40,
    )
    assert seeded_task is not None
    return seeded_task


async def assign_child(
    context: RuntimeRouteContext,
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
    context: RuntimeRouteContext,
    task: SeededRouteTask,
) -> Response:
    return await context.client.post(
        f"/callback/tasks/{task.task_id}/boundary",
        params={"session_key": task.session_key},
        json={"boundary": "yield"},
    )


async def continue_into_child_dispatch(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
) -> SeededRouteTask:
    return await refresh_route_task(
        context,
        task_id=task.task_id,
        task_root=task.task_root,
        expected_dispatch_node_key="implementation_subtree",
        require_live_session=False,
    )


async def _all_operator_paths_exist(paths: list[Path]) -> bool:
    return all(await asyncio.gather(*(asyncio.to_thread(path.is_file) for path in paths)))
