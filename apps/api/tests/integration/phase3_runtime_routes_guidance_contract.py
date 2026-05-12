from __future__ import annotations

from pathlib import Path
from typing import TypedDict, cast

from app.db import AssignmentModel, FlowModel, FlowNodeModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.phase3_runtime_routes_support import (
    Phase3RouteContext,
    assert_operator_current_paths,
    launch_route_task,
    phase3_route_context,
)


class ProducesArtifact(TypedDict):
    slot: str
    description: str
    file_hint: str


async def test_phase3_runtime_routes_map_stale_lineage_to_stale_dispatch(
    tmp_path: Path,
) -> None:
    async with phase3_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_guidance",
            task_root_name="task-guidance-root",
        )
        original_attempt_id = await set_current_assignment_attempt(
            context,
            task_id=task.task_id,
            current_attempt_id=None,
        )

        stale_lineage = await context.client.post(
            f"/callback/tasks/{task.task_id}/boundary",
            headers={"X-Autoclaw-Session-Key": task.session_key},
            json={"boundary": "yield"},
        )
        assert stale_lineage.status_code == 409
        assert stale_lineage.json()["detail"]["code"] == "stale_dispatch"

        await set_current_assignment_attempt(
            context,
            task_id=task.task_id,
            current_attempt_id=original_attempt_id,
        )


async def test_phase3_runtime_routes_map_paused_callback_to_illegal_state(
    tmp_path: Path,
) -> None:
    async with phase3_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_guidance",
            task_root_name="task-guidance-root",
        )
        await set_flow_status(context, task_id=task.task_id, status="paused")

        inactive_callback = await context.client.post(
            f"/callback/tasks/{task.task_id}/boundary",
            headers={"X-Autoclaw-Session-Key": task.session_key},
            json={"boundary": "yield"},
        )
        assert inactive_callback.status_code == 422
        assert inactive_callback.json()["detail"]["code"] == "illegal_state"
        assert inactive_callback.json()["detail"]["suggested_next_step"] == (
            "Reread the current runtime status and dispatch context, then use the operator lane "
            "to resume or inspect the task before sending more callback writes."
        )


async def test_phase3_runtime_routes_surface_paused_snapshot_continue_action(
    tmp_path: Path,
) -> None:
    async with phase3_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_guidance",
            task_root_name="task-guidance-root",
        )
        await set_flow_status(context, task_id=task.task_id, status="paused")

        paused_snapshot = await context.client.get(
            f"/operator/tasks/{task.task_id}/snapshot",
            headers=context.operator_headers,
        )
        assert paused_snapshot.status_code == 200
        paused_snapshot_json = paused_snapshot.json()
        assert paused_snapshot_json["top_actionable_items"][0]["suggested_action"] == "continue"
        assert (
            paused_snapshot_json["top_actionable_items"][0]["current_paths"]
            == paused_snapshot_json["current_paths"]
        )
        assert_operator_current_paths(paused_snapshot_json["current_paths"])


async def test_phase3_runtime_routes_map_missing_release_basis_to_missing_publication(
    tmp_path: Path,
) -> None:
    async with phase3_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_guidance",
            task_root_name="task-guidance-root",
        )
        await set_assignment_produces(
            context,
            task_id=task.task_id,
            produces_json=[
                {
                    "slot": "missing_release_basis",
                    "description": "Synthetic required release basis for route mapping.",
                    "file_hint": "missing_release_basis.md",
                }
            ],
        )

        missing_publication = await context.client.post(
            f"/callback/tasks/{task.task_id}/tools/release_green",
            headers={"X-Autoclaw-Session-Key": task.session_key},
            json={
                "tool_name": "release_green",
                "payload": {},
                "expected_structural_revision_id": task.active_flow_revision_id,
            },
        )
        assert missing_publication.status_code == 422
        assert missing_publication.json()["detail"]["code"] == "missing_required_publication"
        assert missing_publication.json()["detail"]["suggested_next_step"] == (
            "Publish or republish the missing durable or surfaced release basis first, then "
            "retry the control action or reread the surfaced release inputs."
        )


async def test_phase3_runtime_routes_surface_blocked_snapshot_without_action(
    tmp_path: Path,
) -> None:
    async with phase3_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_guidance",
            task_root_name="task-guidance-root",
        )
        await set_flow_status(context, task_id=task.task_id, status="blocked")

        blocked_snapshot = await context.client.get(
            f"/operator/tasks/{task.task_id}/snapshot",
            headers=context.operator_headers,
        )
        assert blocked_snapshot.status_code == 200
        blocked_snapshot_json = blocked_snapshot.json()
        assert blocked_snapshot_json["top_actionable_items"][0]["suggested_action"] is None
        assert (
            blocked_snapshot_json["top_actionable_items"][0]["current_paths"]
            == blocked_snapshot_json["current_paths"]
        )
        assert_operator_current_paths(blocked_snapshot_json["current_paths"])


async def set_current_assignment_attempt(
    context: Phase3RouteContext,
    *,
    task_id: str,
    current_attempt_id: str | None,
) -> str | None:
    async with context.session_factory() as session:
        _, _, assignment = await load_current_assignment(session, task_id=task_id)
        original_attempt_id = assignment.current_attempt_id
        assignment.current_attempt_id = current_attempt_id
        await session.commit()
    return original_attempt_id


async def set_flow_status(
    context: Phase3RouteContext,
    *,
    task_id: str,
    status: str,
) -> None:
    async with context.session_factory() as session:
        flow = await session.get(FlowModel, f"flow.{task_id}")
        assert flow is not None
        flow.status = status
        await session.commit()


async def set_assignment_produces(
    context: Phase3RouteContext,
    *,
    task_id: str,
    produces_json: list[ProducesArtifact],
) -> None:
    async with context.session_factory() as session:
        _, _, assignment = await load_current_assignment(session, task_id=task_id)
        assignment.produces_json = cast(list[dict[str, object]], produces_json)
        await session.commit()


async def load_current_assignment(
    session: AsyncSession,
    *,
    task_id: str,
) -> tuple[FlowModel, FlowNodeModel, AssignmentModel]:
    flow = await session.get(FlowModel, f"flow.{task_id}")
    assert flow is not None
    assert flow.active_flow_revision_id is not None
    assert flow.current_node_key is not None
    node = await session.scalar(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
            FlowNodeModel.node_key == flow.current_node_key,
        )
    )
    assert node is not None
    assert node.current_assignment_id is not None
    assignment = await session.get(AssignmentModel, node.current_assignment_id)
    assert assignment is not None
    return flow, node, assignment
