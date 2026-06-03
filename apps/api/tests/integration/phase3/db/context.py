from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app import cli
from app.config import get_settings
from app.db import DispatchTurnModel, FlowModel, FlowNodeModel
from app.db.session import dispose_db_engine, get_session_factory
from app.runtime import EgressBoundary, accept_boundary, runtime_flow_read
from app.runtime.effects import drive_runtime_until
from app.schemas.definitions.workflow import WorkflowDefinitionFile
from app.schemas.runtime import BoundaryWrite as BoundaryWriteSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from tests.helpers.runtime_init_cache import initialize_runtime_from_template
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.helpers.runtime_test_config import set_dispatch_drain_timeout
from tests.helpers.runtime_wait_effects import queue_gateway_wait_ok_if_available


@dataclass(frozen=True)
class Phase3RuntimePaths:
    config_path: Path
    data_dir: Path
    task_root: Path


@dataclass(frozen=True)
class Phase3RuntimeContext:
    paths: Phase3RuntimePaths
    session_factory: async_sessionmaker[AsyncSession]


def phase3_runtime_paths(tmp_path: Path, *, task_root_name: str) -> Phase3RuntimePaths:
    return Phase3RuntimePaths(
        config_path=tmp_path / "autoclaw-config.toml",
        data_dir=tmp_path / "autoclaw-data",
        task_root=tmp_path / task_root_name,
    )


def phase3_init_args(paths: Phase3RuntimePaths) -> argparse.Namespace:
    return argparse.Namespace(
        config=str(paths.config_path),
        data_dir=str(paths.data_dir),
        database_url=None,
        host="127.0.0.1",
        port=8123,
        log_level="WARNING",
        api_key="api-test-key",
        internal_api_key="internal-test-key",
        force=True,
        skip_db_upgrade=False,
        json=False,
    )


@asynccontextmanager
async def phase3_runtime_context(
    tmp_path: Path,
    *,
    task_root_name: str,
) -> AsyncIterator[Phase3RuntimeContext]:
    paths = phase3_runtime_paths(tmp_path, task_root_name=task_root_name)
    await initialize_runtime_from_template(
        config_path=paths.config_path,
        data_dir=paths.data_dir,
        log_level="WARNING",
        api_key="api-test-key",
        internal_api_key="internal-test-key",
        host="127.0.0.1",
        port=8123,
    )
    set_dispatch_drain_timeout(paths.config_path, timeout_seconds=30)
    try:
        with cli.command_env(config_path=paths.config_path):
            get_settings.cache_clear()
            yield Phase3RuntimeContext(paths=paths, session_factory=get_session_factory())
    finally:
        await dispose_db_engine()


async def launch_runtime_case(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    workflow_key: str,
    compiler_version: str,
    workflow_definition: WorkflowDefinitionFile | None = None,
) -> None:
    async with context.session_factory() as session:
        await launch_seeded_runtime(
            session,
            task_id=task_id,
            task_root=context.paths.task_root,
            task_compose=task_compose_payload(workflow_key),
            compiler_version=compiler_version,
            workflow_definition=workflow_definition,
        )


async def continue_runtime_after_boundary(
    session: AsyncSession,
    *,
    task_id: str,
    expected_active_flow_revision_id: str,
    previous_dispatch_id: str | None,
) -> Any:
    session_factory = _session_factory_for_waits(session)
    await session.commit()
    if previous_dispatch_id is not None:
        await queue_gateway_wait_ok_if_available(
            session_factory,
            dispatch_id=previous_dispatch_id,
        )
        try:
            await drive_runtime_until(
                lambda: _boundary_progress_committed(
                    session_factory,
                    task_id=task_id,
                    previous_dispatch_id=previous_dispatch_id,
                    expected_active_flow_revision_id=expected_active_flow_revision_id,
                ),
                task_id=task_id,
                max_cycles=40,
            )
        except AssertionError as exc:
            snapshot = await _boundary_progress_snapshot(
                session_factory,
                task_id=task_id,
                previous_dispatch_id=previous_dispatch_id,
            )
            raise AssertionError(
                "runtime boundary progression did not commit the expected replacement "
                f"or fenced terminal state: {snapshot}"
            ) from exc
    session.expire_all()
    reread = await runtime_flow_read(session, task_id)
    assert reread.active_flow_revision_id == expected_active_flow_revision_id
    return reread


async def accept_boundary_and_continue(
    session: AsyncSession,
    *,
    task_id: str,
    boundary: EgressBoundary,
) -> Any:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    assert flow is not None
    previous_dispatch_id = flow.current_open_dispatch_id
    accepted = await accept_boundary(
        session,
        task_id,
        BoundaryWriteSchema(boundary=boundary),
    )
    await session.commit()
    return await continue_runtime_after_boundary(
        session,
        task_id=task_id,
        expected_active_flow_revision_id=accepted.flow.active_flow_revision_id,
        previous_dispatch_id=previous_dispatch_id,
    )


async def advance_boundary_on_current_flow(
    context: Phase3RuntimeContext,
    *,
    task_id: str,
    boundary: EgressBoundary,
) -> Any:
    async with context.session_factory() as session:
        return await accept_boundary_and_continue(
            session,
            task_id=task_id,
            boundary=boundary,
        )


def _session_factory_for_waits(
    session: AsyncSession,
) -> async_sessionmaker[AsyncSession]:
    bind = session.bind
    assert isinstance(bind, AsyncEngine)
    return async_sessionmaker(bind, expire_on_commit=False)


async def _boundary_progress_committed(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    previous_dispatch_id: str,
    expected_active_flow_revision_id: str,
) -> bool:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None or flow.active_flow_revision_id != expected_active_flow_revision_id:
            return False
        if flow.current_open_dispatch_id is not None:
            replacement = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
            return (
                replacement is not None
                and replacement.dispatch_id != previous_dispatch_id
                and replacement.closed_at is None
            )
        previous_dispatch = await session.get(DispatchTurnModel, previous_dispatch_id)
        return (
            previous_dispatch is not None
            and previous_dispatch.control_state in {"fenced", "ambiguous"}
            and flow.status in {"succeeded", "blocked", "cancelled"}
        )


async def _boundary_progress_snapshot(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    previous_dispatch_id: str,
) -> dict[str, Any]:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        previous_dispatch = await session.get(DispatchTurnModel, previous_dispatch_id)
        current_dispatch: DispatchTurnModel | None = None
        if flow is not None and flow.current_open_dispatch_id is not None:
            current_dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        return {
            "flow_status": None if flow is None else flow.status,
            "flow_current_node_key": None if flow is None else flow.current_node_key,
            "flow_current_open_dispatch_id": (
                None if flow is None else flow.current_open_dispatch_id
            ),
            "previous_dispatch": None
            if previous_dispatch is None
            else {
                "dispatch_id": previous_dispatch.dispatch_id,
                "node_key": previous_dispatch.node_key,
                "control_state": previous_dispatch.control_state,
                "delivery_status": previous_dispatch.delivery_status,
                "accepted_boundary": previous_dispatch.accepted_boundary,
                "closed_at": previous_dispatch.closed_at,
                "fenced_at": previous_dispatch.fenced_at,
                "previous_dispatch_id": previous_dispatch.previous_dispatch_id,
            },
            "current_dispatch": None
            if current_dispatch is None
            else {
                "dispatch_id": current_dispatch.dispatch_id,
                "node_key": current_dispatch.node_key,
                "control_state": current_dispatch.control_state,
                "delivery_status": current_dispatch.delivery_status,
                "accepted_boundary": current_dispatch.accepted_boundary,
                "closed_at": current_dispatch.closed_at,
                "fenced_at": current_dispatch.fenced_at,
                "previous_dispatch_id": current_dispatch.previous_dispatch_id,
            },
        }


async def require_flow_model(session: AsyncSession, *, task_id: str) -> FlowModel:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    assert flow is not None
    return flow


async def require_flow_node(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    node_key: str,
) -> FlowNodeModel:
    node = await session.scalar(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == flow_revision_id,
            FlowNodeModel.node_key == node_key,
        )
    )
    assert node is not None
    return node


def write_task_file(task_root: Path, relative_path: str, content: str) -> Path:
    path = task_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
