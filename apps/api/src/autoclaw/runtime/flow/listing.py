from __future__ import annotations

from pathlib import Path
from typing import cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload
from sqlalchemy.sql import Select

from autoclaw.persistence.models import (
    AssignmentModel,
    FlowModel,
    FlowNodeModel,
    TaskModel,
    TaskResourceBindingModel,
)
from autoclaw.runtime.contracts import (
    FlowStatus,
    RuntimeFlowSummary,
    RuntimeFlowSummaryListResponse,
    WorkflowManifestRef,
)
from autoclaw.runtime.errors import invalid_request_shape_error, missing_resource_error
from autoclaw.runtime.flow.timestamps import coerce_datetime_to_utc

WORKFLOW_MANIFEST_REF_DESCRIPTION = "Whole-workflow visible contract for the current task."
RUNTIME_FLOW_LIST_STATUSES = frozenset(
    {
        "any",
        FlowStatus.PENDING.value,
        FlowStatus.RUNNING.value,
        FlowStatus.BLOCKED.value,
        FlowStatus.PAUSED.value,
        FlowStatus.SUCCEEDED.value,
        FlowStatus.CANCELLED.value,
    }
)
RUNTIME_FLOW_LIST_SORTS = frozenset(
    {
        "updated_at_desc",
        "updated_at_asc",
        "task_title_asc",
        "task_title_desc",
    }
)

type RuntimeFlowSummaryRow = tuple[FlowModel, TaskModel, str | None]


def parse_runtime_flow_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise invalid_request_shape_error("cursor must be an integer offset") from exc
    if offset < 0:
        raise invalid_request_shape_error("cursor must be non-negative")
    return offset


async def runtime_root_paths_by_task(
    session: AsyncSession,
    task_ids: tuple[str, ...],
) -> dict[str, Path]:
    if not task_ids:
        return {}
    rows = cast(
        list[tuple[str, str]],
        (
            await session.execute(
                select(TaskResourceBindingModel.task_id, TaskResourceBindingModel.path).where(
                    TaskResourceBindingModel.task_id.in_(task_ids),
                    TaskResourceBindingModel.binding_kind == "runtime",
                )
            )
        ).all(),
    )
    runtime_paths = {task_id: Path(path) for task_id, path in rows}
    missing = set(task_ids).difference(runtime_paths)
    if missing:
        raise missing_resource_error(
            "missing runtime root binding for task(s): " + ", ".join(sorted(missing))
        )
    return runtime_paths


async def runtime_flow_summary_page(
    session: AsyncSession,
    *,
    q: str | None,
    status: str,
    sort: str,
    offset: int,
    limit: int,
) -> RuntimeFlowSummaryListResponse:
    query = _runtime_flow_summary_query(q=q, status=status, sort=sort)
    rows = cast(
        list[RuntimeFlowSummaryRow],
        (await session.execute(query.offset(offset).limit(limit + 1))).all(),
    )
    items = await _runtime_flow_summaries(session, rows[:limit])
    next_cursor = str(offset + limit) if len(rows) > limit else None
    return RuntimeFlowSummaryListResponse(items=items, next_cursor=next_cursor)


def _runtime_flow_summary_query(
    *,
    q: str | None,
    status: str,
    sort: str,
) -> Select[tuple[FlowModel, TaskModel, str | None]]:
    query = (
        select(
            FlowModel,
            TaskModel,
            AssignmentModel.current_attempt_id.label("active_attempt_id"),
        )
        .options(raiseload("*"))
        .join(TaskModel, TaskModel.task_id == FlowModel.task_id)
        .outerjoin(
            FlowNodeModel,
            and_(
                FlowNodeModel.flow_revision_id == FlowModel.active_flow_revision_id,
                FlowNodeModel.node_key == FlowModel.current_node_key,
            ),
        )
        .outerjoin(
            AssignmentModel,
            AssignmentModel.assignment_id == FlowNodeModel.current_assignment_id,
        )
    )
    if status != "any":
        query = query.where(FlowModel.status == status)
    if q is not None:
        search = f"%{q.lower()}%"
        query = query.where(
            or_(
                func.lower(TaskModel.task_id).like(search),
                func.lower(TaskModel.title).like(search),
                func.lower(TaskModel.summary).like(search),
                func.lower(func.coalesce(TaskModel.workflow_key, "")).like(search),
                func.lower(func.coalesce(FlowModel.current_node_key, "")).like(search),
            )
        )
    if sort == "updated_at_asc":
        return query.order_by(FlowModel.updated_at.asc(), TaskModel.task_id.asc())
    if sort == "task_title_asc":
        return query.order_by(func.lower(TaskModel.title).asc(), TaskModel.task_id.asc())
    if sort == "task_title_desc":
        return query.order_by(func.lower(TaskModel.title).desc(), TaskModel.task_id.asc())
    return query.order_by(FlowModel.updated_at.desc(), TaskModel.task_id.asc())


async def _runtime_flow_summaries(
    session: AsyncSession,
    rows: list[RuntimeFlowSummaryRow],
) -> tuple[RuntimeFlowSummary, ...]:
    runtime_paths = await runtime_root_paths_by_task(
        session,
        tuple(task.task_id for _, task, _ in rows),
    )
    items: list[RuntimeFlowSummary] = []
    for flow, task, active_attempt_id in rows:
        items.append(
            RuntimeFlowSummary(
                task_id=task.task_id,
                task_title=task.title,
                task_summary=task.summary,
                workflow_key=task.workflow_key,
                status=FlowStatus(flow.status),
                active_flow_revision_id=flow.active_flow_revision_id or "",
                workflow_manifest_ref=WorkflowManifestRef(
                    path=runtime_paths[task.task_id] / "workflow-manifest.md",
                    description=WORKFLOW_MANIFEST_REF_DESCRIPTION,
                ),
                current_node_key=flow.current_node_key,
                active_attempt_id=active_attempt_id,
                updated_at=coerce_datetime_to_utc(flow.updated_at),
            )
        )
    return tuple(items)
