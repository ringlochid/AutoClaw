from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from autoclaw.persistence import CommandRunModel, FlowModel, FlowWaitStateModel
from autoclaw.runtime.command_run_runner import (
    command_run_log_ref,
    drive_command_run_runner_once,
    start_command_run_runner,
)
from autoclaw.runtime.command_run_runner import service as command_run_runner_service
from autoclaw.runtime.command_runs import record_command_run_progress
from autoclaw.runtime.contracts import CommandRunProgressUpdate
from autoclaw.runtime.post_commit import write_runtime_operation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.runtime.command_run_runner_support import (
    assert_command_run_continues_task,
    command_run_events,
    python_command,
    start_runner_command_run,
    wait_for_command_run_state,
)
from tests.integration.runtime.routes.support import (
    RuntimeRouteContext,
    launch_route_task,
    runtime_route_context,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def test_command_runner_fails_unowned_running_run_and_continues_current_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(command_run_runner_service, "_UNOWNED_RUNNING_GRACE_SECONDS", 0.0)
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_command_runner_unowned_running",
            task_root_name="task-root",
        )
        command_run_dispatch_id = task.current_open_dispatch_id
        run_id = await start_runner_command_run(
            context,
            task,
            command=python_command("print('unowned process should not launch')"),
            workdir=None,
            timeout_seconds=120,
            should_drive_runner=False,
        )
        await record_running_progress(context, task_id=task.task_id, run_id=run_id)

        await start_command_run_runner()
        await drive_command_run_runner_once()
        command_run = await wait_for_command_run_state(
            context,
            task_id=task.task_id,
            run_id=run_id,
            expected_state="failed",
        )

        assert command_run.terminal_summary == (
            "command runner lost local process ownership before completion"
        )
        assert command_run.terminal_exit_code is None
        assert command_run.terminal_signal is None
        assert command_run.terminal_log_ref == command_run_log_ref(run_id)
        assert (task.task_root / str(command_run.terminal_log_ref)).is_file()
        await assert_unowned_running_terminal_truth(context, task_id=task.task_id, run_id=run_id)

        _continued_dispatch_id, prompt_path = await assert_command_run_continues_task(
            context,
            task,
            command_run_dispatch_id=command_run_dispatch_id,
        )
        prompt_text = prompt_path.read_text(encoding="utf-8")
        assert f"- run_id: {run_id}" in prompt_text
        assert "- state: failed" in prompt_text
        assert (
            "- summary: command runner lost local process ownership before completion"
            in prompt_text
        )
        assert f"- log_ref: {command_run_log_ref(run_id)}" in prompt_text
        await assert_flow_revision_remains_current(
            context,
            task_id=task.task_id,
            revision_id=task.active_flow_revision_id,
        )


async def record_running_progress(
    context: RuntimeRouteContext,
    *,
    task_id: str,
    run_id: str,
) -> None:
    async def operation(session: AsyncSession) -> None:
        await record_command_run_progress(
            session,
            task_id=task_id,
            update=CommandRunProgressUpdate(
                run_id=run_id,
                summary="command process started before runner restart",
                log_ref=command_run_log_ref(run_id),
                occurred_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
            ),
        )

    await write_runtime_operation(operation)


async def assert_unowned_running_terminal_truth(
    context: RuntimeRouteContext,
    *,
    task_id: str,
    run_id: str,
) -> None:
    terminal_events = await command_run_events(context, task_id, "command_run_failed")
    async with context.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        command_run = await session.get(CommandRunModel, run_id)
        wait_state = None if flow is None else await session.get(FlowWaitStateModel, flow.flow_id)

    assert flow is not None
    assert command_run is not None
    assert wait_state is None
    assert command_run.state == "failed"
    assert len(terminal_events) == 1
    event = terminal_events[0]
    assert event.event_source == "controller"
    assert event.flow_revision_id == command_run.flow_revision_id
    assert event.dispatch_id == command_run.dispatch_id
    assert event.attempt_id == command_run.attempt_id
    assert event.node_key == command_run.requester_node_key
    assert event.payload["run_id"] == run_id
    assert event.payload["state"] == "failed"
    assert event.payload["summary"] == command_run.terminal_summary
    assert event.payload["log_ref"] == command_run_log_ref(run_id)


async def assert_flow_revision_remains_current(
    context: RuntimeRouteContext,
    *,
    task_id: str,
    revision_id: str,
) -> None:
    async with context.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))

    assert flow is not None
    assert flow.active_flow_revision_id == revision_id
