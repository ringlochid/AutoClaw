from __future__ import annotations

import asyncio
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
from autoclaw.runtime.command_runs import (
    record_command_run_progress,
    record_command_run_terminal_result,
    start_command_run,
)
from autoclaw.runtime.contracts import (
    CommandRunProgressUpdate,
    CommandRunRecord,
    CommandRunStartRequest,
    CommandRunTerminalResultRead,
    OperationFailureCode,
)
from autoclaw.runtime.errors import RuntimeOperationError
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


def _command_run_start_payload() -> dict[str, object]:
    return {
        "command": "pytest apps/api/tests/unit/runtime -q",
        "description": "Run focused runtime unit tests.",
        "workdir": "apps/api",
        "timeout_seconds": 900,
    }


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
        assert item["command"] == _command_run_start_payload()["command"]
        assert item["description"] == _command_run_start_payload()["description"]
        assert item["workdir"] == "apps/api"
        assert item["timeout_seconds"] == 900
        assert item["summary"] is None
        assert item["exit_code"] is None
        assert item["signal"] is None
        assert item["log_ref"] is None


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
            headers=context.operator_headers,
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
            headers=context.operator_headers,
        )
        noncurrent = await context.client.post(
            f"/control/tasks/{task.task_id}/command-runs/{run_id}/cancel",
            headers=context.operator_headers,
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
            state="failed",
        )

        terminal_cancel = await context.client.post(
            f"/control/tasks/{terminal_task.task_id}/command-runs/{terminal_run_id}/cancel",
            headers=context.operator_headers,
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
            headers=context.operator_headers,
        )
        second = await context.client.post(
            f"/control/tasks/{duplicate_task.task_id}/command-runs/{duplicate_run_id}/cancel",
            headers=context.operator_headers,
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


async def test_command_run_progress_and_terminal_outcomes_persist_continuation_truth(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        for terminal_state, exit_code, signal in (
            ("failed", 1, None),
            ("timed_out", None, "SIGTERM"),
            ("cancelled", None, "SIGINT"),
        ):
            task = await launch_route_task(
                context,
                task_id=f"task_control_command_run_{terminal_state}",
                task_root_name=f"{terminal_state}-task-root",
            )
            command_run_dispatch_id = task.current_open_dispatch_id
            run_id = await start_route_command_run(context, task)
            await assert_command_run_started_without_boundary(
                context,
                dispatch_id=command_run_dispatch_id,
            )
            progress_record = await record_progress(
                context,
                task,
                run_id=run_id,
                summary=f"{terminal_state} command reached test execution",
                log_ref=f"logs/{terminal_state}.progress.txt",
            )
            terminal_record = await finish_command_run(
                context,
                task,
                run_id=run_id,
                state=terminal_state,
                exit_code=exit_code,
                signal=signal,
                log_ref=f"logs/{terminal_state}.terminal.txt",
            )

            assert progress_record.run_id == run_id
            assert progress_record.state == "running"
            assert progress_record.latest_update == (
                f"{terminal_state} command reached test execution"
            )
            assert terminal_record.run_id == run_id
            assert terminal_record.command == _command_run_start_payload()["command"]
            assert terminal_record.description == _command_run_start_payload()["description"]
            assert terminal_record.workdir == "apps/api"
            assert terminal_record.timeout_seconds == 900
            assert terminal_record.state == terminal_state
            assert terminal_record.terminal_result is not None
            assert terminal_record.terminal_result.summary == (f"{terminal_state} command finished")
            assert terminal_record.terminal_result.exit_code == exit_code
            assert terminal_record.terminal_result.signal == signal
            assert terminal_record.terminal_result.log_ref == (
                f"logs/{terminal_state}.terminal.txt"
            )
            await assert_command_run_terminal_state(
                context,
                task,
                run_id=run_id,
                terminal_state=terminal_state,
                exit_code=exit_code,
                signal=signal,
            )
            continued_dispatch_id, continued_prompt_path = (
                await assert_command_run_terminal_continues_task(
                    context,
                    task,
                    command_run_dispatch_id=command_run_dispatch_id,
                )
            )
            assert continued_dispatch_id != command_run_dispatch_id
            prompt_text = continued_prompt_path.read_text(encoding="utf-8")
            assert "## Command Run Continuation Context" in prompt_text
            assert f"- run_id: {run_id}" in prompt_text
            assert f"- state: {terminal_state}" in prompt_text
            assert f"- summary: {terminal_state} command finished" in prompt_text
            assert f"- log_ref: logs/{terminal_state}.terminal.txt" in prompt_text
            assert f"logs/{terminal_state}.progress.txt" not in prompt_text


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
                state="failed",
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
        missing_read = await context.client.get(
            "/control/tasks/task_missing/command-runs",
            headers=context.operator_headers,
        )
        missing_cancel = await context.client.post(
            "/control/tasks/task_missing/command-runs/command-run.missing/cancel",
            headers=context.operator_headers,
        )

        assert unauthorized.status_code == 401
        assert unauthorized.json()["detail"]["code"] == "illegal_caller"
        assert missing_read.status_code == 404
        assert missing_read.json()["detail"]["code"] == "missing_resource"
        assert missing_cancel.status_code == 404
        assert missing_cancel.json()["detail"]["code"] == "missing_resource"


async def start_route_command_run(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
) -> str:
    await allow_command_run(context.session_factory, task_id=task.task_id)
    async with context.session_factory() as session:
        state = await current_runtime_state(session, task.task_id)
        dispatch = await session.get(DispatchTurnModel, task.current_open_dispatch_id)
        assert dispatch is not None
        response = await start_command_run(
            session,
            task_id=task.task_id,
            request=CommandRunStartRequest.model_validate(_command_run_start_payload()),
            state=state,
            dispatch=dispatch,
        )
        await session.commit()
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


async def record_progress(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    run_id: str,
    summary: str,
    log_ref: str,
) -> CommandRunRecord:
    async with context.session_factory() as session:
        record = await record_command_run_progress(
            session,
            task_id=task.task_id,
            update=CommandRunProgressUpdate(
                run_id=run_id,
                summary=summary,
                log_ref=log_ref,
                occurred_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
            ),
        )
        await session.commit()
        return record


async def finish_command_run(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    run_id: str,
    state: str,
    exit_code: int | None = None,
    signal: str | None = None,
    log_ref: str | None = None,
) -> CommandRunRecord:
    return await write_runtime_operation(
        lambda active_session: record_command_run_terminal_result(
            active_session,
            task_id=task.task_id,
            result=CommandRunTerminalResultRead(
                run_id=run_id,
                state=state,
                summary=f"{state} command finished",
                exit_code=exit_code,
                signal=signal,
                log_ref=log_ref,
                ended_at=datetime(2026, 6, 25, 12, 5, tzinfo=UTC),
            ),
        )
    )


async def replace_active_command_run_wait(
    context: RuntimeRouteContext,
    run_id: str,
) -> str:
    async with context.session_factory() as session:
        command_run = await session.get(CommandRunModel, run_id)
        assert command_run is not None
        wait_state = await session.get(FlowWaitStateModel, command_run.flow_id)
        assert wait_state is not None
        replacement_run_id = f"{run_id}.replacement"
        session.add(
            CommandRunModel(
                run_id=replacement_run_id,
                task_id=command_run.task_id,
                flow_id=command_run.flow_id,
                flow_revision_id=command_run.flow_revision_id,
                flow_node_id=command_run.flow_node_id,
                assignment_id=command_run.assignment_id,
                attempt_id=command_run.attempt_id,
                dispatch_id=command_run.dispatch_id,
                requester_node_key=command_run.requester_node_key,
                command=command_run.command,
                description="Replacement command run",
                workdir=command_run.workdir,
                timeout_seconds=command_run.timeout_seconds,
                state="pending_start",
                created_at=command_run.created_at,
                updated_at=command_run.updated_at,
            )
        )
        wait_state.command_run_id = replacement_run_id
        await session.commit()
        return replacement_run_id


async def assert_command_run_cancel_requested(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    run_id: str,
) -> None:
    async with context.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
        command_run = await session.get(CommandRunModel, run_id)
        wait_state = None if flow is None else await session.get(FlowWaitStateModel, flow.flow_id)
        events = await command_run_events(session, task.task_id, "command_run_cancel_requested")

        assert flow is not None
        assert command_run is not None
        assert wait_state is not None
        assert wait_state.waiting_cause == "waiting_for_command_run"
        assert wait_state.command_run_id == run_id
        assert command_run.state == "cancellation_requested"
        assert command_run.cancellation_requested_at is not None
        assert command_run.cancellation_requested_by_actor_ref == "control_api"
        assert command_run.latest_update == "command run cancellation requested"
        assert len(events) == 1
        event = events[0]
        assert event.event_source == "control_api"
        assert event.actor_ref == "control_api"
        assert event.flow_revision_id == command_run.flow_revision_id
        assert event.dispatch_id == command_run.dispatch_id
        assert event.attempt_id == command_run.attempt_id
        assert event.node_key == command_run.requester_node_key
        assert event.payload["run_id"] == run_id
        assert event.payload["state"] == "cancellation_requested"
        assert event.payload["summary"] == "command run cancellation requested"


async def assert_command_run_started_without_boundary(
    context: RuntimeRouteContext,
    *,
    dispatch_id: str,
) -> None:
    async with context.session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        assert dispatch.control_state == "fenced"
        assert dispatch.accepted_boundary is None


async def assert_command_run_terminal_continues_task(
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
            if not dispatch.prompt_path:
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


async def assert_command_run_unchanged(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    run_id: str,
    *,
    wait_owner_id: str,
) -> None:
    async with context.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
        command_run = await session.get(CommandRunModel, run_id)
        wait_state = None if flow is None else await session.get(FlowWaitStateModel, flow.flow_id)

        assert flow is not None
        assert command_run is not None
        assert wait_state is not None
        assert command_run.state == "pending_start"
        assert command_run.cancellation_requested_at is None
        assert command_run.cancellation_requested_by_actor_ref is None
        assert wait_state.waiting_cause == "waiting_for_command_run"
        assert wait_state.command_run_id == wait_owner_id
        assert (
            await command_run_event_count(
                context.session_factory,
                task_id=task.task_id,
                event_type="command_run_cancel_requested",
            )
            == 0
        )


async def assert_command_run_terminal_state(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    run_id: str,
    terminal_state: str,
    exit_code: int | None,
    signal: str | None,
) -> None:
    async with context.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
        command_run = await session.get(CommandRunModel, run_id)
        wait_state = None if flow is None else await session.get(FlowWaitStateModel, flow.flow_id)
        progress_events = await command_run_events(session, task.task_id, "command_run_progressed")
        terminal_events = await command_run_events(
            session,
            task.task_id,
            f"command_run_{terminal_state}",
        )

        assert flow is not None
        assert command_run is not None
        assert wait_state is None
        assert command_run.state == terminal_state
        assert command_run.terminal_summary == f"{terminal_state} command finished"
        assert command_run.terminal_exit_code == exit_code
        assert command_run.terminal_signal == signal
        assert command_run.terminal_log_ref == f"logs/{terminal_state}.terminal.txt"
        assert len(progress_events) == 1
        assert progress_events[0].payload == {
            "run_id": run_id,
            "summary": f"{terminal_state} command reached test execution",
            "log_ref": f"logs/{terminal_state}.progress.txt",
            "occurred_at": "2026-06-25T12:00:00+00:00",
            "state": "running",
        }
        assert len(terminal_events) == 1
        terminal_event = terminal_events[0]
        assert terminal_event.event_source == "controller"
        assert terminal_event.payload == {
            "run_id": run_id,
            "state": terminal_state,
            "summary": f"{terminal_state} command finished",
            "exit_code": exit_code,
            "signal": signal,
            "ended_at": "2026-06-25T12:05:00+00:00",
            "log_ref": f"logs/{terminal_state}.terminal.txt",
        }


async def command_run_events(
    session: AsyncSession,
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
