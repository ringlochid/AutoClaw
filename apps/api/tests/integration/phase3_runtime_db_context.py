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
from app.runtime import (
    EgressBoundary,
    accept_boundary,
    continue_runtime_flow,
)
from app.runtime.post_commit import wait_for_runtime_effects
from app.schemas.definitions.workflow import WorkflowDefinitionFile
from app.schemas.runtime import BoundaryWrite as BoundaryWriteSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload


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
        log_level="INFO",
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
    await cli._cmd_init(phase3_init_args(paths))
    try:
        with cli._command_env(config_path=paths.config_path):
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
) -> Any:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    assert flow is not None
    if flow.current_open_dispatch_id is not None:
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        if (
            dispatch.fenced_at is None
            and dispatch.delivery_status == "accepted"
            and (
                dispatch.accepted_boundary is not None
                or dispatch.control_state == "abort_requested"
            )
        ):
            dispatch.delivery_status = "provider_completed"
    continued = await continue_runtime_flow(
        session,
        task_id,
        expected_active_flow_revision_id=expected_active_flow_revision_id,
    )
    await session.commit()
    await wait_for_runtime_effects(task_id=task_id)
    return continued


async def accept_boundary_and_continue(
    session: AsyncSession,
    *,
    task_id: str,
    boundary: EgressBoundary,
) -> Any:
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
