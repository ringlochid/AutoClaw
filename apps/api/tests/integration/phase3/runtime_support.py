from __future__ import annotations

import argparse
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from app import cli
from app.config import get_settings
from app.db import DispatchCallbackBindingModel, DispatchTurnModel, FlowModel
from app.db.session import get_session_factory
from app.main import create_app
from app.runtime.effects import wait_for_runtime_effects
from app.schemas.definitions.workflow import WorkflowDefinitionFile
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload

OPERATOR_HEADERS = {"X-AutoClaw-API-Key": "api-test-key"}


@dataclass(frozen=True)
class Phase3RuntimeApi:
    session_factory: async_sessionmaker[AsyncSession]
    client: AsyncClient


@dataclass(frozen=True)
class ChildDispatchStage:
    root_session_key: str
    worker_session_key: str
    active_flow_revision_id: str


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


@asynccontextmanager
async def phase3_runtime_api(config_path: Path) -> AsyncIterator[Phase3RuntimeApi]:
    with cli._command_env(config_path=config_path):
        get_settings.cache_clear()
        session_factory = get_session_factory()
        app = create_app()
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                yield Phase3RuntimeApi(
                    session_factory=session_factory,
                    client=client,
                )


async def runtime_read_json(client: AsyncClient, task_id: str) -> dict[str, Any]:
    response = await client.get(
        f"/runtime/tasks/{task_id}",
        headers=OPERATOR_HEADERS,
    )
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


async def current_session_key(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    client: AsyncClient | None = None,
    expected_active_flow_revision_id: str | None = None,
) -> str:
    if client is not None and expected_active_flow_revision_id is not None:
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            assert flow.current_open_dispatch_id is not None
            dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
            assert dispatch is not None
            dispatch.delivery_status = "provider_completed"
            await session.commit()
        resumed = await client.post(
            f"/runtime/tasks/{task_id}/continue",
            headers=OPERATOR_HEADERS,
            params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
        )
        assert resumed.status_code == 200
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        binding = await session.get(
            DispatchCallbackBindingModel,
            f"dispatch-callback-binding.{flow.current_open_dispatch_id}",
        )
        assert binding is not None
        assert binding.binding_status == "live"
        assert isinstance(binding.session_key, str)
        return binding.session_key


async def parent_tool(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    tool_name: str,
    payload: dict[str, Any],
    active_flow_revision_id: str,
) -> Response:
    return await client.post(
        f"/callback/tasks/{task_id}/tools/{tool_name}",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={
            "tool_name": tool_name,
            "payload": payload,
            "expected_structural_revision_id": active_flow_revision_id,
        },
    )


async def assign_child(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    child_node_key: str,
    active_flow_revision_id: str,
    summary: str = "go",
    instruction: str = "go",
) -> Response:
    return await parent_tool(
        client,
        task_id=task_id,
        session_key=session_key,
        tool_name="assign_child",
        payload={
            "child_node_key": child_node_key,
            "assignment_intent": {
                "summary": summary,
                "instruction": instruction,
            },
        },
        active_flow_revision_id=active_flow_revision_id,
    )


async def boundary(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    boundary_name: str,
) -> Response:
    return await client.post(
        f"/callback/tasks/{task_id}/boundary",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"boundary": boundary_name},
    )


async def pause_flow(
    client: AsyncClient,
    *,
    task_id: str,
    active_flow_revision_id: str,
) -> Response:
    return await client.post(
        f"/runtime/tasks/{task_id}/pause",
        headers=OPERATOR_HEADERS,
        params={"expected_active_flow_revision_id": active_flow_revision_id},
    )


async def continue_flow(
    client: AsyncClient,
    *,
    task_id: str,
    active_flow_revision_id: str,
) -> Response:
    return await client.post(
        f"/runtime/tasks/{task_id}/continue",
        headers=OPERATOR_HEADERS,
        params={"expected_active_flow_revision_id": active_flow_revision_id},
    )


async def record_checkpoint(
    client: AsyncClient,
    *,
    task_id: str,
    session_key: str,
    checkpoint_kind: str = "terminal",
    outcome: str | None,
    summary: str,
    next_step: str,
    produced_artifacts: Sequence[dict[str, str]] = (),
    transient_surfaces: Sequence[dict[str, str]] = (),
) -> Response:
    checkpoint: dict[str, Any] = {
        "checkpoint_kind": checkpoint_kind,
        "handoff": {
            "summary": summary,
            "next_step": next_step,
        },
    }
    if outcome is not None:
        checkpoint["outcome"] = outcome
    if produced_artifacts:
        checkpoint["produced_artifacts"] = list(produced_artifacts)
    if transient_surfaces:
        checkpoint["transient_surfaces"] = list(transient_surfaces)
    return await client.post(
        f"/callback/tasks/{task_id}/checkpoint",
        headers={"X-Autoclaw-Session-Key": session_key},
        json={"checkpoint": checkpoint},
    )


async def stage_child_dispatch(
    api: Phase3RuntimeApi,
    *,
    task_id: str,
    child_node_key: str = "implement_change",
) -> ChildDispatchStage:
    root_session_key = await current_session_key(
        session_factory=api.session_factory,
        task_id=task_id,
    )
    runtime_read = await runtime_read_json(api.client, task_id)
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
