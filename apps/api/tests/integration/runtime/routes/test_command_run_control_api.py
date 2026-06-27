from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.persistence import FlowModel, FlowWaitStateModel
from autoclaw.runtime.contracts import (
    CommandRunState,
    OperationFailureCode,
)
from autoclaw.runtime.contracts.command_runs import CommandRunTerminalState
from autoclaw.runtime.errors import RuntimeOperationError
from sqlalchemy import select
from tests.helpers.operator_auth_headers import current_operator_headers
from tests.integration.runtime.routes.run_control_api_support import (
    assert_command_run_cancel_requested,
    assert_command_run_started_without_boundary,
    assert_command_run_unchanged,
    assert_terminal_command_run_case,
    command_run_event_count,
    command_run_start_payload,
    finish_command_run,
    record_progress,
    replace_active_command_run_wait,
    start_route_command_run,
)
from tests.integration.runtime.routes.support import (
    control_write_headers,
    launch_route_task,
    runtime_route_context,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]


async def test_control_command_runs_read_exposes_started_run(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_read",
            task_root_name="task-root",
        )
        run_id = await start_route_command_run(context, task)

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs",
            headers=context.operator_headers,
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["task_id"] == task.task_id
        assert payload["next_cursor"] is None
        assert len(payload["items"]) == 1
        item = payload["items"][0]
        assert item["run_id"] == run_id
        assert item["state"] == "pending_start"
        assert item["command"] == command_run_start_payload()["command"]
        assert item["description"] == command_run_start_payload()["description"]
        assert item["workdir"] == "apps/api"
        assert item["timeout_seconds"] == 900
        assert item["summary"] is None
        assert item["exit_code"] is None
        assert item["signal"] is None
        assert item["log_ref"] is None

        detail = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}",
            headers=context.operator_headers,
        )
        assert detail.status_code == 200
        detail_json = detail.json()
        assert detail_json["run_id"] == run_id
        assert detail_json["state"] == "pending_start"
        assert detail_json["latest_update"] is None
        assert detail_json["terminal_result"] is None

        log = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}/log",
            headers=context.operator_headers,
        )
        assert log.status_code == 404
        assert log.json()["detail"]["code"] == "missing_resource"


async def test_control_command_run_cancel_persists_request_and_keeps_wait_open(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_cancel",
            task_root_name="task-root",
        )
        run_id = await start_route_command_run(context, task)

        response = await context.client.post(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}/cancel",
            headers=control_write_headers(context, task),
        )

        assert response.status_code == 200
        run = response.json()["run"]
        assert response.json()["task_id"] == task.task_id
        assert run["run_id"] == run_id
        assert run["state"] == "cancellation_requested"
        assert run["summary"] == "command run cancellation requested"
        await assert_command_run_cancel_requested(context, task, run_id)

        readback = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs",
            headers=context.operator_headers,
        )
        assert readback.status_code == 200
        assert readback.json()["items"][0] == run


async def test_control_command_run_cancel_rejects_missing_and_noncurrent_runs(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_noncurrent",
            task_root_name="task-root",
        )
        run_id = await start_route_command_run(context, task)
        replacement_run_id = await replace_active_command_run_wait(context, run_id)

        missing = await context.client.post(
            f"/control/tasks/{task.task_id}/command-runs/command-run.missing/cancel",
            headers=control_write_headers(context, task),
        )
        noncurrent = await context.client.post(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}/cancel",
            headers=control_write_headers(context, task),
        )

        assert missing.status_code == 409
        assert missing.json()["detail"]["code"] == "illegal_state"
        assert noncurrent.status_code == 409
        assert noncurrent.json()["detail"]["code"] == "illegal_state"
        await assert_command_run_unchanged(
            context,
            task,
            run_id,
            wait_owner_id=replacement_run_id,
        )


async def test_pause_then_continue_rejects_active_command_run_wait(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_pause_wait",
            task_root_name="task-root",
        )
        run_id = await start_route_command_run(context, task)

        pause_response = await context.client.post(
            f"/control/tasks/{task.task_id}/pause",
            headers=control_write_headers(context, task),
            params={"expected_active_flow_revision_id": task.active_flow_revision_id},
        )

        assert pause_response.status_code == 200
        assert pause_response.json()["flow"]["status"] == "paused"

        continue_response = await context.client.post(
            f"/control/tasks/{task.task_id}/continue",
            headers=control_write_headers(context, task),
            params={"expected_active_flow_revision_id": task.active_flow_revision_id},
        )

        assert continue_response.status_code == 422
        assert continue_response.json()["detail"]["code"] == "illegal_state"
        assert "command run wait is still active" in continue_response.json()["detail"]["summary"]

        async with context.session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
            assert flow is not None
            wait_state = await session.get(FlowWaitStateModel, flow.flow_id)
            assert wait_state is not None
            assert flow.status == "paused"
            assert wait_state.waiting_cause == "waiting_for_command_run"
            assert wait_state.command_run_id == run_id


async def test_control_command_run_cancel_rejects_terminal_and_duplicate_requests(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        terminal_task = await launch_route_task(
            context,
            task_id="task_control_command_run_terminal_cancel",
            task_root_name="terminal-task-root",
        )
        terminal_run_id = await start_route_command_run(context, terminal_task)
        await finish_command_run(
            context,
            terminal_task,
            run_id=terminal_run_id,
            state=CommandRunState.FAILED,
        )

        terminal_cancel = await context.client.post(
            f"/control/tasks/{terminal_task.task_id}/command-runs/{terminal_run_id}/cancel",
            headers=control_write_headers(context, terminal_task),
        )
        assert terminal_cancel.status_code == 409
        assert terminal_cancel.json()["detail"]["code"] == "illegal_state"

        duplicate_task = await launch_route_task(
            context,
            task_id="task_control_command_run_duplicate_cancel",
            task_root_name="duplicate-task-root",
        )
        duplicate_run_id = await start_route_command_run(context, duplicate_task)
        first = await context.client.post(
            f"/control/tasks/{duplicate_task.task_id}/command-runs/{duplicate_run_id}/cancel",
            headers=control_write_headers(context, duplicate_task),
        )
        second = await context.client.post(
            f"/control/tasks/{duplicate_task.task_id}/command-runs/{duplicate_run_id}/cancel",
            headers=control_write_headers(context, duplicate_task),
        )

        assert first.status_code == 200
        assert second.status_code == 409
        assert second.json()["detail"]["code"] == "illegal_state"
        assert (
            await command_run_event_count(
                context.session_factory,
                task_id=duplicate_task.task_id,
                event_type="command_run_cancel_requested",
            )
            == 1
        )


async def test_control_command_run_log_preserves_exact_text(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_log_exact_text",
            task_root_name="log-exact-task-root",
        )
        run_id = await start_route_command_run(context, task)
        log_ref = "outputs/command-runs/exact.log"
        exact_text = "  leading whitespace\ntrailing whitespace  \n"
        log_path = task.task_root / log_ref
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(exact_text, encoding="utf-8")

        await record_progress(
            context,
            task,
            run_id=run_id,
            summary="command log became available",
            log_ref=log_ref,
        )

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}/log",
            headers=context.operator_headers,
        )

        assert response.status_code == 200
        assert response.json()["content"] == exact_text


async def test_control_command_run_log_allows_empty_file(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_log_empty",
            task_root_name="log-empty-task-root",
        )
        run_id = await start_route_command_run(context, task)
        log_ref = "outputs/command-runs/empty.log"
        log_path = task.task_root / log_ref
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")

        await record_progress(
            context,
            task,
            run_id=run_id,
            summary="empty command log became available",
            log_ref=log_ref,
        )

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}/log",
            headers=context.operator_headers,
        )

        assert response.status_code == 200
        assert response.json()["content"] == ""


async def test_control_command_run_log_read_returns_full_persisted_content(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_log_oversized",
            task_root_name="log-oversized-task-root",
        )
        run_id = await start_route_command_run(context, task)
        log_ref = "outputs/command-runs/oversized.log"
        log_path = task.task_root / log_ref
        log_path.parent.mkdir(parents=True, exist_ok=True)
        oversized_content = b"A" * (1024 * 1024 + 1024) + b"LOG_READ_SENTINEL"
        log_path.write_bytes(oversized_content)

        await record_progress(
            context,
            task,
            run_id=run_id,
            summary="oversized command log became available",
            log_ref=log_ref,
        )

        response = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}/log",
            headers=context.operator_headers,
        )

        assert response.status_code == 200
        content = response.json()["content"]
        assert content.encode("utf-8") == oversized_content
        assert content.startswith("A" * 64)
        assert content.endswith("LOG_READ_SENTINEL")


@pytest.mark.parametrize(
    ("terminal_state", "exit_code", "signal"),
    (
        (CommandRunState.FAILED, 1, None),
        (CommandRunState.TIMED_OUT, None, "SIGTERM"),
        (CommandRunState.CANCELLED, None, "SIGINT"),
    ),
)
async def test_command_run_progress_and_terminal_outcomes_persist_continuation_truth(
    tmp_path: Path,
    terminal_state: CommandRunTerminalState,
    exit_code: int | None,
    signal: str | None,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        terminal_state_value = terminal_state.value
        task = await launch_route_task(
            context,
            task_id=f"task_control_command_run_{terminal_state_value}",
            task_root_name=f"{terminal_state_value}-task-root",
        )
        command_run_dispatch_id = task.current_open_dispatch_id
        run_id = await start_route_command_run(context, task)
        await assert_command_run_started_without_boundary(
            context,
            dispatch_id=command_run_dispatch_id,
        )
        await assert_terminal_command_run_case(
            context,
            task,
            run_id=run_id,
            command_run_dispatch_id=command_run_dispatch_id,
            terminal_state=terminal_state,
            exit_code=exit_code,
            signal=signal,
        )


async def test_command_run_terminal_rejects_noncurrent_run_without_continuing_task(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_stale_terminal",
            task_root_name="stale-terminal-task-root",
        )
        run_id = await start_route_command_run(context, task)
        replacement_run_id = await replace_active_command_run_wait(context, run_id)

        with pytest.raises(RuntimeOperationError) as exc_info:
            await finish_command_run(
                context,
                task,
                run_id=run_id,
                state=CommandRunState.FAILED,
                exit_code=1,
                log_ref="logs/stale-terminal.txt",
            )

        assert exc_info.value.code == OperationFailureCode.ILLEGAL_STATE
        await assert_command_run_unchanged(
            context,
            task,
            run_id,
            wait_owner_id=replacement_run_id,
        )
        async with context.session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
            assert flow is not None
            assert flow.current_open_dispatch_id is None


async def test_control_command_runs_require_operator_auth_and_existing_task(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_auth",
            task_root_name="task-root",
        )

        unauthorized = await context.client.get(f"/control/tasks/{task.task_id}/command-runs")
        unauthorized_detail = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs/command-run.missing",
        )
        unauthorized_log = await context.client.get(
            f"/control/tasks/{task.task_id}/command-runs/command-run.missing/log",
        )
        missing_read = await context.client.get(
            "/control/tasks/task_missing/command-runs",
            headers=context.operator_headers,
        )
        missing_detail = await context.client.get(
            "/control/tasks/task_missing/command-runs/command-run.missing",
            headers=context.operator_headers,
        )
        missing_log = await context.client.get(
            "/control/tasks/task_missing/command-runs/command-run.missing/log",
            headers=context.operator_headers,
        )
        missing_cancel = await context.client.post(
            "/control/tasks/task_missing/command-runs/command-run.missing/cancel",
            headers=current_operator_headers(),
        )

        assert unauthorized.status_code == 401
        assert unauthorized.json()["detail"]["code"] == "illegal_caller"
        assert unauthorized_detail.status_code == 401
        assert unauthorized_detail.json()["detail"]["code"] == "illegal_caller"
        assert unauthorized_log.status_code == 401
        assert unauthorized_log.json()["detail"]["code"] == "illegal_caller"
        assert missing_read.status_code == 404
        assert missing_read.json()["detail"]["code"] == "missing_resource"
        assert missing_detail.status_code == 404
        assert missing_detail.json()["detail"]["code"] == "missing_resource"
        assert missing_log.status_code == 404
        assert missing_log.json()["detail"]["code"] == "missing_resource"
        assert missing_cancel.status_code == 404
        assert missing_cancel.json()["detail"]["code"] == "missing_resource"
