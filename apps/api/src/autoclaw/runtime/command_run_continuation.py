from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import CommandRunModel, DispatchTurnModel, FlowModel
from autoclaw.runtime.contracts import (
    TERMINAL_COMMAND_RUN_STATES,
    CommandRunRecord,
    CommandRunState,
    CommandRunTerminalResult,
)
from autoclaw.runtime.errors import illegal_state_error
from autoclaw.runtime.flow.queries import current_semantic_flow_target
from autoclaw.runtime.flow.timestamps import coerce_datetime_to_utc

_SEMANTIC_TARGET_INCOMPLETE_SUMMARY = "current semantic target is incomplete"
_SEMANTIC_TARGET_REPAIR_NEXT_STEP = (
    "Inspect the current node assignment and attempt currentness, then repair the "
    "incomplete semantic target before continuing this task."
)


async def command_run_continuation_context_for_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    previous_dispatch_id: str | None,
) -> CommandRunRecord | None:
    if previous_dispatch_id is None:
        return None
    command_run = await terminal_command_run_for_dispatch(
        session,
        task_id=task_id,
        dispatch_id=previous_dispatch_id,
    )
    if command_run is None:
        return None
    return command_run_record_from_model(command_run)


async def command_run_terminal_continuation_matches_current_target(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    previous_dispatch: DispatchTurnModel,
) -> bool:
    command_run = await terminal_command_run_for_dispatch(
        session,
        task_id=task_id,
        dispatch_id=previous_dispatch.dispatch_id,
    )
    if command_run is None:
        return False
    if (
        command_run.flow_id != flow.flow_id
        or command_run.flow_revision_id != flow.active_flow_revision_id
    ):
        return False
    semantic_target = await current_semantic_flow_target(
        session,
        flow=flow,
        incomplete_summary=_SEMANTIC_TARGET_INCOMPLETE_SUMMARY,
        suggested_next_step=_SEMANTIC_TARGET_REPAIR_NEXT_STEP,
    )
    if semantic_target is None:
        return False
    return (
        command_run.flow_node_id == semantic_target.node.flow_node_id
        and command_run.assignment_id == semantic_target.assignment.assignment_id
        and command_run.attempt_id == semantic_target.attempt.attempt_id
    )


async def terminal_command_run_for_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> CommandRunModel | None:
    terminal_states = tuple(state.value for state in TERMINAL_COMMAND_RUN_STATES)
    return cast(
        CommandRunModel | None,
        await session.scalar(
            select(CommandRunModel)
            .where(
                CommandRunModel.task_id == task_id,
                CommandRunModel.dispatch_id == dispatch_id,
                CommandRunModel.state.in_(terminal_states),
                CommandRunModel.ended_at.is_not(None),
                CommandRunModel.terminal_summary.is_not(None),
            )
            .order_by(
                CommandRunModel.ended_at.desc(),
                CommandRunModel.updated_at.desc(),
                CommandRunModel.run_id.desc(),
            )
            .limit(1)
        ),
    )


def command_run_record_from_model(row: CommandRunModel) -> CommandRunRecord:
    return CommandRunRecord(
        run_id=row.run_id,
        task_id=row.task_id,
        dispatch_id=row.dispatch_id,
        attempt_id=row.attempt_id,
        command=row.command,
        description=row.description,
        workdir=row.workdir,
        state=CommandRunState(row.state),
        created_at=coerce_datetime_to_utc(row.created_at),
        started_at=_optional_datetime(row.started_at),
        ended_at=_optional_datetime(row.ended_at),
        timeout_seconds=row.timeout_seconds,
        latest_update=row.latest_update,
        latest_log_ref=row.latest_log_ref,
        terminal_result=terminal_result_from_model(row),
    )


def terminal_result_from_model(row: CommandRunModel) -> CommandRunTerminalResult | None:
    if CommandRunState(row.state) not in TERMINAL_COMMAND_RUN_STATES:
        return None
    if row.terminal_summary is None or row.ended_at is None:
        raise illegal_state_error(f"terminal command run '{row.run_id}' is missing result truth")
    return CommandRunTerminalResult(
        summary=row.terminal_summary,
        exit_code=row.terminal_exit_code,
        signal=row.terminal_signal,
        log_ref=row.terminal_log_ref,
    )


def _optional_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return coerce_datetime_to_utc(value)


__all__ = [
    "command_run_continuation_context_for_dispatch",
    "command_run_record_from_model",
    "command_run_terminal_continuation_matches_current_target",
    "terminal_command_run_for_dispatch",
    "terminal_result_from_model",
]
