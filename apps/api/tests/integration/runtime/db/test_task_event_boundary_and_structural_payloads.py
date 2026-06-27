from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from autoclaw.persistence import TaskEventModel
from autoclaw.runtime import CheckpointOutcome, runtime_flow_read
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.runtime.db.actions import (
    add_child_on_current_flow,
    remove_child_on_current_flow,
    run_child_outcome,
)
from tests.integration.runtime.db.context import (
    RuntimeDatabaseContext,
    launch_runtime_case,
    runtime_database_context,
)
from tests.integration.runtime.db.workflows import root_blocked_workflow

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]
type JsonObject = dict[str, Any]


async def test_task_events_emit_structural_revision_adopted_for_add_and_remove_child(
    tmp_path: Path,
) -> None:
    task_id = "task_db_structural_event_coverage"
    async with runtime_database_context(tmp_path, task_root_name="task-root") as context:
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key="normal-parent-first-release",
            compiler_version="task-event-runtime-family-coverage",
        )
        original_flow_revision_id = await active_flow_revision_id(context, task_id=task_id)

        await add_child_on_current_flow(
            context,
            task_id=task_id,
            child={
                "node_key": "qa_probe",
                "role": "architect",
                "description": "Probe child added for runtime event coverage.",
            },
        )
        added_flow_revision_id = await active_flow_revision_id(context, task_id=task_id)

        await remove_child_on_current_flow(
            context,
            task_id=task_id,
            child_node_key="qa_probe",
        )
        removed_flow_revision_id = await active_flow_revision_id(context, task_id=task_id)

        async with context.session_factory() as session:
            structural_events = await task_events_for_task(
                session,
                task_id=task_id,
                event_type="structural_revision_adopted",
            )

    assert [payload(event)["operation"] for event in structural_events] == [
        "add_child",
        "remove_child",
    ]

    add_event_payload = payload(structural_events[0])
    assert add_event_payload["previous_flow_revision_id"] == original_flow_revision_id
    assert add_event_payload["active_flow_revision_id"] == added_flow_revision_id
    assert add_event_payload["target_node_key"] == "qa_probe"
    assert add_event_payload["affected_node_keys"] == ["qa_probe"]

    remove_event_payload = payload(structural_events[1])
    assert remove_event_payload["previous_flow_revision_id"] == added_flow_revision_id
    assert remove_event_payload["active_flow_revision_id"] == removed_flow_revision_id
    assert remove_event_payload["target_node_key"] == "qa_probe"
    assert remove_event_payload["affected_node_keys"] == ["qa_probe"]


@pytest.mark.parametrize(
    ("outcome", "expected_boundary"),
    (
        (CheckpointOutcome.GREEN, "green"),
        (CheckpointOutcome.RETRY, "retry"),
        (CheckpointOutcome.BLOCKED, "blocked"),
    ),
)
async def test_task_events_emit_terminal_boundary_payloads(
    tmp_path: Path,
    outcome: CheckpointOutcome,
    expected_boundary: str,
) -> None:
    task_id = f"task_db_boundary_event_{expected_boundary}"
    workflow_definition = root_blocked_workflow()
    async with runtime_database_context(tmp_path, task_root_name="task-root") as context:
        await launch_runtime_case(
            context,
            task_id=task_id,
            workflow_key=workflow_definition.id,
            compiler_version=f"task-event-boundary-{expected_boundary}",
            workflow_definition=workflow_definition,
        )
        continued_flow = await run_child_outcome(
            context,
            task_id=task_id,
            child_node_key="investigate_blocker",
            assignment_summary="Investigate the blocker.",
            assignment_instruction="Report whether the work should continue.",
            outcome=outcome,
            handoff_summary=f"Worker closed the blocker investigation as {expected_boundary}.",
            next_step=f"Continue from the accepted {expected_boundary} child boundary.",
        )

        async with context.session_factory() as session:
            boundary_events = await task_events_for_task(
                session,
                task_id=task_id,
                event_type="boundary_accepted",
            )

    matching_events = [
        event for event in boundary_events if payload(event)["boundary"] == expected_boundary
    ]
    assert matching_events
    boundary_event_payload = payload(matching_events[-1])
    continued_status = str(continued_flow.status)

    assert boundary_event_payload["previous_node_key"] == "investigate_blocker"
    assert boundary_event_payload["resulting_flow_status"] == continued_status
    assert boundary_event_payload["requires_reopen_after_inactivity"] is (
        continued_status == "running"
    )
    assert checkpoint_ref_name(boundary_event_payload, "latest_checkpoint_ref") == (
        "latest-checkpoint.md"
    )
    assert boundary_event_payload["next_node_key"] == continued_flow.current_node_key
    assert boundary_event_payload["next_attempt_id"] == continued_flow.active_attempt_id


async def active_flow_revision_id(
    context: RuntimeDatabaseContext,
    *,
    task_id: str,
) -> str:
    async with context.session_factory() as session:
        flow = await runtime_flow_read(session, task_id)
    return flow.active_flow_revision_id


async def task_events_for_task(
    session: AsyncSession,
    *,
    task_id: str,
    event_type: str,
) -> list[TaskEventModel]:
    return list(
        await session.scalars(
            select(TaskEventModel)
            .where(
                TaskEventModel.task_id == task_id,
                TaskEventModel.event_type == event_type,
            )
            .order_by(TaskEventModel.event_seq.asc())
        )
    )


def payload(event: TaskEventModel) -> JsonObject:
    return cast(JsonObject, event.payload)


def checkpoint_ref_name(event_payload: JsonObject, key: str) -> str:
    checkpoint_ref = cast(JsonObject, event_payload[key])
    path = checkpoint_ref["path"]
    assert isinstance(path, str)
    return Path(path).name
