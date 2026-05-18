from __future__ import annotations

import argparse
import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app import cli
from app.config import get_settings
from app.db import (
    ArtifactCurrentPointerModel,
    ArtifactPublicationModel,
    AssignmentModel,
    AttemptModel,
    DispatchTurnModel,
    FlowNodeModel,
)
from app.db.session import dispose_db_engine, get_session_factory
from app.runtime import CheckpointProjection, PromptSendMode, TaskComposeInput
from app.runtime.contracts import RuntimeBootstrapResult
from app.runtime.projection.attempt_materialization import materialize_attempt_files
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.phase2.bootstrap.fixtures import (
    persist_bootstrap_runtime,
    seed_child_terminal_retry_checkpoint,
    seed_dispatch,
)


@dataclass(frozen=True)
class Phase2RuntimePaths:
    config_path: Path
    data_dir: Path
    task_root: Path


@dataclass(frozen=True)
class Phase2RuntimeContext:
    paths: Phase2RuntimePaths
    session_factory: async_sessionmaker[AsyncSession]


@dataclass(frozen=True)
class BootstrappedDispatchCase:
    result: RuntimeBootstrapResult
    dispatch: DispatchTurnModel


def phase2_runtime_paths(tmp_path: Path) -> Phase2RuntimePaths:
    return Phase2RuntimePaths(
        config_path=tmp_path / "autoclaw-config.toml",
        data_dir=tmp_path / "autoclaw-data",
        task_root=tmp_path / "task-root",
    )


def phase2_init_args(paths: Phase2RuntimePaths) -> argparse.Namespace:
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
async def phase2_runtime_context(
    tmp_path: Path,
    *,
    quiet_init: bool = False,
    init_log_level: str | None = None,
) -> AsyncIterator[Phase2RuntimeContext]:
    paths = phase2_runtime_paths(tmp_path)
    get_settings.cache_clear()
    await dispose_db_engine()
    init_args = phase2_init_args(paths)
    if init_log_level is not None:
        init_args.log_level = init_log_level
    if quiet_init:
        with io.StringIO() as devnull:
            with redirect_stdout(devnull), redirect_stderr(devnull):
                await cli.cmd_init(init_args)
    else:
        await cli.cmd_init(init_args)
    try:
        with cli.command_env(config_path=paths.config_path):
            get_settings.cache_clear()
            yield Phase2RuntimeContext(paths=paths, session_factory=get_session_factory())
    finally:
        get_settings.cache_clear()
        await dispose_db_engine()


async def bootstrap_materialized_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    task_root: Path,
    compiler_version: str,
    dispatch_id: str,
    send_mode: PromptSendMode,
    task_compose: TaskComposeInput | None = None,
    latest_checkpoint: CheckpointProjection | None = None,
    rendered_at: datetime | None = None,
) -> BootstrappedDispatchCase:
    result = await persist_bootstrap_runtime(
        session,
        task_id=task_id,
        task_root=task_root,
        compiler_version=compiler_version,
        task_compose=task_compose,
        latest_checkpoint=latest_checkpoint,
    )
    await materialize_attempt_files(
        session,
        task_id,
        result.manifest.current_context.active_attempt_id,
    )
    dispatch = await seed_dispatch(
        session,
        task_id=task_id,
        dispatch_id=dispatch_id,
        send_mode=send_mode,
        rendered_at=rendered_at,
    )
    return BootstrappedDispatchCase(result=result, dispatch=dispatch)


async def require_flow_node_by_key(
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


async def require_dispatch_flow_node(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    node_key: str,
) -> FlowNodeModel:
    assert dispatch.flow_revision_id is not None
    return await require_flow_node_by_key(
        session,
        flow_revision_id=dispatch.flow_revision_id,
        node_key=node_key,
    )


def consumed_durable_refs_section(full_markdown: str) -> str:
    return full_markdown.split("## Consumed Durable Refs", maxsplit=1)[1].split(
        "## Allowed Actions Now",
        maxsplit=1,
    )[0]


def stage_release_descendant_refs(
    dispatch: DispatchTurnModel,
    *,
    task_root: Path,
    task_id: str,
) -> tuple[Path, Path]:
    checkpoint_path = (
        task_root
        / "_runtime"
        / "attempts"
        / f"attempt.{task_id}.review_change.01"
        / "latest-checkpoint.md"
    )
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text("staged descendant checkpoint", encoding="utf-8")

    artifact_path = (
        task_root
        / "outputs"
        / "artifacts"
        / "review_change"
        / "review_report"
        / "review_report.v02.md"
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("staged descendant artifact", encoding="utf-8")

    dispatch.release_precondition_descendant_refs_json = [
        {
            "kind": "checkpoint",
            "path": str(checkpoint_path),
            "description": "Controller-staged descendant checkpoint for the release reread.",
        },
        {
            "kind": "artifact",
            "slot": "review_report",
            "version": 2,
            "path": str(artifact_path),
            "description": "Controller-staged descendant review artifact for the release reread.",
        },
    ]
    return checkpoint_path, artifact_path


def child_artifact_runtime_rows(
    *,
    task_id: str,
    child_node: FlowNodeModel,
    slot: str,
    artifact_path: Path,
    artifact_description: str,
    assignment_key: str,
    attempt_id: str,
    published_at: datetime,
) -> tuple[ArtifactPublicationModel, ArtifactCurrentPointerModel]:
    return (
        ArtifactPublicationModel(
            artifact_publication_id=f"{task_id}.{child_node.node_key}.{slot}.v01",
            task_id=task_id,
            flow_node_id=child_node.flow_node_id,
            owner_node_key=child_node.node_key,
            slot=slot,
            version=1,
            path=str(artifact_path),
            description=artifact_description,
            assignment_key=assignment_key,
            attempt_id=attempt_id,
            published_at=published_at,
            supersedes_version=None,
            supersedes_path=None,
        ),
        ArtifactCurrentPointerModel(
            artifact_current_pointer_id=f"{task_id}.{child_node.node_key}.{slot}.current",
            task_id=task_id,
            flow_node_id=child_node.flow_node_id,
            owner_node_key=child_node.node_key,
            slot=slot,
            current_version=1,
            current_path=str(artifact_path),
            description=artifact_description,
            assignment_key=assignment_key,
            attempt_id=attempt_id,
            published_at=published_at,
            supersedes_path=None,
        ),
    )


async def seed_child_artifact_publication(
    session: AsyncSession,
    *,
    task_id: str,
    task_root: Path,
    flow_id: str,
    flow_revision_id: str,
    child_node: FlowNodeModel,
    slot: str,
    assignment_summary: str,
    artifact_body: str,
    artifact_description: str,
    published_at: datetime,
) -> Path:
    assignment_key = f"{task_id}.{child_node.node_key}.assign-01"
    assignment_id = f"{task_id}.{child_node.node_key}.assignment.db"
    attempt_id = f"attempt.{task_id}.{child_node.node_key}.01"
    artifact_path = (
        task_root / "outputs" / "artifacts" / child_node.node_key / slot / f"{slot}.v01.md"
    )

    session.add(
        AssignmentModel(
            assignment_id=assignment_id,
            task_id=task_id,
            flow_id=flow_id,
            flow_revision_id=flow_revision_id,
            flow_node_id=child_node.flow_node_id,
            assignment_key=assignment_key,
            node_key=child_node.node_key,
            summary=assignment_summary,
            instruction=None,
            criteria_json=[],
            consumes_json=[],
            produces_json=[],
            transient_refs_json=[],
            task_memory_search_hints_json=[],
            current_attempt_id=attempt_id,
        )
    )
    session.add(
        AttemptModel(
            attempt_id=attempt_id,
            assignment_id=assignment_id,
            assignment_key=assignment_key,
            flow_node_id=child_node.flow_node_id,
            task_id=task_id,
            node_key=child_node.node_key,
            status="succeeded",
            opened_at=published_at,
        )
    )

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(artifact_body, encoding="utf-8")
    publication, current_pointer = child_artifact_runtime_rows(
        task_id=task_id,
        child_node=child_node,
        slot=slot,
        artifact_path=artifact_path,
        artifact_description=artifact_description,
        assignment_key=assignment_key,
        attempt_id=attempt_id,
        published_at=published_at,
    )
    session.add(publication)
    session.add(current_pointer)
    await session.flush()
    return artifact_path


async def seed_controller_selected_checkpoint_pair(
    session: AsyncSession,
    *,
    task_id: str,
    task_root: Path,
    dispatch: DispatchTurnModel,
    child_node: FlowNodeModel,
    rendered_at: datetime,
    selected_attempt_id: str,
    current_attempt_id: str,
) -> tuple[Path, Path]:
    selected_checkpoint_path = await seed_child_terminal_retry_checkpoint(
        session,
        task_id=task_id,
        task_root=task_root,
        dispatch=dispatch,
        child_node=child_node,
        attempt_id=selected_attempt_id,
        assignment_suffix="selected",
        assignment_summary="Older child attempt selected explicitly for the next root review.",
        checkpoint_summary="Controller-selected child checkpoint for the next root review.",
        checkpoint_next_step="Re-read this explicit checkpoint before deciding the next turn.",
        checkpoint_risk="This child checkpoint remains the selected handoff basis.",
        recorded_at=rendered_at - timedelta(seconds=15),
        make_current=False,
    )
    dispatch.relevant_checkpoint_attempt_id = selected_attempt_id
    current_checkpoint_path = await seed_child_terminal_retry_checkpoint(
        session,
        task_id=task_id,
        task_root=task_root,
        dispatch=dispatch,
        child_node=child_node,
        attempt_id=current_attempt_id,
        assignment_suffix="current",
        assignment_summary="Current child attempt with a newer checkpoint that should not win.",
        checkpoint_summary="Newer direct-child checkpoint that should stay ordinary context.",
        checkpoint_next_step="Keep this visible as direct-child context only.",
        checkpoint_risk="This checkpoint is newer but not controller-selected.",
        recorded_at=rendered_at - timedelta(seconds=1),
        make_current=True,
    )
    await materialize_attempt_files(session, task_id, selected_attempt_id)
    await materialize_attempt_files(session, task_id, current_attempt_id)
    return selected_checkpoint_path, current_checkpoint_path
