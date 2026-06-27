from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from autoclaw.persistence import (
    CommandRunModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    FlowWaitStateModel,
    PolicyRevisionModel,
    TaskEventModel,
)
from autoclaw.runtime.command_run.service import (
    record_command_run_progress,
    record_command_run_terminal_result,
    start_command_run,
)
from autoclaw.runtime.contracts import (
    CommandRunProgressUpdate,
    CommandRunRecord,
    CommandRunStartRequest,
    CommandRunState,
    CommandRunTerminalResultRead,
)
from autoclaw.runtime.contracts.command_runs import CommandRunTerminalState
from autoclaw.runtime.post_commit import drive_runtime_until, write_runtime_operation
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.operator_auth_headers import DEFAULT_OPERATOR_ACTOR_REF
from tests.integration.runtime.routes.support import RuntimeRouteContext, SeededRouteTask


def command_run_start_payload() -> dict[str, object]:
    return {
        "command": "pytest apps/api/tests/unit/runtime -q",
        "description": "Run focused runtime unit tests.",
        "workdir": "apps/api",
        "timeout_seconds": 900,
    }


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
            request=CommandRunStartRequest.model_validate(command_run_start_payload()),
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
    state: CommandRunTerminalState,
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
                summary=f"{state.value} command finished",
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
        assert command_run.cancellation_requested_by_actor_ref == DEFAULT_OPERATOR_ACTOR_REF
        assert command_run.latest_update == "command run cancellation requested"
        assert len(events) == 1
        event = events[0]
        assert event.event_source == "control_api"
        assert event.actor_ref == DEFAULT_OPERATOR_ACTOR_REF
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
    terminal_state: CommandRunTerminalState,
    exit_code: int | None,
    signal: str | None,
) -> None:
    async with context.session_factory() as session:
        terminal_state_value = terminal_state.value
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task.task_id))
        command_run = await session.get(CommandRunModel, run_id)
        wait_state = None if flow is None else await session.get(FlowWaitStateModel, flow.flow_id)
        progress_events = await command_run_events(session, task.task_id, "command_run_progressed")
        terminal_events = await command_run_events(
            session,
            task.task_id,
            f"command_run_{terminal_state_value}",
        )

        assert flow is not None
        assert command_run is not None
        assert wait_state is None
        assert command_run.state == terminal_state_value
        assert command_run.terminal_summary == f"{terminal_state_value} command finished"
        assert command_run.terminal_exit_code == exit_code
        assert command_run.terminal_signal == signal
        assert command_run.terminal_log_ref == f"logs/{terminal_state_value}.terminal.txt"
        assert command_run.terminal_event_source == "controller"
        assert command_run.terminal_actor_ref is None
        assert len(progress_events) == 1
        assert progress_events[0].payload == {
            "run_id": run_id,
            "summary": f"{terminal_state_value} command reached test execution",
            "log_ref": f"logs/{terminal_state_value}.progress.txt",
            "occurred_at": "2026-06-25T12:00:00+00:00",
            "state": "running",
        }
        assert len(terminal_events) == 1
        terminal_event = terminal_events[0]
        assert terminal_event.event_source == "controller"
        assert terminal_event.actor_ref is None
        assert terminal_event.payload == {
            "run_id": run_id,
            "state": terminal_state_value,
            "summary": f"{terminal_state_value} command finished",
            "exit_code": exit_code,
            "signal": signal,
            "ended_at": "2026-06-25T12:05:00+00:00",
            "log_ref": f"logs/{terminal_state_value}.terminal.txt",
        }


async def assert_terminal_command_run_case(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
    *,
    run_id: str,
    command_run_dispatch_id: str,
    terminal_state: CommandRunTerminalState,
    exit_code: int | None,
    signal: str | None,
) -> None:
    terminal_state_value = terminal_state.value
    progress_summary = f"{terminal_state_value} command reached test execution"
    terminal_summary = f"{terminal_state_value} command finished"
    progress_log_ref = f"logs/{terminal_state_value}.progress.txt"
    terminal_log_ref = f"logs/{terminal_state_value}.terminal.txt"
    progress_record = await record_progress(
        context,
        task,
        run_id=run_id,
        summary=progress_summary,
        log_ref=progress_log_ref,
    )
    terminal_record = await finish_command_run(
        context,
        task,
        run_id=run_id,
        state=terminal_state,
        exit_code=exit_code,
        signal=signal,
        log_ref=terminal_log_ref,
    )

    assert progress_record.run_id == run_id
    assert progress_record.state == "running"
    assert progress_record.latest_update == progress_summary
    assert_terminal_command_run_record(
        terminal_record=terminal_record,
        run_id=run_id,
        terminal_state=terminal_state,
        exit_code=exit_code,
        signal=signal,
        terminal_summary=terminal_summary,
        terminal_log_ref=terminal_log_ref,
    )
    await assert_terminal_command_run_readback(
        context,
        task_id=task.task_id,
        terminal_state_value=terminal_state_value,
        exit_code=exit_code,
        signal=signal,
        terminal_summary=terminal_summary,
        terminal_log_ref=terminal_log_ref,
    )
    await assert_command_run_terminal_state(
        context,
        task,
        run_id=run_id,
        terminal_state=terminal_state,
        exit_code=exit_code,
        signal=signal,
    )
    await assert_terminal_command_run_prompt_context(
        context,
        task=task,
        run_id=run_id,
        command_run_dispatch_id=command_run_dispatch_id,
        terminal_state_value=terminal_state_value,
        terminal_summary=terminal_summary,
        progress_log_ref=progress_log_ref,
        terminal_log_ref=terminal_log_ref,
    )


def assert_terminal_command_run_record(
    *,
    terminal_record: CommandRunRecord,
    run_id: str,
    terminal_state: CommandRunTerminalState,
    exit_code: int | None,
    signal: str | None,
    terminal_summary: str,
    terminal_log_ref: str,
) -> None:
    assert terminal_record.run_id == run_id
    assert (
        terminal_record.command,
        terminal_record.description,
        terminal_record.workdir,
        terminal_record.timeout_seconds,
    ) == (
        command_run_start_payload()["command"],
        command_run_start_payload()["description"],
        "apps/api",
        900,
    )
    assert terminal_record.state == terminal_state
    if terminal_state == CommandRunState.CANCELLED:
        assert terminal_record.cancellation_requested_at is not None
        assert terminal_record.cancellation_requested_by_actor_ref is None
    else:
        assert terminal_record.cancellation_requested_at is None
        assert terminal_record.cancellation_requested_by_actor_ref is None
    assert terminal_record.terminal_result is not None
    assert (
        terminal_record.terminal_result.summary,
        terminal_record.terminal_result.exit_code,
        terminal_record.terminal_result.signal,
        terminal_record.terminal_result.log_ref,
        terminal_record.terminal_event_source,
        terminal_record.terminal_actor_ref,
    ) == (
        terminal_summary,
        exit_code,
        signal,
        terminal_log_ref,
        "controller",
        None,
    )


async def assert_terminal_command_run_readback(
    context: RuntimeRouteContext,
    *,
    task_id: str,
    terminal_state_value: str,
    exit_code: int | None,
    signal: str | None,
    terminal_summary: str,
    terminal_log_ref: str,
) -> None:
    terminal_readback = await context.client.get(
        f"/control/tasks/{task_id}/command-runs",
        headers=context.operator_headers,
    )
    assert terminal_readback.status_code == 200
    readback_item = terminal_readback.json()["items"][0]
    assert (
        readback_item["state"],
        readback_item["summary"],
        readback_item["exit_code"],
        readback_item["signal"],
        readback_item["log_ref"],
    ) == (
        terminal_state_value,
        terminal_summary,
        exit_code,
        signal,
        terminal_log_ref,
    )


async def assert_terminal_command_run_prompt_context(
    context: RuntimeRouteContext,
    *,
    task: SeededRouteTask,
    run_id: str,
    command_run_dispatch_id: str,
    terminal_state_value: str,
    terminal_summary: str,
    progress_log_ref: str,
    terminal_log_ref: str,
) -> None:
    continued_dispatch_id, prompt_path = await assert_command_run_terminal_continues_task(
        context,
        task,
        command_run_dispatch_id=command_run_dispatch_id,
    )
    assert continued_dispatch_id != command_run_dispatch_id
    prompt_text = prompt_path.read_text(encoding="utf-8")
    assert "## Command Run Continuation Context" in prompt_text
    assert f"- run_id: {run_id}" in prompt_text
    assert f"- state: {terminal_state_value}" in prompt_text
    assert f"- summary: {terminal_summary}" in prompt_text
    assert f"- log_ref: {terminal_log_ref}" in prompt_text
    assert progress_log_ref not in prompt_text


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
