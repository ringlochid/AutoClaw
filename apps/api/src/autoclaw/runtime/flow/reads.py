from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import Select, and_, exists, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, raiseload

from autoclaw.persistence.models import (
    CommandRunModel,
    DispatchTurnModel,
    FlowModel,
    HumanRequestModel,
    TaskModel,
)
from autoclaw.runtime.contracts import (
    FlowStatus,
    RuntimeFlowPauseReason,
    RuntimeFlowRead,
    RuntimeFlowSummary,
    RuntimeFlowSummaryListResponse,
    RuntimeFlowWaitingCause,
    WorkflowManifestRef,
)
from autoclaw.runtime.errors import (
    illegal_state_error,
    invalid_request_shape_error,
    missing_resource_error,
)

WORKFLOW_MANIFEST_REF_DESCRIPTION = "Whole-workflow visible contract for the current task."

RUNTIME_FLOW_LIST_SORTS = frozenset(
    {
        "updated_at_desc",
        "updated_at_asc",
        "task_title_asc",
        "task_title_desc",
    }
)
RUNTIME_FLOW_LIST_STATUSES = frozenset(
    {"any", "pending", "running", "blocked", "paused", "succeeded", "cancelled"}
)


@dataclass(frozen=True, slots=True)
class RuntimeFlowTarget:
    node_key: str
    assignment_id: str
    attempt_id: str


async def read_runtime_flow(session: AsyncSession, task_id: str) -> RuntimeFlowRead:
    """Read controller-owned current flow facts for one task."""

    row = (
        await session.execute(
            select(TaskModel, FlowModel)
            .join(FlowModel, FlowModel.task_id == TaskModel.task_id)
            .options(raiseload("*"))
            .where(TaskModel.task_id == task_id)
            .execution_options(populate_existing=True)
        )
    ).one_or_none()
    if row is None:
        raise missing_resource_error(f"unknown task_id '{task_id}'")
    task, flow = row
    if flow.active_flow_revision_id is None:
        raise illegal_state_error(f"task '{task_id}' has no active flow revision")

    target = (
        None
        if flow.status in {"completed", "cancelled"}
        else await read_runtime_flow_target(session, flow)
    )
    return RuntimeFlowRead(
        task_id=task.task_id,
        task_title=task.title,
        task_summary=task.summary,
        workflow_key=task.workflow_key,
        status=public_flow_status(flow),
        active_flow_revision_id=flow.active_flow_revision_id,
        control_revision=flow.control_revision,
        workflow_manifest_ref=workflow_manifest_ref(),
        current_node_key=target.node_key if target is not None else None,
        active_assignment_id=target.assignment_id if target is not None else None,
        active_attempt_id=target.attempt_id if target is not None else None,
        current_dispatch_id=flow.current_dispatch_id,
        waiting_cause=normalized_waiting_cause(flow.waiting_cause),
        pause_reason=normalized_pause_reason(flow.pause_reason),
        updated_at=coerce_datetime_to_utc(flow.updated_at),
    )


async def list_runtime_flow_summaries(
    session: AsyncSession,
    *,
    q: str | None,
    cursor: str | None,
    status: str,
    limit: int,
    sort: str,
) -> RuntimeFlowSummaryListResponse:
    """Return a bounded controller-row task list without support-file reads."""

    validate_runtime_flow_list_arguments(status=status, sort=sort, limit=limit)
    offset = parse_runtime_flow_cursor(cursor)
    statement = runtime_flow_summary_statement(q=q, status=status, sort=sort).offset(offset)
    rows = list((await session.execute(statement.limit(limit + 1))).all())
    page = rows[:limit]
    summaries: list[RuntimeFlowSummary] = []
    for task, flow, dispatch in page:
        if flow.active_flow_revision_id is None:
            raise illegal_state_error(f"task '{task.task_id}' has no active flow revision")
        summaries.append(
            RuntimeFlowSummary(
                task_id=task.task_id,
                task_title=task.title,
                task_summary=task.summary,
                workflow_key=task.workflow_key,
                status=public_flow_status(flow),
                active_flow_revision_id=flow.active_flow_revision_id,
                workflow_manifest_ref=workflow_manifest_ref(),
                current_node_key=dispatch.node_key if dispatch is not None else None,
                active_attempt_id=dispatch.attempt_id if dispatch is not None else None,
                updated_at=coerce_datetime_to_utc(flow.updated_at),
            )
        )
    return RuntimeFlowSummaryListResponse(
        items=tuple(summaries),
        next_cursor=str(offset + limit) if len(rows) > limit else None,
    )


async def read_runtime_flow_target(
    session: AsyncSession,
    flow: FlowModel,
) -> RuntimeFlowTarget | None:
    """Resolve the exact current, waiting, or retained lineage target."""

    if flow.current_dispatch_id is not None:
        dispatch = await session.scalar(
            select(DispatchTurnModel)
            .options(raiseload("*"))
            .where(
                DispatchTurnModel.dispatch_id == flow.current_dispatch_id,
                DispatchTurnModel.task_id == flow.task_id,
                DispatchTurnModel.flow_id == flow.flow_id,
                DispatchTurnModel.status.in_(("starting", "open")),
            )
        )
        if dispatch is None:
            raise illegal_state_error("flow current-dispatch pointer is inconsistent")
        return runtime_flow_target_from_dispatch(dispatch)

    if flow.waiting_cause == "human_request" and flow.waiting_source_id is not None:
        request = await session.scalar(
            select(HumanRequestModel)
            .options(raiseload("*"))
            .where(
                HumanRequestModel.request_id == flow.waiting_source_id,
                HumanRequestModel.task_id == flow.task_id,
                HumanRequestModel.flow_id == flow.flow_id,
            )
        )
        if request is None:
            raise illegal_state_error("flow human-request pointer is inconsistent")
        return RuntimeFlowTarget(
            node_key=(
                await read_dispatch_node_key(session, request.source_dispatch_id, flow.flow_id)
            ),
            assignment_id=request.assignment_id,
            attempt_id=request.attempt_id,
        )

    if flow.waiting_cause == "command_run" and flow.waiting_source_id is not None:
        run = await session.scalar(
            select(CommandRunModel)
            .options(raiseload("*"))
            .where(
                CommandRunModel.run_id == flow.waiting_source_id,
                CommandRunModel.task_id == flow.task_id,
                CommandRunModel.flow_id == flow.flow_id,
            )
        )
        if run is None:
            raise illegal_state_error("flow command-run pointer is inconsistent")
        return RuntimeFlowTarget(
            node_key=await read_dispatch_node_key(session, run.source_dispatch_id, flow.flow_id),
            assignment_id=run.assignment_id,
            attempt_id=run.attempt_id,
        )

    if flow.waiting_cause != "none" or flow.waiting_source_id is not None:
        raise illegal_state_error("flow waiting pointer is inconsistent")
    return await read_retained_lineage_target(session, flow)


def runtime_flow_summary_statement(
    *,
    q: str | None,
    status: str,
    sort: str,
) -> Select[tuple[TaskModel, FlowModel, DispatchTurnModel]]:
    statement = (
        select(TaskModel, FlowModel, DispatchTurnModel)
        .join(FlowModel, FlowModel.task_id == TaskModel.task_id)
        .outerjoin(
            DispatchTurnModel,
            and_(
                DispatchTurnModel.flow_id == FlowModel.flow_id,
                DispatchTurnModel.dispatch_id == FlowModel.current_dispatch_id,
            ),
        )
        .options(raiseload("*"))
    )
    normalized_query = (q or "").strip().lower()
    if normalized_query:
        pattern = f"%{normalized_query}%"
        statement = statement.where(
            or_(
                func.lower(TaskModel.task_id).like(pattern),
                func.lower(TaskModel.title).like(pattern),
                func.lower(TaskModel.summary).like(pattern),
                func.lower(func.coalesce(TaskModel.workflow_key, "")).like(pattern),
            )
        )
    statement = apply_runtime_flow_status_filter(statement, status)
    if sort == "updated_at_asc":
        return statement.order_by(FlowModel.updated_at.asc(), TaskModel.task_id.asc())
    if sort == "task_title_asc":
        return statement.order_by(TaskModel.title.asc(), TaskModel.task_id.asc())
    if sort == "task_title_desc":
        return statement.order_by(TaskModel.title.desc(), TaskModel.task_id.desc())
    return statement.order_by(FlowModel.updated_at.desc(), TaskModel.task_id.desc())


def apply_runtime_flow_status_filter(
    statement: Select[tuple[TaskModel, FlowModel, DispatchTurnModel]],
    status: str,
) -> Select[tuple[TaskModel, FlowModel, DispatchTurnModel]]:
    if status == "any":
        return statement
    if status == "pending":
        return statement.where(false())
    if status == "succeeded":
        return statement.where(
            FlowModel.status == "completed",
            FlowModel.terminal_outcome == "green",
        )
    if status == "blocked":
        return statement.where(
            FlowModel.status == "completed",
            FlowModel.terminal_outcome == "blocked",
        )
    return statement.where(FlowModel.status == status)


async def read_retained_lineage_target(
    session: AsyncSession,
    flow: FlowModel,
) -> RuntimeFlowTarget | None:
    successor = aliased(DispatchTurnModel)
    rows = tuple(
        await session.scalars(
            select(DispatchTurnModel)
            .options(raiseload("*"))
            .where(
                DispatchTurnModel.task_id == flow.task_id,
                DispatchTurnModel.flow_id == flow.flow_id,
                DispatchTurnModel.status == "closed",
                ~exists().where(successor.predecessor_dispatch_id == DispatchTurnModel.dispatch_id),
            )
            .limit(2)
        )
    )
    if len(rows) > 1:
        raise illegal_state_error("flow has more than one retained lineage tail")
    return runtime_flow_target_from_dispatch(rows[0]) if rows else None


async def read_dispatch_node_key(
    session: AsyncSession,
    dispatch_id: str,
    flow_id: str,
) -> str:
    node_key = await session.scalar(
        select(DispatchTurnModel.node_key).where(
            DispatchTurnModel.dispatch_id == dispatch_id,
            DispatchTurnModel.flow_id == flow_id,
        )
    )
    if node_key is None:
        raise illegal_state_error("external source dispatch lineage is incomplete")
    return node_key


def runtime_flow_target_from_dispatch(dispatch: DispatchTurnModel) -> RuntimeFlowTarget:
    return RuntimeFlowTarget(
        node_key=dispatch.node_key,
        assignment_id=dispatch.assignment_id,
        attempt_id=dispatch.attempt_id,
    )


def public_flow_status(flow: FlowModel) -> FlowStatus:
    if flow.status == "completed":
        return FlowStatus.SUCCEEDED if flow.terminal_outcome == "green" else FlowStatus.BLOCKED
    return FlowStatus(flow.status)


def normalized_pause_reason(
    pause_reason: str | None,
) -> RuntimeFlowPauseReason | None:
    if pause_reason is None:
        return None
    if pause_reason not in {
        "paused_by_operator",
        "runtime_recovery_exhausted",
        "runtime_transition_failed",
    }:
        raise illegal_state_error(f"flow has unsupported pause reason '{pause_reason}'")
    return cast(RuntimeFlowPauseReason, pause_reason)


def normalized_waiting_cause(waiting_cause: str) -> RuntimeFlowWaitingCause | None:
    if waiting_cause not in {"human_request", "command_run"}:
        return None
    return cast(RuntimeFlowWaitingCause, waiting_cause)


def workflow_manifest_ref() -> WorkflowManifestRef:
    return WorkflowManifestRef(
        path=Path("_runtime/workflow-manifest.md"),
        description=WORKFLOW_MANIFEST_REF_DESCRIPTION,
    )


def parse_runtime_flow_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise invalid_request_shape_error("runtime task cursor must be an integer offset") from exc
    if offset < 0:
        raise invalid_request_shape_error("runtime task cursor must be non-negative")
    return offset


def validate_runtime_flow_list_arguments(*, status: str, sort: str, limit: int) -> None:
    if status not in RUNTIME_FLOW_LIST_STATUSES:
        raise invalid_request_shape_error(f"unknown status filter '{status}'")
    if sort not in RUNTIME_FLOW_LIST_SORTS:
        raise invalid_request_shape_error(f"unknown runtime task sort '{sort}'")
    if not 1 <= limit <= 200:
        raise invalid_request_shape_error("runtime task limit must be between 1 and 200")


def coerce_datetime_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "RUNTIME_FLOW_LIST_SORTS",
    "RUNTIME_FLOW_LIST_STATUSES",
    "WORKFLOW_MANIFEST_REF_DESCRIPTION",
    "RuntimeFlowTarget",
    "list_runtime_flow_summaries",
    "normalized_pause_reason",
    "normalized_waiting_cause",
    "read_runtime_flow",
    "read_runtime_flow_target",
]
