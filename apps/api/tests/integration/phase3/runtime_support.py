from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from app import cli
from app.config import get_settings
from app.db import DispatchTurnModel, FlowModel
from app.db.session import get_session_factory
from app.runtime.effects import wait_for_runtime_effects
from app.schemas.definitions.workflow import WorkflowDefinitionFile
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase3.callback_api import (
    OPERATOR_HEADERS,
    ChildDispatchStage,
    Phase3RuntimeApi,
    assign_child,
    boundary,
    continue_flow,
    parent_tool,
    pause_flow,
    phase3_runtime_api,
    record_checkpoint,
    runtime_read_json,
)


def phase3_init_args(*, config_path: Path, data_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
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


async def prepare_runtime_db(tmp_path: Path) -> Path:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    await cli._cmd_init(
        phase3_init_args(
            config_path=config_path,
            data_dir=data_dir,
        )
    )
    return config_path


async def persist_bootstrap(
    *,
    config_path: Path,
    task_id: str,
    task_root: Path,
    workflow_definition: WorkflowDefinitionFile,
    revision_no: int,
) -> None:
    with cli._command_env(config_path=config_path):
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
        await wait_for_runtime_effects(task_id=task_id)


async def bootstrap_parent_runtime(
    *,
    config_path: Path,
    task_id: str,
    task_root: Path,
    compiler_version: str,
    workflow_key: str = "normal-parent-first-release",
) -> None:
    with cli._command_env(config_path=config_path):
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
        await wait_for_runtime_effects(task_id=task_id)


async def current_session_key(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    client: AsyncClient | None = None,
    expected_active_flow_revision_id: str | None = None,
) -> str:
    if client is None or expected_active_flow_revision_id is None:
        for _ in range(20):
            async with session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                dispatch = await _load_live_dispatch(session, task_id=task_id, flow=flow)
                if (
                    dispatch is not None
                    and dispatch.control_state == "live"
                    and dispatch.closed_at is None
                    and isinstance(dispatch.gateway_session_key, str)
                ):
                    return dispatch.gateway_session_key
            await asyncio.sleep(0.05)
        raise AssertionError(f"task '{task_id}' did not expose a live dispatch session key")

    if client is not None and expected_active_flow_revision_id is not None:
        resumed_key = await _resume_live_dispatch_if_needed(
            session_factory=session_factory,
            task_id=task_id,
            client=client,
            expected_active_flow_revision_id=expected_active_flow_revision_id,
        )
        if resumed_key is not None:
            return resumed_key
    for _ in range(20):
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            if (
                flow.current_open_dispatch_id is None
                and client is not None
                and expected_active_flow_revision_id is not None
            ):
                await _continue_latest_dispatch(
                    session=session,
                    client=client,
                    task_id=task_id,
                    expected_active_flow_revision_id=expected_active_flow_revision_id,
                )
            dispatch = await _load_live_dispatch(session, task_id=task_id, flow=flow)
            if (
                dispatch is not None
                and dispatch.control_state == "live"
                and dispatch.closed_at is None
                and isinstance(dispatch.gateway_session_key, str)
            ):
                return dispatch.gateway_session_key
        await wait_for_runtime_effects(task_id=task_id)
    raise AssertionError(f"task '{task_id}' did not reopen a live dispatch session key")


async def _resume_live_dispatch_if_needed(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    client: AsyncClient,
    expected_active_flow_revision_id: str,
) -> str | None:
    await wait_for_runtime_effects(task_id=task_id)
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        dispatch = await _load_live_dispatch(session, task_id=task_id, flow=flow)
        if (
            dispatch is not None
            and dispatch.control_state == "live"
            and dispatch.closed_at is None
            and isinstance(dispatch.gateway_session_key, str)
        ):
            return dispatch.gateway_session_key
        if flow.current_open_dispatch_id is None:
            await _continue_latest_dispatch(
                session=session,
                client=client,
                task_id=task_id,
                expected_active_flow_revision_id=expected_active_flow_revision_id,
            )
            await wait_for_runtime_effects(task_id=task_id)
            return None
        if (
            flow.current_open_dispatch_id is not None
            and dispatch is not None
            and dispatch.delivery_status not in {"provider_completed", "provider_failed"}
        ):
            assert dispatch.accepted_boundary is not None or dispatch.closed_at is not None
            dispatch.delivery_status = "provider_completed"
            await session.commit()
            await wait_for_runtime_effects(task_id=task_id)
    resumed = await client.post(
        f"/runtime/tasks/{task_id}/continue",
        headers=OPERATOR_HEADERS,
        params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
    )
    assert resumed.status_code == 200
    await wait_for_runtime_effects(task_id=task_id)
    return None


async def _continue_latest_dispatch(
    *,
    session: AsyncSession,
    client: AsyncClient,
    task_id: str,
    expected_active_flow_revision_id: str,
) -> None:
    latest_dispatch = await session.scalar(
        select(DispatchTurnModel)
        .where(DispatchTurnModel.task_id == task_id)
        .order_by(DispatchTurnModel.rendered_at.desc())
    )
    assert latest_dispatch is not None
    latest_dispatch.delivery_status = "provider_completed"
    latest_dispatch.control_state = "fenced"
    latest_dispatch.control_deadline_at = None
    latest_dispatch.fenced_at = latest_dispatch.fenced_at or latest_dispatch.closed_at
    if latest_dispatch.fenced_at is None:
        latest_dispatch.fenced_at = datetime.now(tz=UTC)
    await session.commit()
    resumed = await client.post(
        f"/runtime/tasks/{task_id}/continue",
        headers=OPERATOR_HEADERS,
        params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
    )
    assert resumed.status_code == 200


async def _load_live_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
) -> DispatchTurnModel | None:
    dispatch_id = flow.current_open_dispatch_id
    if dispatch_id is not None:
        return await session.get(DispatchTurnModel, dispatch_id)
    return cast(
        DispatchTurnModel | None,
        await session.scalar(
        select(DispatchTurnModel)
        .where(
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.control_state == "live",
            DispatchTurnModel.closed_at.is_(None),
            DispatchTurnModel.gateway_session_key.is_not(None),
        )
        .order_by(DispatchTurnModel.rendered_at.desc())
        ),
    )


async def stage_child_dispatch(
    api: Phase3RuntimeApi,
    *,
    task_id: str,
    child_node_key: str = "implement_change",
) -> ChildDispatchStage:
    runtime_read = await runtime_read_json(api.client, task_id)
    root_session_key = await current_session_key(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=cast(str, runtime_read["active_flow_revision_id"]),
    )
    assign = await assign_child(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        child_node_key=child_node_key,
        active_flow_revision_id=cast(str, runtime_read["active_flow_revision_id"]),
    )
    assert assign.status_code == 200
    yielded = await boundary(
        api.client,
        task_id=task_id,
        session_key=root_session_key,
        boundary_name="yield",
    )
    assert yielded.status_code == 200
    active_flow_revision_id = cast(
        str,
        yielded.json()["flow"]["active_flow_revision_id"],
    )
    worker_session_key = await current_session_key(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=active_flow_revision_id,
    )
    return ChildDispatchStage(
        root_session_key=root_session_key,
        worker_session_key=worker_session_key,
        active_flow_revision_id=active_flow_revision_id,
    )


def write_workspace_file(task_root: Path, relative_path: str, body: str) -> Path:
    output_path = task_root / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return output_path


async def drive_minimal_child_to_green(
    api: Phase3RuntimeApi,
    *,
    task_id: str,
    task_root: Path,
) -> tuple[str, str]:
    stage = await stage_child_dispatch(api, task_id=task_id)
    patch_file = write_workspace_file(
        task_root,
        "workspace/change_patch.diff",
        "diff --git a b",
    )
    verification_file = write_workspace_file(
        task_root,
        "workspace/verification_report.md",
        "verification passed",
    )
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        outcome="green",
        summary="done",
        next_step="root should verify the bounded change and close the flow.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(patch_file)},
            {"slot": "verification_report", "path": str(verification_file)},
        ],
    )
    assert checkpoint.status_code == 200
    worker_green = await boundary(
        api.client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        boundary_name="green",
    )
    assert worker_green.status_code == 200
    await wait_for_runtime_effects(task_id=task_id)
    root_session_key = await current_session_key(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=cast(
            str,
            worker_green.json()["flow"]["active_flow_revision_id"],
        ),
    )
    resumed_root = await runtime_read_json(api.client, task_id)
    return root_session_key, cast(str, resumed_root["active_flow_revision_id"])


__all__ = [
    "OPERATOR_HEADERS",
    "ChildDispatchStage",
    "Phase3RuntimeApi",
    "assign_child",
    "bootstrap_parent_runtime",
    "boundary",
    "continue_flow",
    "current_session_key",
    "drive_minimal_child_to_green",
    "parent_tool",
    "pause_flow",
    "persist_bootstrap",
    "phase3_init_args",
    "phase3_runtime_api",
    "prepare_runtime_db",
    "record_checkpoint",
    "runtime_read_json",
    "stage_child_dispatch",
    "write_workspace_file",
]
