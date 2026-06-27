from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import CommandRunModel, FlowModel
from autoclaw.runtime.command_run.records import (
    command_run_list_item_from_model,
    command_run_record_from_model,
)
from autoclaw.runtime.contracts import (
    CommandRunListResponse,
    CommandRunLogReadResponse,
    CommandRunRecord,
    OperationFailureCode,
)
from autoclaw.runtime.errors import RuntimeOperationError, missing_resource_error
from autoclaw.runtime.task_root.reads import read_task_root_paths

COMMAND_RUN_CONFLICT_NEXT_STEP = (
    "Reread the current command-run list for this task before retrying the command-run action."
)


async def list_command_runs(
    session: AsyncSession,
    *,
    task_id: str,
    cursor: str | None = None,
    limit: int = 100,
) -> CommandRunListResponse:
    await _require_flow_for_task(session, task_id)
    page_limit = max(1, min(limit, 250))
    statement = (
        select(CommandRunModel)
        .where(CommandRunModel.task_id == task_id)
        .order_by(CommandRunModel.created_at.asc(), CommandRunModel.run_id.asc())
        .limit(page_limit + 1)
    )
    if cursor is not None:
        cursor_row = await load_command_run_for_task(session, task_id=task_id, run_id=cursor)
        if cursor_row is None:
            raise command_run_conflict(f"command run cursor '{cursor}' is not current")
        statement = statement.where(
            or_(
                CommandRunModel.created_at > cursor_row.created_at,
                and_(
                    CommandRunModel.created_at == cursor_row.created_at,
                    CommandRunModel.run_id > cursor_row.run_id,
                ),
            )
        )

    rows = list(await session.scalars(statement))
    page_rows = rows[:page_limit]
    next_cursor = page_rows[-1].run_id if len(rows) > page_limit else None
    return CommandRunListResponse(
        task_id=task_id,
        items=tuple(command_run_list_item_from_model(row) for row in page_rows),
        next_cursor=next_cursor,
    )


async def read_command_run(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
) -> CommandRunRecord:
    await _require_flow_for_task(session, task_id)
    command_run = await load_command_run_for_task(session, task_id=task_id, run_id=run_id)
    if command_run is None:
        raise missing_resource_error(f"command run '{run_id}' is not part of task '{task_id}'")
    return command_run_record_from_model(command_run)


async def read_command_run_log(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
) -> CommandRunLogReadResponse:
    await _require_flow_for_task(session, task_id)
    command_run = await load_command_run_for_task(session, task_id=task_id, run_id=run_id)
    if command_run is None:
        raise missing_resource_error(f"command run '{run_id}' is not part of task '{task_id}'")

    log_ref = command_run_log_ref(command_run)
    if log_ref is None:
        raise missing_resource_error(f"command run '{run_id}' does not have an available log")

    task_root_paths = await read_task_root_paths(session, task_id)
    log_path = task_root_paths.task_root / log_ref
    if not await asyncio.to_thread(log_path.is_file):
        raise missing_resource_error(f"command run '{run_id}' log file is missing")

    content = await asyncio.to_thread(_read_log_content, log_path)
    return CommandRunLogReadResponse(
        task_id=task_id,
        run_id=run_id,
        log_ref=log_ref,
        content=content,
    )


async def load_command_run_for_task(
    session: AsyncSession,
    *,
    task_id: str,
    run_id: str,
) -> CommandRunModel | None:
    return cast(
        CommandRunModel | None,
        await session.scalar(
            select(CommandRunModel).where(
                CommandRunModel.task_id == task_id,
                CommandRunModel.run_id == run_id,
            )
        ),
    )


def command_run_conflict(summary: str) -> RuntimeOperationError:
    return RuntimeOperationError(
        code=OperationFailureCode.ILLEGAL_STATE,
        summary=summary,
        is_retryable=False,
        suggested_next_step=COMMAND_RUN_CONFLICT_NEXT_STEP,
        status_code_override=409,
    )


def command_run_log_ref(command_run: CommandRunModel) -> str | None:
    if command_run.terminal_log_ref is not None:
        return command_run.terminal_log_ref
    return command_run.latest_log_ref


def _read_log_content(log_path: Path) -> str:
    return log_path.read_bytes().decode("utf-8", errors="replace")


async def _require_flow_for_task(
    session: AsyncSession,
    task_id: str,
) -> FlowModel:
    from autoclaw.runtime.flow.queries import require_flow_for_task

    return await require_flow_for_task(session, task_id)


__all__ = [
    "command_run_conflict",
    "command_run_log_ref",
    "list_command_runs",
    "load_command_run_for_task",
    "read_command_run",
    "read_command_run_log",
]
