from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.runtime.command_run_runner import (
    MAX_COMMAND_RUN_LOG_BYTES,
    command_run_log_ref,
    drive_command_run_runner_once,
    start_command_run_runner,
    stop_command_run_runner,
    wait_for_command_run_runner_idle,
)
from tests.integration.runtime.command_run_runner.support import (
    assert_command_run_continues_task,
    command_run_event_count,
    command_run_events,
    python_command,
    read_command_run,
    replace_active_command_run_wait,
    start_runner_command_run,
    wait_for_command_run_state,
)
from tests.integration.runtime.routes.support import (
    control_write_headers,
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
            headers=control_write_headers(context, task),
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
            headers=control_write_headers(context, task),
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


async def test_command_runner_stops_live_process_after_whole_task_cancel(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_command_runner_task_cancel",
            task_root_name="task-root",
        )
        await start_command_run_runner()
        command = python_command(
            "import signal\n"
            "import time\n"
            "from pathlib import Path\n"
            "def handle(signum, _frame):\n"
            "    Path('task-cancel-signal.txt').write_text("
            "signal.Signals(signum).name, encoding='utf-8')\n"
            "    raise SystemExit(0)\n"
            "signal.signal(signal.SIGTERM, handle)\n"
            "signal.signal(signal.SIGINT, handle)\n"
            "print('RUNNER_TASK_CANCEL_READY', flush=True)\n"
            "while True:\n"
            "    time.sleep(0.1)\n"
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
            f"/runtime/tasks/{task.task_id}/cancel",
            headers=control_write_headers(context, task),
            params={"expected_active_flow_revision_id": task.active_flow_revision_id},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

        await wait_for_command_run_runner_idle()
        command_run = await read_command_run(context, run_id)
        signal_path = task.task_root / "workspace" / "task-cancel-signal.txt"

        assert command_run.state == "cancelled"
        assert (
            command_run.terminal_summary == "command run cancelled because the task was cancelled"
        )
        assert signal_path.read_text(encoding="utf-8") == "SIGTERM"
        assert (
            await command_run_event_count(
                context.session_factory,
                task_id=task.task_id,
                event_type="command_run_cancelled",
            )
            == 1
        )


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
