from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.persistence import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    FlowModel,
    FlowNodeModel,
)
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.post_commit import drive_runtime_once
from httpx import AsyncClient, Response
from sqlalchemy import select
from tests.helpers.runtime_support import (
    drive_bounded_child_to_green,
    parent_tool,
    persist_bootstrap,
    prepare_runtime_db,
    runtime_api_context,
)
from tests.helpers.seeded_runtime_support import load_workflow_definition

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def release_green(
    *,
    task_id: str,
    session_key: str,
    active_flow_revision_id: str,
    client: AsyncClient,
) -> Response:
    return await parent_tool(
        client,
        task_id=task_id,
        session_key=session_key,
        tool_name="release_green",
        payload={},
        active_flow_revision_id=active_flow_revision_id,
    )


@pytest.mark.asyncio
async def test_release_green_uses_relational_children_and_maps_stale_checkpoint_to_409(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_release_relational_child"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("bounded_change"),
            revision_no=1,
        )

        async with runtime_api_context(config_path) as api:
            root_session_key, active_flow_revision_id = await drive_bounded_child_to_green(
                api,
                task_id=task_id,
                task_root=task_root,
            )
            await drive_runtime_once(task_id=task_id)

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                child_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                        FlowNodeModel.node_key == "implement_change",
                    )
                )
                assert child_node is not None
                assert child_node.current_assignment_id is not None
                child_assignment = await session.get(
                    AssignmentModel,
                    child_node.current_assignment_id,
                )
                assert child_assignment is not None
                assert child_assignment.current_attempt_id is not None
                child_node.parent_node_key = child_node.node_key
                checkpoint_dir = (
                    task_root / "_runtime" / "attempts" / child_assignment.current_attempt_id
                )
                (checkpoint_dir / "latest-checkpoint.json").unlink()
                (checkpoint_dir / "latest-checkpoint.md").unlink()
                await session.commit()

            release = await release_green(
                client=api.client,
                task_id=task_id,
                session_key=root_session_key,
                active_flow_revision_id=active_flow_revision_id,
            )
            assert release.status_code == 409
            detail = release.json()["detail"]
            assert detail["code"] == "stale_checkpoint"
            assert "requires current checkpoint evidence" in detail["summary"]
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_release_green_keeps_missing_required_publication_on_422(tmp_path: Path) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_release_missing_publication"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("bounded_change"),
            revision_no=1,
        )

        async with runtime_api_context(config_path) as api:
            root_session_key, active_flow_revision_id = await drive_bounded_child_to_green(
                api,
                task_id=task_id,
                task_root=task_root,
            )

            async with api.session_factory() as session:
                flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
                assert flow is not None
                root_node = await session.scalar(
                    select(FlowNodeModel).where(
                        FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                        FlowNodeModel.node_key == "root",
                    )
                )
                assert root_node is not None
                assert root_node.current_assignment_id is not None
                root_assignment = await session.get(
                    AssignmentModel,
                    root_node.current_assignment_id,
                )
                assert root_assignment is not None
                root_assignment.produces_json = [
                    {
                        "slot": "missing_release_basis",
                        "description": "Synthetic required release basis for route mapping.",
                        "file_hint": "missing_release_basis.md",
                    }
                ]
                await session.commit()

            release = await release_green(
                client=api.client,
                task_id=task_id,
                session_key=root_session_key,
                active_flow_revision_id=active_flow_revision_id,
            )
            assert release.status_code == 422
            detail = release.json()["detail"]
            assert detail["code"] == "missing_required_publication"
            assert detail["summary"].startswith("missing required publication")
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_release_green_maps_missing_child_current_publication_to_422(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    task_root = tmp_path / "task-root"
    task_id = "task_release_missing_child_publication"

    try:
        await persist_bootstrap(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            workflow_definition=load_workflow_definition("bounded_change"),
            revision_no=1,
        )

        async with runtime_api_context(config_path) as api:
            root_session_key, active_flow_revision_id = await drive_bounded_child_to_green(
                api,
                task_id=task_id,
                task_root=task_root,
            )

            async with api.session_factory() as session:
                current_pointer = await session.scalar(
                    select(ArtifactCurrentPointerModel).where(
                        ArtifactCurrentPointerModel.task_id == task_id,
                        ArtifactCurrentPointerModel.owner_node_key == "implement_change",
                        ArtifactCurrentPointerModel.slot == "change_patch",
                    )
                )
                assert current_pointer is not None
                await session.delete(current_pointer)
                await session.commit()

            release = await release_green(
                client=api.client,
                task_id=task_id,
                session_key=root_session_key,
                active_flow_revision_id=active_flow_revision_id,
            )
            assert release.status_code == 422
            detail = release.json()["detail"]
            assert detail["code"] == "missing_required_publication"
            assert detail["summary"].startswith("missing required publication")
    finally:
        await dispose_db_engine()


__all__ = [
    "test_release_green_keeps_missing_required_publication_on_422",
    "test_release_green_maps_missing_child_current_publication_to_422",
    "test_release_green_uses_relational_children_and_maps_stale_checkpoint_to_409",
]
