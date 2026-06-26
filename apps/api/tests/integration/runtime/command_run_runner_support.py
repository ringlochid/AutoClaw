from __future__ import annotations

import asyncio
import shlex
import sys
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
from autoclaw.runtime.command_run_runner import (
    drive_command_run_runner_once,
    notify_command_run_runner,
)
from autoclaw.runtime.command_runs import start_command_run
from autoclaw.runtime.contracts import CommandRunStartRequest, CommandRunStartResponse
from autoclaw.runtime.post_commit import drive_runtime_until, write_runtime_operation
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.runtime.routes.support import RuntimeRouteContext, SeededRouteTask


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
