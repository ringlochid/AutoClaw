from __future__ import annotations

from pathlib import Path
from typing import cast

from autoclaw.db import FlowModel
from autoclaw.runtime.effects import drive_runtime_once, wait_for_runtime_effects
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_wait_effects import mark_dispatch_provider_completed
from tests.integration.phase3.callback_api import (
    ChildDispatchStage,
    Phase3RuntimeApi,
    assign_child,
    boundary,
    record_checkpoint,
    runtime_read_json,
)
from tests.integration.phase3.runtime_harness.live_dispatch import (
    live_node_session_key_for_dispatch,
    load_live_dispatch,
    resume_live_dispatch_if_needed,
)


async def current_session_key(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> str:
    for _ in range(40):
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            dispatch = await load_live_dispatch(session, task_id=task_id, flow=flow)
            session_key = await live_node_session_key_for_dispatch(session, dispatch=dispatch)
            if session_key is not None:
                return session_key
        await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
        await drive_runtime_once(task_id=task_id)
    raise AssertionError(f"task '{task_id}' did not expose a live dispatch session key")


async def current_open_dispatch_id(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> str:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        return flow.current_open_dispatch_id


async def current_session_key_after_dispatch_progress(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    client: AsyncClient,
    expected_active_flow_revision_id: str,
) -> str:
    for _ in range(40):
        dispatch_id_to_progress: str | None = None
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            dispatch = await load_live_dispatch(session, task_id=task_id, flow=flow)
            session_key = await live_node_session_key_for_dispatch(session, dispatch=dispatch)
            if (
                dispatch is not None
                and dispatch.accepted_boundary is None
                and session_key is not None
                and dispatch.node_key == flow.current_node_key
            ):
                return session_key
            if dispatch is not None and dispatch.accepted_boundary is not None:
                dispatch_id_to_progress = dispatch.dispatch_id
        if dispatch_id_to_progress is not None:
            await mark_dispatch_provider_completed(
                session_factory,
                dispatch_id=dispatch_id_to_progress,
            )
        resumed_key = await resume_live_dispatch_if_needed(
            session_factory=session_factory,
            task_id=task_id,
            client=client,
            expected_active_flow_revision_id=expected_active_flow_revision_id,
        )
        if resumed_key is not None:
            return resumed_key
        await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
        await drive_runtime_once(task_id=task_id)
    raise AssertionError(f"task '{task_id}' did not expose a progressed live dispatch session key")


async def current_session_key_after_dispatch_progress_for_node(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    client: AsyncClient,
    expected_active_flow_revision_id: str,
    expected_node_key: str,
) -> str:
    for _ in range(40):
        dispatch_id_to_progress: str | None = None
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            dispatch = await load_live_dispatch(session, task_id=task_id, flow=flow)
            session_key = await live_node_session_key_for_dispatch(session, dispatch=dispatch)
            if (
                flow.current_node_key == expected_node_key
                and dispatch is not None
                and dispatch.node_key == expected_node_key
                and dispatch.accepted_boundary is None
                and session_key is not None
            ):
                return session_key
            if (
                dispatch is not None
                and dispatch.node_key != expected_node_key
                and dispatch is not None
                and dispatch.accepted_boundary is not None
            ):
                dispatch_id_to_progress = dispatch.dispatch_id
        if dispatch_id_to_progress is not None:
            await mark_dispatch_provider_completed(
                session_factory,
                dispatch_id=dispatch_id_to_progress,
            )
        await resume_live_dispatch_if_needed(
            session_factory=session_factory,
            task_id=task_id,
            client=client,
            expected_active_flow_revision_id=expected_active_flow_revision_id,
        )
        await wait_for_runtime_effects(task_id=task_id, max_wait_seconds=2.0)
        await drive_runtime_once(task_id=task_id)
    raise AssertionError(
        "task "
        f"'{task_id}' did not expose a live dispatch session key for node "
        f"'{expected_node_key}'"
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
    assert yielded.json()["flow"]["current_node_key"] == child_node_key
    active_flow_revision_id = cast(str, yielded.json()["flow"]["active_flow_revision_id"])
    worker_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=active_flow_revision_id,
        expected_node_key=child_node_key,
    )
    return ChildDispatchStage(
        root_session_key,
        worker_session_key,
        active_flow_revision_id,
        child_node_key,
    )


async def _retry_child_checkpoint(
    *,
    api: Phase3RuntimeApi,
    stage: ChildDispatchStage,
    task_id: str,
    outcome: str,
    summary: str,
    next_step: str,
    produced_artifacts: list[dict[str, str]],
) -> tuple[Response, str]:
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        outcome=outcome,
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts,
    )
    if checkpoint.status_code != 409:
        return checkpoint, stage.worker_session_key
    refreshed_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=stage.active_flow_revision_id,
        expected_node_key=stage.worker_node_key,
    )
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=refreshed_session_key,
        outcome=outcome,
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts,
    )
    return checkpoint, refreshed_session_key


async def retry_terminal_green_checkpoint(
    api: Phase3RuntimeApi,
    *,
    stage: ChildDispatchStage,
    task_id: str,
    summary: str,
    next_step: str,
    produced_artifacts: list[dict[str, str]] | None = None,
) -> tuple[Response, str]:
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=stage.worker_session_key,
        outcome="green",
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts or [],
    )
    if checkpoint.status_code != 409:
        return checkpoint, stage.worker_session_key
    refreshed_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=stage.active_flow_revision_id,
        expected_node_key=stage.worker_node_key,
    )
    checkpoint = await record_checkpoint(
        api.client,
        task_id=task_id,
        session_key=refreshed_session_key,
        outcome="green",
        summary=summary,
        next_step=next_step,
        produced_artifacts=produced_artifacts or [],
    )
    return checkpoint, refreshed_session_key


async def _retry_child_boundary(
    *,
    api: Phase3RuntimeApi,
    stage: ChildDispatchStage,
    task_id: str,
    session_key: str,
    boundary_name: str,
) -> Response:
    boundary_response = await boundary(
        api.client,
        task_id=task_id,
        session_key=session_key,
        boundary_name=boundary_name,
    )
    if boundary_response.status_code != 409:
        return boundary_response
    refreshed_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=stage.active_flow_revision_id,
        expected_node_key=stage.worker_node_key,
    )
    return await boundary(
        api.client,
        task_id=task_id,
        session_key=refreshed_session_key,
        boundary_name=boundary_name,
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
    checkpoint, worker_session_key = await _retry_child_checkpoint(
        api=api,
        stage=stage,
        task_id=task_id,
        outcome="green",
        summary="done",
        next_step="root should verify the bounded change and close the flow.",
        produced_artifacts=[
            {"slot": "change_patch", "path": str(patch_file)},
            {"slot": "verification_report", "path": str(verification_file)},
        ],
    )
    assert checkpoint.status_code == 200
    worker_green = await _retry_child_boundary(
        api=api,
        stage=stage,
        task_id=task_id,
        session_key=worker_session_key,
        boundary_name="green",
    )
    assert worker_green.status_code == 200
    assert worker_green.json()["flow"]["current_node_key"] == "root"
    root_session_key = await current_session_key_after_dispatch_progress_for_node(
        session_factory=api.session_factory,
        task_id=task_id,
        client=api.client,
        expected_active_flow_revision_id=stage.active_flow_revision_id,
        expected_node_key="root",
    )
    resumed_root = await runtime_read_json(api.client, task_id)
    return root_session_key, cast(str, resumed_root["active_flow_revision_id"])


__all__ = [
    "current_session_key",
    "current_session_key_after_dispatch_progress",
    "current_session_key_after_dispatch_progress_for_node",
    "drive_minimal_child_to_green",
    "retry_terminal_green_checkpoint",
    "stage_child_dispatch",
    "write_workspace_file",
]
