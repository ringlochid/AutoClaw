from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.persistence.models import CommandRunModel, FlowWaitStateModel
from autoclaw.runtime.contracts import CommandRunState, WaitingCause

ACTIVE_COMMAND_RUN_STATES = frozenset(
    {
        CommandRunState.PENDING_START.value,
        CommandRunState.RUNNING.value,
        CommandRunState.CANCELLATION_REQUESTED.value,
    }
)


@dataclass(frozen=True)
class CurrentCommandRun:
    run_id: str
    task_id: str
    command: str
    workdir: str | None
    timeout_seconds: int | None
    state: str


async def list_current_command_runs(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[CurrentCommandRun]:
    async with session_factory() as session:
        rows = list(
            await session.scalars(
                select(CommandRunModel)
                .join(
                    FlowWaitStateModel,
                    FlowWaitStateModel.command_run_id == CommandRunModel.run_id,
                )
                .where(
                    FlowWaitStateModel.waiting_cause == WaitingCause.WAITING_FOR_COMMAND_RUN.value,
                    CommandRunModel.state.in_(tuple(sorted(ACTIVE_COMMAND_RUN_STATES))),
                )
                .order_by(CommandRunModel.created_at.asc(), CommandRunModel.run_id.asc())
            )
        )
    return [
        CurrentCommandRun(
            run_id=row.run_id,
            task_id=row.task_id,
            command=row.command,
            workdir=row.workdir,
            timeout_seconds=row.timeout_seconds,
            state=row.state,
        )
        for row in rows
    ]


async def read_current_command_run_state(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    run_id: str,
) -> str | None:
    async with session_factory() as session:
        return cast(
            str | None,
            await session.scalar(
                select(CommandRunModel.state)
                .join(
                    FlowWaitStateModel,
                    FlowWaitStateModel.command_run_id == CommandRunModel.run_id,
                )
                .where(
                    CommandRunModel.task_id == task_id,
                    CommandRunModel.run_id == run_id,
                    FlowWaitStateModel.waiting_cause == WaitingCause.WAITING_FOR_COMMAND_RUN.value,
                )
            ),
        )


__all__ = [
    "CurrentCommandRun",
    "list_current_command_runs",
    "read_current_command_run_state",
]
