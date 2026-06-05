from __future__ import annotations

from typing import Any, cast

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import (
    AttemptCheckpointModel,
    AttemptModel,
    DispatchTurnModel,
    FlowModel,
)
from autoclaw.runtime.contracts import (
    BoundaryHistoryEntry,
    CheckpointHistoryEntry,
    DispatchHistoryEntry,
    OperatorFlowTraceResponse,
)
from autoclaw.runtime.errors import invalid_request_shape_error
from autoclaw.runtime.flow.queries import require_flow_for_task
from autoclaw.runtime.flow.timestamps import coerce_datetime_to_utc
from autoclaw.runtime.observability.support import (
    current_trace_scope,
    operator_current_paths,
)


async def operator_trace(
    session: AsyncSession,
    task_id: str,
    *,
    scope: str = "current",
    q: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    sort: str = "occurred_at_desc",
) -> OperatorFlowTraceResponse:
    return await _operator_trace(
        session,
        task_id,
        scope=scope,
        q=q,
        cursor=cursor,
        limit=limit,
        sort=sort,
    )


def _boundary_history_entries(
    boundary_rows: list[tuple[str, str, object]],
    *,
    limit: int,
) -> tuple[BoundaryHistoryEntry, ...]:
    entries: list[BoundaryHistoryEntry] = []
    for node_key, accepted_boundary, occurred_at in boundary_rows[:limit]:
        if not isinstance(occurred_at, object):
            continue
        entries.append(
            BoundaryHistoryEntry.model_validate(
                {
                    "node_key": node_key,
                    "boundary": accepted_boundary,
                    "occurred_at": coerce_datetime_to_utc(cast(Any, occurred_at)),
                }
            )
        )
    return tuple(entries)


def _parse_trace_offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise invalid_request_shape_error("cursor must be an integer offset") from exc
    if offset < 0:
        raise invalid_request_shape_error("cursor must be non-negative")
    return offset


def _base_trace_queries(task_id: str) -> tuple[Any, Any, Any]:
    dispatch_query = (
        select(DispatchTurnModel)
        .options(raiseload("*"))
        .where(DispatchTurnModel.task_id == task_id)
    )
    checkpoint_query = (
        select(AttemptCheckpointModel)
        .options(raiseload("*"))
        .join(AttemptModel, AttemptModel.attempt_id == AttemptCheckpointModel.attempt_id)
        .where(AttemptModel.task_id == task_id)
    )
    boundary_query = select(
        DispatchTurnModel.node_key,
        DispatchTurnModel.accepted_boundary,
        func.coalesce(
            DispatchTurnModel.closed_at,
            DispatchTurnModel.rendered_at,
        ).label("occurred_at"),
    ).where(
        DispatchTurnModel.task_id == task_id,
        DispatchTurnModel.accepted_boundary.is_not(None),
    )
    return dispatch_query, checkpoint_query, boundary_query


async def _apply_trace_scope(
    session: AsyncSession,
    flow: FlowModel,
    *,
    scope: str,
    dispatch_query: Any,
    checkpoint_query: Any,
    boundary_query: Any,
) -> tuple[Any, Any, Any]:
    if scope != "current":
        return dispatch_query, checkpoint_query, boundary_query
    current_node_key, current_attempt_id = await current_trace_scope(session, flow)
    if current_node_key is not None:
        dispatch_query = dispatch_query.where(DispatchTurnModel.node_key == current_node_key)
        boundary_query = boundary_query.where(DispatchTurnModel.node_key == current_node_key)
    if current_attempt_id is not None:
        checkpoint_query = checkpoint_query.where(AttemptModel.attempt_id == current_attempt_id)
    elif current_node_key is not None:
        checkpoint_query = checkpoint_query.where(AttemptModel.node_key == current_node_key)
    return dispatch_query, checkpoint_query, boundary_query


def _apply_trace_search(
    *,
    q: str | None,
    dispatch_query: Any,
    checkpoint_query: Any,
    boundary_query: Any,
) -> tuple[Any, Any, Any]:
    if q is None:
        return dispatch_query, checkpoint_query, boundary_query
    search = f"%{q.lower()}%"
    dispatch_query = dispatch_query.where(
        or_(
            func.lower(DispatchTurnModel.node_key).like(search),
            func.lower(func.coalesce(DispatchTurnModel.assignment_key, "")).like(search),
            func.lower(DispatchTurnModel.delivery_status).like(search),
        )
    )
    checkpoint_query = checkpoint_query.where(
        or_(
            func.lower(AttemptCheckpointModel.summary).like(search),
            func.lower(AttemptCheckpointModel.attempt_id).like(search),
            func.lower(AttemptModel.node_key).like(search),
        )
    )
    boundary_query = boundary_query.where(
        or_(
            func.lower(DispatchTurnModel.node_key).like(search),
            func.lower(DispatchTurnModel.accepted_boundary).like(search),
        )
    )
    return dispatch_query, checkpoint_query, boundary_query


def _apply_trace_sort(
    *,
    sort: str,
    dispatch_query: Any,
    checkpoint_query: Any,
    boundary_query: Any,
) -> tuple[Any, Any, Any]:
    if sort == "occurred_at_asc":
        dispatch_query = dispatch_query.order_by(
            DispatchTurnModel.rendered_at.asc(),
            DispatchTurnModel.dispatch_id.asc(),
        )
        checkpoint_query = checkpoint_query.order_by(
            AttemptCheckpointModel.recorded_at.asc(),
            AttemptCheckpointModel.checkpoint_id.asc(),
        )
        boundary_query = boundary_query.order_by(
            func.coalesce(
                DispatchTurnModel.closed_at,
                DispatchTurnModel.rendered_at,
            ).asc(),
            DispatchTurnModel.dispatch_id.asc(),
        )
        return dispatch_query, checkpoint_query, boundary_query
    dispatch_query = dispatch_query.order_by(
        DispatchTurnModel.rendered_at.desc(),
        DispatchTurnModel.dispatch_id.asc(),
    )
    checkpoint_query = checkpoint_query.order_by(
        AttemptCheckpointModel.recorded_at.desc(),
        AttemptCheckpointModel.checkpoint_id.asc(),
    )
    boundary_query = boundary_query.order_by(
        func.coalesce(
            DispatchTurnModel.closed_at,
            DispatchTurnModel.rendered_at,
        ).desc(),
        DispatchTurnModel.dispatch_id.asc(),
    )
    return dispatch_query, checkpoint_query, boundary_query


async def _trace_history(
    session: AsyncSession,
    *,
    dispatch_query: Any,
    checkpoint_query: Any,
    boundary_query: Any,
    offset: int,
    limit: int,
) -> tuple[list[DispatchTurnModel], list[AttemptCheckpointModel], list[tuple[str, str, object]]]:
    dispatches = cast(
        list[DispatchTurnModel],
        list(await session.scalars(dispatch_query.offset(offset).limit(limit + 1))),
    )
    checkpoints = cast(
        list[AttemptCheckpointModel],
        list(await session.scalars(checkpoint_query.offset(offset).limit(limit + 1))),
    )
    boundary_rows = cast(
        list[tuple[str, str, object]],
        list((await session.execute(boundary_query.offset(offset).limit(limit + 1))).all()),
    )
    return dispatches, checkpoints, boundary_rows


def _build_operator_trace_response(
    *,
    task_id: str,
    scope: str,
    limit: int,
    offset: int,
    dispatches: list[DispatchTurnModel],
    checkpoints: list[AttemptCheckpointModel],
    boundary_rows: list[tuple[str, str, object]],
    current_paths: tuple[Any, ...],
) -> OperatorFlowTraceResponse:
    return OperatorFlowTraceResponse(
        task_id=task_id,
        scope="whole" if scope == "whole" else "current",
        dispatch_history=tuple(
            DispatchHistoryEntry.model_validate(
                {
                    "attempt_id": dispatch.attempt_id,
                    "assignment_key": dispatch.assignment_key,
                    "node_key": dispatch.node_key,
                    "delivery_status": dispatch.delivery_status,
                    "rendered_at": coerce_datetime_to_utc(dispatch.rendered_at),
                }
            )
            for dispatch in dispatches[:limit]
        ),
        checkpoint_history=tuple(
            CheckpointHistoryEntry.model_validate(
                {
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "attempt_id": checkpoint.attempt_id,
                    "checkpoint_kind": checkpoint.checkpoint_kind,
                    "outcome": checkpoint.outcome,
                    "summary": checkpoint.summary,
                    "recorded_at": coerce_datetime_to_utc(checkpoint.recorded_at),
                }
            )
            for checkpoint in checkpoints[:limit]
        ),
        boundary_history=_boundary_history_entries(boundary_rows, limit=limit),
        current_paths=current_paths,
        next_cursor=_next_cursor(
            offset=offset,
            limit=limit,
            dispatches=dispatches,
            checkpoints=checkpoints,
            boundary_rows=boundary_rows,
        ),
    )


def _next_cursor(
    *,
    offset: int,
    limit: int,
    dispatches: list[DispatchTurnModel],
    checkpoints: list[AttemptCheckpointModel],
    boundary_rows: list[tuple[str, str, object]],
) -> str | None:
    if len(dispatches) > limit or len(checkpoints) > limit or len(boundary_rows) > limit:
        return str(offset + limit)
    return None


async def _operator_trace(
    session: AsyncSession,
    task_id: str,
    *,
    scope: str = "current",
    q: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    sort: str = "occurred_at_desc",
) -> OperatorFlowTraceResponse:
    flow = await require_flow_for_task(session, task_id)
    if scope not in {"current", "whole"}:
        raise invalid_request_shape_error(f"unknown trace scope '{scope}'")
    if sort not in {"occurred_at_desc", "occurred_at_asc"}:
        raise invalid_request_shape_error(f"unknown trace sort '{sort}'")
    offset = _parse_trace_offset(cursor)
    dispatch_query, checkpoint_query, boundary_query = _base_trace_queries(task_id)
    dispatch_query, checkpoint_query, boundary_query = await _apply_trace_scope(
        session,
        flow,
        scope=scope,
        dispatch_query=dispatch_query,
        checkpoint_query=checkpoint_query,
        boundary_query=boundary_query,
    )
    dispatch_query, checkpoint_query, boundary_query = _apply_trace_search(
        q=q,
        dispatch_query=dispatch_query,
        checkpoint_query=checkpoint_query,
        boundary_query=boundary_query,
    )
    dispatch_query, checkpoint_query, boundary_query = _apply_trace_sort(
        sort=sort,
        dispatch_query=dispatch_query,
        checkpoint_query=checkpoint_query,
        boundary_query=boundary_query,
    )
    dispatches, checkpoints, boundary_rows = await _trace_history(
        session,
        dispatch_query=dispatch_query,
        checkpoint_query=checkpoint_query,
        boundary_query=boundary_query,
        offset=offset,
        limit=limit,
    )
    current_paths = await operator_current_paths(session, task_id)
    return _build_operator_trace_response(
        task_id=task_id,
        scope=scope,
        limit=limit,
        offset=offset,
        dispatches=dispatches,
        checkpoints=checkpoints,
        boundary_rows=boundary_rows,
        current_paths=current_paths,
    )


__all__ = ["operator_trace"]
