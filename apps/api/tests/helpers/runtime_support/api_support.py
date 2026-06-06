from __future__ import annotations

import argparse
from pathlib import Path

import autoclaw.interfaces.cli as cli
from autoclaw.config import get_settings
from autoclaw.definitions.contracts.workflow import WorkflowDefinitionFile
from autoclaw.persistence.session import get_session_factory
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers.runtime_support.child_dispatch_support import (
    drive_minimal_child_to_green,
    stage_child_dispatch,
    write_workspace_file,
)
from tests.helpers.runtime_support.dispatch_session_support import (
    current_session_key,
    current_session_key_after_dispatch_progress,
    current_session_key_after_dispatch_progress_for_node,
    live_node_session_key_for_dispatch,
    load_live_dispatch,
)
from tests.helpers.runtime_support.http_api_support import (
    OPERATOR_HEADERS,
    ChildDispatchStage,
    RuntimeApiContext,
    assign_child,
    boundary,
    continue_flow,
    parent_tool,
    pause_flow,
    record_checkpoint,
    runtime_api_context,
    runtime_read_json,
)
from tests.helpers.runtime_support.runtime_config_support import set_dispatch_drain_timeout
from tests.helpers.runtime_support.runtime_template_support import (
    initialize_runtime_from_template,
)
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload


def runtime_api_init_args(*, config_path: Path, data_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        config=str(config_path),
        data_dir=str(data_dir),
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


async def prepare_runtime_db(
    tmp_path: Path,
    *,
    dispatch_drain_timeout_seconds: int | None = None,
) -> Path:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    get_settings.cache_clear()
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
    get_settings.cache_clear()
    return config_path


async def persist_bootstrap(
    *,
    config_path: Path,
    task_id: str,
    task_root: Path,
    workflow_definition: WorkflowDefinitionFile,
    revision_no: int,
) -> None:
    with cli.command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        async with session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=task_root,
                task_compose=task_compose_payload(workflow_definition.id),
                compiler_version=f"phase-3-contract-fixes-r{revision_no}",
                workflow_definition=workflow_definition,
            )
        await _wait_for_live_dispatch_session_key(session_factory, task_id=task_id)


async def bootstrap_parent_runtime(
    *,
    config_path: Path,
    task_id: str,
    task_root: Path,
    compiler_version: str,
    workflow_key: str = "normal-parent-first-release",
) -> None:
    with cli.command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        async with session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=task_root,
                task_compose=task_compose_payload(workflow_key),
                compiler_version=compiler_version,
            )
        await _wait_for_live_dispatch_session_key(session_factory, task_id=task_id)


async def _wait_for_live_dispatch_session_key(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> None:
    from autoclaw.runtime.post_commit import drive_runtime_until

    await drive_runtime_until(
        lambda: _task_has_live_dispatch_session(session_factory, task_id=task_id),
        task_id=task_id,
        max_cycles=20,
    )


async def _task_has_live_dispatch_session(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> bool:
    from autoclaw.persistence import FlowModel
    from sqlalchemy import select

    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        if flow is None:
            return False
        dispatch = await load_live_dispatch(session, task_id=task_id, flow=flow)
        session_key = await live_node_session_key_for_dispatch(session, dispatch=dispatch)
        return session_key is not None


__all__ = [
    "OPERATOR_HEADERS",
    "ChildDispatchStage",
    "RuntimeApiContext",
    "assign_child",
    "bootstrap_parent_runtime",
    "boundary",
    "continue_flow",
    "current_session_key",
    "current_session_key_after_dispatch_progress",
    "current_session_key_after_dispatch_progress_for_node",
    "drive_minimal_child_to_green",
    "parent_tool",
    "pause_flow",
    "persist_bootstrap",
    "prepare_runtime_db",
    "record_checkpoint",
    "runtime_api_context",
    "runtime_api_init_args",
    "runtime_read_json",
    "stage_child_dispatch",
    "write_workspace_file",
]
