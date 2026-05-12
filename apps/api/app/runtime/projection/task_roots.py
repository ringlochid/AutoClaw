from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import TaskModel, TaskResourceBindingModel
from app.runtime.contracts import TaskRootPaths
from app.runtime.resources import ensure_task_root_layout

_REQUIRED_TASK_ROOT_BINDINGS = frozenset(
    {
        "workspace",
        "context",
        "criteria",
        "wiki",
        "outputs",
        "artifacts",
        "tmp",
        "transfers",
        "runtime",
        "attempts",
        "dispatch",
    }
)


async def _task_with_root_bindings(
    session: AsyncSession,
    task_id: str,
) -> tuple[TaskModel, dict[str, str]]:
    rows = list(
        (
            await session.execute(
                select(TaskModel, TaskResourceBindingModel)
                .options(raiseload("*"))
                .outerjoin(
                    TaskResourceBindingModel,
                    TaskResourceBindingModel.task_id == TaskModel.task_id,
                )
                .where(TaskModel.task_id == task_id)
                .order_by(TaskResourceBindingModel.binding_kind.asc())
            )
        ).all()
    )
    if not rows:
        raise ValueError(f"unknown task_id '{task_id}'")
    task = rows[0][0]
    bindings = {binding.binding_kind: binding.path for _, binding in rows if binding is not None}
    missing = _REQUIRED_TASK_ROOT_BINDINGS.difference(bindings)
    if missing:
        raise ValueError(
            f"task '{task_id}' is missing task root bindings: {', '.join(sorted(missing))}"
        )
    return task, bindings


async def load_task_root_paths(session: AsyncSession, task_id: str) -> TaskRootPaths:
    task, bindings = await _task_with_root_bindings(session, task_id)
    paths = TaskRootPaths(
        task_root=Path(task.task_root_path),
        workspace_path=Path(bindings["workspace"]),
        context_path=Path(bindings["context"]),
        criteria_path=Path(bindings["criteria"]),
        wiki_path=Path(bindings["wiki"]),
        outputs_path=Path(bindings["outputs"]),
        artifacts_path=Path(bindings["artifacts"]),
        tmp_path=Path(bindings["tmp"]),
        transfers_path=Path(bindings["transfers"]),
        runtime_path=Path(bindings["runtime"]),
        attempts_path=Path(bindings["attempts"]),
        dispatch_path=Path(bindings["dispatch"]),
    )
    ensure_task_root_layout(paths)
    return paths
