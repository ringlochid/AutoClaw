from __future__ import annotations

import asyncio
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from autoclaw.persistence import (
    CommandRunModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    FlowWaitStateModel,
    PolicyRevisionModel,
    TaskEventModel,
)
from autoclaw.runtime.command_run_runner import (
    MAX_COMMAND_RUN_LOG_BYTES,
    command_run_log_ref,
    drive_command_run_runner_once,
    notify_command_run_runner,
    start_command_run_runner,
    stop_command_run_runner,
)
from autoclaw.runtime.command_runs import start_command_run
from autoclaw.runtime.contracts import CommandRunStartRequest, CommandRunStartResponse
from autoclaw.runtime.post_commit import drive_runtime_until, write_runtime_operation
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.runtime.routes.support import (
    RuntimeRouteContext,
    SeededRouteTask,
    launch_route_task,
    runtime_route_context,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def test_command_runner_launches_pending_run_from_wait_and_writes_log_ref(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_command_runner_launch",
            task_root_name="task-root",
        )
        await start_command_run_runner()
        command = python_command(
            "from pathlib import Path; "
            "Path('default-workdir.txt').write_text('ok', encoding='utf-8'); "
            "print('RUNNER_OUTPUT_' + 'SENTINEL')"
        )
        command_run_dispatch_id = task.current_open_dispatch_id

        run_id = await start_runner_command_run(
            context,
            task,
            command=command,
            workdir=None,
            timeout_seconds=5,
        )
        command_run = await wait_for_command_run_state(
            context,
            task_id=task.task_id,
            run_id=run_id,
            expected_state="succeeded",
        )

        assert (task.task_root / "workspace" / "default-workdir.txt").read_text(
            encoding="utf-8"
        ) == "ok"
        assert command_run.started_at is not None
        assert command_run.ended_at is not None
        assert command_run.terminal_summary == "command succeeded with exit code 0"
        assert command_run.terminal_exit_code == 0
        assert command_run.terminal_signal is None
        assert command_run.terminal_log_ref == command_run_log_ref(run_id)
        log_path = task.task_root / str(command_run.terminal_log_ref)
        assert log_path.is_file()
        log_text = log_path.read_text(encoding="utf-8")
        assert "$ " in log_text
        assert "RUNNER_OUTPUT_SENTINEL" in log_text

        _continued_dispatch_id, prompt_path = await assert_command_run_continues_task(
            context,
            task,
            command_run_dispatch_id=command_run_dispatch_id,
        )
        prompt_text = prompt_path.read_text(encoding="utf-8")
        assert "- summary: command succeeded with exit code 0" in prompt_text
        assert f"- log_ref: {command_run_log_ref(run_id)}" in prompt_text
        assert "RUNNER_OUTPUT_SENTINEL" not in prompt_text


async def test_command_runner_records_failed_exit_with_bounded_summary_and_log(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_command_runner_failed_exit",
            task_root_name="task-root",
        )
        await start_command_run_runner()
        command = python_command("print('RUNNER_FAILURE_' + 'SENTINEL'); raise SystemExit(7)")

        run_id = await start_runner_command_run(
            context,
            task,
            command=command,
            workdir=None,
            timeout_seconds=5,
        )
        command_run = await wait_for_command_run_state(
            context,
            task_id=task.task_id,
            run_id=run_id,
            expected_state="failed",
        )

        assert command_run.terminal_summary == "command failed with exit code 7"
        assert command_run.terminal_exit_code == 7
        assert command_run.terminal_signal is None
        assert command_run.terminal_log_ref == command_run_log_ref(run_id)
        assert "RUNNER_FAILURE_SENTINEL" in (
            task.task_root / str(command_run.terminal_log_ref)
        ).read_text(encoding="utf-8")

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs",
            headers=context.operator_headers,
        )
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["summary"] == "command failed with exit code 7"
        assert item["exit_code"] == 7
        assert item["log_ref"] == command_run_log_ref(run_id)
        assert "RUNNER_FAILURE_SENTINEL" not in item["summary"]


async def test_command_runner_caps_long_output_log_without_read_surface_bytes(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_command_runner_long_output",
            task_root_name="task-root",
        )
        await start_command_run_runner()
        command = python_command(
            "import sys; "
            f"sys.stdout.write('A' * {MAX_COMMAND_RUN_LOG_BYTES + 2048}); "
            "sys.stdout.write('LOG_CAP_' + 'SENTINEL')"
        )

        run_id = await start_runner_command_run(
            context,
            task,
            command=command,
            workdir=None,
            timeout_seconds=5,
        )
        command_run = await wait_for_command_run_state(
            context,
            task_id=task.task_id,
            run_id=run_id,
            expected_state="succeeded",
        )

        assert command_run.terminal_summary == "command succeeded with exit code 0"
        assert command_run.terminal_log_ref == command_run_log_ref(run_id)
        log_path = task.task_root / str(command_run.terminal_log_ref)
        assert log_path.stat().st_size <= MAX_COMMAND_RUN_LOG_BYTES
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        assert "additional output omitted" in log_text
        assert "LOG_CAP_SENTINEL" not in log_text

        item = (
            await context.client.get(
                f"/control/tasks/{task.task_id}/command-runs",
                headers=context.operator_headers,
            )
        ).json()["items"][0]
        assert item["summary"] == "command succeeded with exit code 0"
        assert "LOG_CAP_SENTINEL" not in str(item)


async def test_command_runner_times_out_process_and_records_log_ref(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_command_runner_timeout",
            task_root_name="task-root",
        )
        await start_command_run_runner()
        command = python_command(
            "import time; "
            "from pathlib import Path; "
            "time.sleep(5); "
            "Path('timeout-survived.txt').write_text('survived', encoding='utf-8')"
        )

        run_id = await start_runner_command_run(
            context,
            task,
            command=command,
            workdir=None,
            timeout_seconds=1,
        )
        command_run = await wait_for_command_run_state(
            context,
            task_id=task.task_id,
            run_id=run_id,
            expected_state="timed_out",
        )

        assert not (task.task_root / "workspace" / "timeout-survived.txt").exists()
        assert command_run.terminal_summary == "command timed out after 1 seconds"
        assert command_run.terminal_exit_code is None
        assert command_run.terminal_signal in {"SIGTERM", "SIGKILL"}
        assert command_run.terminal_log_ref == command_run_log_ref(run_id)
        assert (task.task_root / str(command_run.terminal_log_ref)).is_file()


async def test_command_runner_records_cancel_requested_before_process_launch(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        await stop_command_run_runner()
        task = await launch_route_task(
            context,
            task_id="task_command_runner_prelaunch_cancel",
            task_root_name="task-root",
        )
        command = python_command(
            "from pathlib import Path; "
            "Path('prelaunch-cancel-survived.txt').write_text('survived', encoding='utf-8')"
        )
        run_id = await start_runner_command_run(
            context,
            task,
            command=command,
            workdir=None,
            timeout_seconds=120,
            should_drive_runner=False,
        )

        response = await context.client.post(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}/cancel",
            headers=context.operator_headers,
        )
        assert response.status_code == 200
        assert response.json()["run"]["state"] == "cancellation_requested"

        await start_command_run_runner()
        command_run = await wait_for_command_run_state(
            context,
            task_id=task.task_id,
            run_id=run_id,
            expected_state="cancelled",
        )

        assert not (task.task_root / "workspace" / "prelaunch-cancel-survived.txt").exists()
        assert command_run.terminal_summary == "command run cancelled before local process launch"
        assert command_run.terminal_exit_code is None
        assert command_run.terminal_signal is None
        assert command_run.terminal_log_ref == command_run_log_ref(run_id)
        assert await command_run_events(context, task.task_id, "command_run_progressed") == []


async def test_command_runner_cancels_process_after_control_request_without_noisy_progress(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_command_runner_cancel",
            task_root_name="task-root",
        )
        await start_command_run_runner()
        command = python_command(
            "import time; "
            "from pathlib import Path; "
            "time.sleep(60); "
            "Path('cancel-survived.txt').write_text('survived', encoding='utf-8')"
        )
        run_id = await start_runner_command_run(
            context,
            task,
            command=command,
            workdir=None,
            timeout_seconds=120,
        )
        await wait_for_command_run_state(
            context,
            task_id=task.task_id,
            run_id=run_id,
            expected_state="running",
        )

        response = await context.client.post(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}/cancel",
            headers=context.operator_headers,
        )
        assert response.status_code == 200
        assert response.json()["run"]["state"] == "cancellation_requested"

        command_run = await wait_for_command_run_state(
            context,
            task_id=task.task_id,
            run_id=run_id,
            expected_state="cancelled",
        )
        assert not (task.task_root / "workspace" / "cancel-survived.txt").exists()
        assert command_run.terminal_summary == (
            "command run cancelled after accepted cancellation request"
        )
        assert command_run.terminal_exit_code is None
        assert command_run.terminal_signal in {"SIGTERM", "SIGKILL"}
        assert (
            await command_run_event_count(
                context.session_factory,
                task_id=task.task_id,
                event_type="command_run_cancel_requested",
            )
            == 1
        )
        progress_events = await command_run_events(context, task.task_id, "command_run_progressed")
        assert [event.payload["summary"] for event in progress_events] == [
            "command process started"
        ]


async def test_command_runner_reconcile_skips_run_that_no_longer_owns_wait(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_command_runner_stale_wait",
            task_root_name="task-root",
        )
        stale_command = python_command("print('stale command should not launch')")
        current_command = python_command("print('replacement command launched')")
        stale_run_id = await start_runner_command_run(
            context,
            task,
            command=stale_command,
            workdir=None,
            timeout_seconds=5,
            should_drive_runner=False,
        )
        current_run_id = await replace_active_command_run_wait(
            context,
            stale_run_id=stale_run_id,
            replacement_command=current_command,
        )

        await start_command_run_runner()
        await drive_command_run_runner_once()
        current_run = await wait_for_command_run_state(
            context,
            task_id=task.task_id,
            run_id=current_run_id,
            expected_state="succeeded",
        )
        stale_run = await read_command_run(context, stale_run_id)

        assert current_run.terminal_summary == "command succeeded with exit code 0"
        assert stale_run.state == "pending_start"
        assert stale_run.started_at is None
        assert not (task.task_root / command_run_log_ref(stale_run_id)).exists()
        assert "replacement command launched" in (
            task.task_root / str(current_run.terminal_log_ref)
        ).read_text(encoding="utf-8")


def python_command(script: str) -> str:
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"


async def start_runner_command_run(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    command: str,
    workdir: str | None,
    timeout_seconds: int | None,
    should_drive_runner: bool = True,
) -> str:
    await allow_command_run(context.session_factory, task_id=task.task_id)

    async def operation(session: AsyncSession) -> CommandRunStartResponse:
        state = await current_runtime_state(session, task.task_id)
        dispatch = await session.get(DispatchTurnModel, task.current_open_dispatch_id)
        assert dispatch is not None
        return await start_command_run(
            session,
            task_id=task.task_id,
            request=CommandRunStartRequest(
                command=command,
                description="Run a concrete command-runner integration command.",
                workdir=workdir,
                timeout_seconds=timeout_seconds,
            ),
            state=state,
            dispatch=dispatch,
        )

    response = await write_runtime_operation(operation)
    if should_drive_runner:
        notify_command_run_runner()
        await drive_command_run_runner_once()
    return response.run_id


async def allow_command_run(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        node = await session.scalar(
            select(FlowNodeModel).where(
                FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                FlowNodeModel.node_key == flow.current_node_key,
            )
        )
        assert node is not None
        assert node.policy_key is not None
        assert node.policy_revision_no is not None
        policy_revision = await session.scalar(
            select(PolicyRevisionModel).where(
                PolicyRevisionModel.policy_key == node.policy_key,
                PolicyRevisionModel.revision_no == node.policy_revision_no,
            )
        )
        assert policy_revision is not None
        content = dict(policy_revision.content_json)
        raw_capabilities = content.get("capabilities")
        capabilities = dict(raw_capabilities) if isinstance(raw_capabilities, dict) else {}
        capabilities.setdefault("human_request", {"mode": "deny", "allowed_kinds": []})
        capabilities["command_run"] = "allow"
        content["capabilities"] = capabilities
        policy_revision.content_json = content
        await session.commit()


async def wait_for_command_run_state(
    context: RuntimeRouteContext,
    *,
    task_id: str,
    run_id: str,
    expected_state: str,
) -> CommandRunModel:
    deadline = asyncio.get_running_loop().time() + 25.0
    while asyncio.get_running_loop().time() < deadline:
        command_run = await read_command_run(context, run_id)
        if command_run.state == expected_state:
            return command_run
        notify_command_run_runner()
        await asyncio.sleep(0.05)
    command_run = await read_command_run(context, run_id)
    if command_run.state == expected_state:
        return command_run
    raise AssertionError(
        f"command run {run_id} reached {command_run.state!r}, expected {expected_state!r}"
    )


async def read_command_run(
    context: RuntimeRouteContext,
    run_id: str,
) -> CommandRunModel:
    async with context.session_factory() as session:
        command_run = await session.get(CommandRunModel, run_id)
        assert command_run is not None
        return command_run


async def replace_active_command_run_wait(
    context: RuntimeRouteContext,
    *,
    stale_run_id: str,
    replacement_command: str,
) -> str:
    async with context.session_factory() as session:
        stale_run = await session.get(CommandRunModel, stale_run_id)
        assert stale_run is not None
        wait_state = await session.get(FlowWaitStateModel, stale_run.flow_id)
        assert wait_state is not None
        replacement_run_id = f"{stale_run_id}.replacement"
        session.add(
            CommandRunModel(
                run_id=replacement_run_id,
                task_id=stale_run.task_id,
                flow_id=stale_run.flow_id,
                flow_revision_id=stale_run.flow_revision_id,
                flow_node_id=stale_run.flow_node_id,
                assignment_id=stale_run.assignment_id,
                attempt_id=stale_run.attempt_id,
                dispatch_id=stale_run.dispatch_id,
                requester_node_key=stale_run.requester_node_key,
                command=replacement_command,
                description="Replacement command-runner integration command.",
                workdir=stale_run.workdir,
                timeout_seconds=stale_run.timeout_seconds,
                state="pending_start",
                created_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
                updated_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
            )
        )
        wait_state.command_run_id = replacement_run_id
        await session.commit()
        return replacement_run_id


async def assert_command_run_continues_task(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    command_run_dispatch_id: str,
) -> tuple[str, Path]:
    continued_dispatch_id: str | None = None
    prompt_path: Path | None = None

    async def task_continued() -> bool:
        nonlocal continued_dispatch_id, prompt_path
        async with context.session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
            assert flow is not None
            dispatch_id = flow.current_open_dispatch_id
            if dispatch_id is None or dispatch_id == command_run_dispatch_id:
                return False
            dispatch = await session.get(DispatchTurnModel, dispatch_id)
            assert dispatch is not None
            if dispatch.previous_dispatch_id != command_run_dispatch_id:
                return False
            if dispatch.accepted_boundary is not None:
                return False
            if dispatch.prompt_path is None:
                return False
            candidate_prompt_path = Path(dispatch.prompt_path)
            if not await asyncio.to_thread(candidate_prompt_path.is_file):
                return False
            continued_dispatch_id = dispatch.dispatch_id
            prompt_path = candidate_prompt_path
            return True

    await drive_runtime_until(task_continued, task_id=task.task_id, max_cycles=60)
    assert continued_dispatch_id is not None
    assert prompt_path is not None
    return continued_dispatch_id, prompt_path


async def command_run_events(
    context: RuntimeRouteContext,
    task_id: str,
    event_type: str,
) -> list[TaskEventModel]:
    async with context.session_factory() as session:
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


async def command_run_event_count(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    event_type: str,
) -> int:
    async with session_factory() as session:
        return int(
            await session.scalar(
                select(func.count(TaskEventModel.event_id)).where(
                    TaskEventModel.task_id == task_id,
                    TaskEventModel.event_type == event_type,
                )
            )
            or 0
        )
