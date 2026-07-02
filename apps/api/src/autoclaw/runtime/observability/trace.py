from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload, selectinload

from autoclaw.persistence.models import (
    AttemptCheckpointModel,
    AttemptModel,
    DispatchTurnModel,
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    TaskEventModel,
)
from autoclaw.runtime.contracts import (
    BoundaryHistoryEntry,
    CheckpointHistoryEntry,
    DispatchHistoryEntry,
    OperatorFlowTraceResponse,
    TaskEventType,
    TaskGraphDependencyEntry,
    TaskGraphNodeEntry,
)
from autoclaw.runtime.errors import invalid_request_shape_error
from autoclaw.runtime.flow.queries import require_flow_for_task
from autoclaw.runtime.flow.timestamps import coerce_datetime_to_utc
from autoclaw.runtime.observability.support import (
    current_trace_scope,
    operator_current_paths,
)

type BoundaryTraceRow = tuple[str, str, datetime, dict[str, Any] | None]


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
    graph_nodes, dependency_edges = await _trace_graph(session, flow)
    current_paths = await operator_current_paths(session, task_id)
    return _build_operator_trace_response(
        task_id=task_id,
        scope=scope,
        limit=limit,
        offset=offset,
        graph_nodes=graph_nodes,
        dependency_edges=dependency_edges,
        dispatches=dispatches,
        checkpoints=checkpoints,
        boundary_rows=boundary_rows,
        current_paths=current_paths,
    )


def _boundary_history_entries(
    boundary_rows: list[BoundaryTraceRow],
    *,
    limit: int,
) -> tuple[BoundaryHistoryEntry, ...]:
    entries: list[BoundaryHistoryEntry] = []
    for node_key, accepted_boundary, occurred_at, event_payload in boundary_rows[:limit]:
        payload = event_payload or {}
        entries.append(
            BoundaryHistoryEntry.model_validate(
                {
                    "node_key": node_key,
                    "boundary": accepted_boundary,
                    "previous_node_key": str(payload.get("previous_node_key") or node_key),
                    "next_node_key": payload.get("next_node_key"),
                    "next_attempt_id": payload.get("next_attempt_id"),
                    "resulting_flow_status": payload.get("resulting_flow_status"),
                    "should_reopen_after_inactivity": payload.get(
                        "requires_reopen_after_inactivity"
                    ),
                    "occurred_at": coerce_datetime_to_utc(occurred_at),
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
        .options(raiseload("*"), selectinload(DispatchTurnModel.assignment))
        .where(DispatchTurnModel.task_id == task_id)
    )
    checkpoint_query = (
        select(AttemptCheckpointModel)
        .options(raiseload("*"))
        .join(AttemptModel, AttemptModel.attempt_id == AttemptCheckpointModel.attempt_id)
        .where(AttemptModel.task_id == task_id)
    )
    boundary_query = (
        select(
            DispatchTurnModel.node_key,
            DispatchTurnModel.accepted_boundary,
            func.coalesce(
                DispatchTurnModel.closed_at,
                DispatchTurnModel.rendered_at,
            ).label("occurred_at"),
            TaskEventModel.payload,
        )
        .outerjoin(
            TaskEventModel,
            (TaskEventModel.task_id == DispatchTurnModel.task_id)
            & (TaskEventModel.dispatch_id == DispatchTurnModel.dispatch_id)
            & (TaskEventModel.event_type == TaskEventType.BOUNDARY_ACCEPTED.value),
        )
        .where(
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.accepted_boundary.is_not(None),
        )
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
) -> tuple[list[DispatchTurnModel], list[AttemptCheckpointModel], list[BoundaryTraceRow]]:
    dispatches = cast(
        list[DispatchTurnModel],
        list(await session.scalars(dispatch_query.offset(offset).limit(limit + 1))),
    )
    checkpoints = cast(
        list[AttemptCheckpointModel],
        list(await session.scalars(checkpoint_query.offset(offset).limit(limit + 1))),
    )
    boundary_rows = cast(
        list[BoundaryTraceRow],
        list((await session.execute(boundary_query.offset(offset).limit(limit + 1))).all()),
    )
    return dispatches, checkpoints, boundary_rows


async def _trace_graph(
    session: AsyncSession,
    flow: FlowModel,
) -> tuple[tuple[TaskGraphNodeEntry, ...], tuple[TaskGraphDependencyEntry, ...]]:
    if flow.active_flow_revision_id is None:
        return (), ()

    node_rows = list(
        await session.scalars(
            select(FlowNodeModel)
            .options(raiseload("*"))
            .where(FlowNodeModel.flow_revision_id == flow.active_flow_revision_id)
            .order_by(FlowNodeModel.order_index.asc(), FlowNodeModel.node_key.asc())
        )
    )
    edge_rows = list(
        await session.scalars(
            select(FlowEdgeModel)
            .options(raiseload("*"))
            .where(FlowEdgeModel.flow_revision_id == flow.active_flow_revision_id)
            .order_by(FlowEdgeModel.order_index.asc(), FlowEdgeModel.flow_edge_id.asc())
        )
    )
    return _graph_node_entries(node_rows, edge_rows), _graph_dependency_entries(edge_rows)


def _graph_node_entries(
    node_rows: list[FlowNodeModel],
    edge_rows: list[FlowEdgeModel],
) -> tuple[TaskGraphNodeEntry, ...]:
    child_node_keys_by_parent: dict[str, list[str]] = {}
    depends_on_node_keys_by_consumer: dict[str, list[str]] = {}
    depended_on_by_provider: dict[str, list[str]] = {}

    for node in node_rows:
        if node.parent_node_key is not None:
            child_node_keys_by_parent.setdefault(node.parent_node_key, []).append(node.node_key)

    for edge in edge_rows:
        depends_on_node_keys_by_consumer.setdefault(edge.consumer_node_key, []).append(
            edge.provider_node_key
        )
        depended_on_by_provider.setdefault(edge.provider_node_key, []).append(
            edge.consumer_node_key
        )

    return tuple(
        TaskGraphNodeEntry.model_validate(
            {
                "node_key": node.node_key,
                "parent_node_key": node.parent_node_key,
                "node_kind": node.structural_kind,
                "role": node.role_key,
                "policy": node.policy_key,
                "description": node.description,
                "order_index": node.order_index,
                "child_node_keys": _ordered_unique(
                    child_node_keys_by_parent.get(node.node_key, [])
                ),
                "depends_on_node_keys": _ordered_unique(
                    depends_on_node_keys_by_consumer.get(node.node_key, [])
                ),
                "depended_on_by_node_keys": _ordered_unique(
                    depended_on_by_provider.get(node.node_key, [])
                ),
            }
        )
        for node in node_rows
    )


def _graph_dependency_entries(
    edge_rows: list[FlowEdgeModel],
) -> tuple[TaskGraphDependencyEntry, ...]:
    return tuple(
        TaskGraphDependencyEntry.model_validate(
            {
                "provider_node_key": edge.provider_node_key,
                "consumer_node_key": edge.consumer_node_key,
                "kind": edge.kind,
                "slot": edge.slot,
                "description": edge.description,
                "order_index": edge.order_index,
            }
        )
        for edge in edge_rows
    )


def _ordered_unique(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _build_operator_trace_response(
    *,
    task_id: str,
    scope: str,
    limit: int,
    offset: int,
    graph_nodes: tuple[TaskGraphNodeEntry, ...],
    dependency_edges: tuple[TaskGraphDependencyEntry, ...],
    dispatches: list[DispatchTurnModel],
    checkpoints: list[AttemptCheckpointModel],
    boundary_rows: list[BoundaryTraceRow],
    current_paths: tuple[Any, ...],
) -> OperatorFlowTraceResponse:
    return OperatorFlowTraceResponse(
        task_id=task_id,
        scope="whole" if scope == "whole" else "current",
        graph_nodes=graph_nodes,
        dependency_edges=dependency_edges,
        dispatch_history=tuple(
            DispatchHistoryEntry.model_validate(
                {
                    "attempt_id": dispatch.attempt_id,
                    "assignment_key": dispatch.assignment_key,
                    "assignment_summary": (
                        None if dispatch.assignment is None else dispatch.assignment.summary
                    ),
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
    boundary_rows: list[BoundaryTraceRow],
) -> str | None:
    if len(dispatches) > limit or len(checkpoints) > limit or len(boundary_rows) > limit:
        return str(offset + limit)
    return None


__all__ = ["operator_trace"]
