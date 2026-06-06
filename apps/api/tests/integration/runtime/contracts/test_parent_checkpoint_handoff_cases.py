from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from autoclaw.persistence import DispatchTurnModel, FlowModel
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.projection.dispatch.prompt import render_dispatch_prompt
from autoclaw.runtime.projection.manifest.projection import build_dispatch_manifest_projection
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.runtime_dispatch_support import mark_dispatch_provider_completed
from tests.helpers.runtime_support import (
    assign_child,
    boundary,
    current_session_key,
    current_session_key_after_dispatch_progress,
    persist_bootstrap,
    prepare_runtime_db,
    record_checkpoint,
    runtime_api_context,
    runtime_read_json,
)
from tests.helpers.seeded_runtime_support import load_workflow_definition

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]

async def _current_child_dispatch_prompt(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> tuple[Any, tuple[Any, Any]]:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id is not None
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        assert dispatch is not None
        manifest = await build_dispatch_manifest_projection(
            session,
            task_id=task_id,
            dispatch=dispatch,
        )
        return manifest, await render_dispatch_prompt(session, task_id, dispatch)


@pytest.mark.asyncio
async def test_child_dispatch_after_parent_yield_does_not_surface_parent_checkpoint(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_parent_yield_child_checkpoint_split"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("normal_parent_first_release"),
            revision_no=7,
        )

        async with runtime_api_context(config_path) as api:
            root_session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            runtime_read = await runtime_read_json(api.client, task_id)
            progress = await record_checkpoint(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                checkpoint_kind="progress",
                outcome=None,
                summary="Parent progress checkpoint that must not leak into child context.",
                next_step=(
                    "Stage child work without surfacing the parent checkpoint as child handoff."
                ),
            )
            assert progress.status_code == 200
            assign = await assign_child(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                child_node_key="implementation_subtree",
                active_flow_revision_id=runtime_read["active_flow_revision_id"],
            )
            assert assign.status_code == 200

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                assert flow.current_open_dispatch_id is not None
                parent_dispatch_id = flow.current_open_dispatch_id

            yielded = await boundary(
                api.client,
                task_id=task_id,
                session_key=root_session_key,
                boundary_name="yield",
            )
            assert yielded.status_code == 200
            await mark_dispatch_provider_completed(
                api.session_factory,
                dispatch_id=parent_dispatch_id,
            )
            await current_session_key_after_dispatch_progress(
                session_factory=api.session_factory,
                task_id=task_id,
                client=api.client,
                expected_active_flow_revision_id=yielded.json()["flow"]["active_flow_revision_id"],
            )
            manifest, (bundle, _) = await _current_child_dispatch_prompt(
                session_factory=api.session_factory,
                task_id=task_id,
            )

            assert manifest.current_context.latest_relevant_checkpoint_path is None
            assert "Parent progress checkpoint that must not leak into child context." not in (
                bundle.full_markdown
            )
            assert "- no current relevant checkpoint is surfaced" in bundle.full_markdown
    finally:
        await dispose_db_engine()


__all__ = ["test_child_dispatch_after_parent_yield_does_not_surface_parent_checkpoint"]
