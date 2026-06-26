from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoclaw.runtime.task_root.reads import load_task_root_paths


async def resolve_command_run_paths(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    workdir: str | None,
    log_ref: str,
) -> tuple[Path, Path]:
    async with session_factory() as session:
        paths = await load_task_root_paths(session, task_id)
    log_path = paths.task_root / log_ref
    command_workdir = resolve_command_workdir(paths.workspace_path, workdir)
    return command_workdir, log_path


async def best_effort_command_log_path(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    log_ref: str,
) -> Path:
    async with session_factory() as session:
        paths = await load_task_root_paths(session, task_id)
    return paths.task_root / log_ref


def resolve_command_workdir(workspace_path: Path, workdir: str | None) -> Path:
    if workdir is None or not workdir.strip():
        return workspace_path.resolve()
    requested_workdir = Path(workdir).expanduser()
    if requested_workdir.is_absolute():
        return requested_workdir.resolve()
    return (workspace_path / requested_workdir).resolve()


__all__ = [
    "best_effort_command_log_path",
    "resolve_command_run_paths",
    "resolve_command_workdir",
]
