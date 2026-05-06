from __future__ import annotations

from typing import cast

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import (
    AttemptCheckpointModel,
    AttemptModel,
    DispatchTurnModel,
)
from app.runtime.contracts import (
    FlowStatus,
)
from app.runtime.control.flows import runtime_flow_read
from app.runtime.control.support import _flow_by_task
from app.runtime.projection import (
    load_task_root_paths,
    materialize_dispatch_files,
)
from app.schemas.runtime import (
    BoundaryHistoryEntry,
    CheckpointHistoryEntry,
    DispatchHistoryEntry,
    ObservabilityFileRef,
    OperatorFlowSnapshotResponse,
    OperatorFlowTraceResponse,
    OperatorSupportSurfaceRef,
    TopActionableItem,
    WorkflowManifestRef,
)

_OBSERVABILITY_FILE_SPECS: tuple[tuple[str, str], ...] = (
    ("delivery-state.json", "Latest task-scoped delivery-state projection."),
    ("continuity-state.json", "Latest task-scoped continuity-state projection."),
    ("watchdog-state.json", "Latest task-scoped watchdog-state projection."),
    ("provider-events.ndjson", "Normalized provider-event history for the selected task."),
)
type OperatorCurrentPath = WorkflowManifestRef | ObservabilityFileRef


async def _latest_dispatch_id(session: AsyncSession, task_id: str) -> str | None:
    return cast(
        str | None,
        await session.scalar(
            select(DispatchTurnModel.dispatch_id)
            .where(DispatchTurnModel.task_id == task_id)
            .order_by(DispatchTurnModel.rendered_at.desc())
        ),
    )


async def _current_dispatch_id(session: AsyncSession, task_id: str) -> str | None:
    flow = await _flow_by_task(session, task_id)
    return flow.current_open_dispatch_id or await _latest_dispatch_id(session, task_id)


async def _operator_current_paths(
    session: AsyncSession,
    task_id: str,
) -> tuple[OperatorSupportSurfaceRef, ...]:
    paths = await load_task_root_paths(session, task_id)
    current_paths: list[OperatorCurrentPath] = [
        WorkflowManifestRef(
            path=paths.runtime_path / "workflow-manifest.md",
            description="Whole-workflow visible contract for the current task.",
        )
    ]
    dispatch_id = await _current_dispatch_id(session, task_id)
    if dispatch_id is None:
        return tuple(OperatorSupportSurfaceRef.model_validate(path) for path in current_paths)
    await materialize_dispatch_files(session, task_id, dispatch_id)
    current_paths.extend(
        ObservabilityFileRef(
            path=paths.dispatch_path / dispatch_id / filename,
            description=description,
        )
        for filename, description in _OBSERVABILITY_FILE_SPECS
    )
    return tuple(OperatorSupportSurfaceRef.model_validate(path) for path in current_paths)


async def operator_snapshot(session: AsyncSession, task_id: str) -> OperatorFlowSnapshotResponse:
    flow = await runtime_flow_read(session, task_id)
    current_paths = await _operator_current_paths(session, task_id)
    return OperatorFlowSnapshotResponse(
        flow=flow,
        top_actionable_items=(
            TopActionableItem(
                summary=f"Current runtime status is '{flow.status.value}'.",
                node_key=flow.current_node_key,
                current_paths=current_paths,
                suggested_action="continue" if flow.status == FlowStatus.PAUSED else None,
            ),
        ),
        current_paths=current_paths,
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
    flow = await _flow_by_task(session, task_id)
    if scope not in {"current", "whole"}:
        raise ValueError(f"unknown trace scope '{scope}'")
    if sort not in {"occurred_at_desc", "occurred_at_asc"}:
        raise ValueError(f"unknown trace sort '{sort}'")
    offset = 0
    if cursor is not None:
        try:
            offset = int(cursor)
        except ValueError as exc:
            raise ValueError("cursor must be an integer offset") from exc
        if offset < 0:
            raise ValueError("cursor must be non-negative")

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
    if scope == "current" and flow.current_node_key is not None:
        dispatch_query = dispatch_query.where(DispatchTurnModel.node_key == flow.current_node_key)
        checkpoint_query = checkpoint_query.where(AttemptModel.node_key == flow.current_node_key)
        boundary_query = boundary_query.where(DispatchTurnModel.node_key == flow.current_node_key)
    if q is not None:
        search = f"%{q.lower()}%"
        dispatch_query = dispatch_query.where(
            or_(
                func.lower(DispatchTurnModel.node_key).like(search),
                func.lower(func.coalesce(DispatchTurnModel.assignment_key, "")).like(search),
                func.lower(DispatchTurnModel.send_mode).like(search),
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
    else:
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

    dispatches = list(await session.scalars(dispatch_query.offset(offset).limit(limit + 1)))
    checkpoints = list(await session.scalars(checkpoint_query.offset(offset).limit(limit + 1)))
    boundary_rows = list(
        (await session.execute(boundary_query.offset(offset).limit(limit + 1))).all()
    )
    current_paths = await _operator_current_paths(session, task_id)
    return OperatorFlowTraceResponse(
        task_id=task_id,
        scope="whole" if scope == "whole" else "current",
        dispatch_history=tuple(
            DispatchHistoryEntry.model_validate(dispatch, from_attributes=True)
            for dispatch in dispatches[:limit]
        ),
        checkpoint_history=tuple(
            CheckpointHistoryEntry.model_validate(checkpoint, from_attributes=True)
            for checkpoint in checkpoints[:limit]
        ),
        boundary_history=tuple(
            BoundaryHistoryEntry.model_validate(
                {
                    "node_key": node_key,
                    "boundary": accepted_boundary,
                    "occurred_at": occurred_at,
                }
            )
            for node_key, accepted_boundary, occurred_at in boundary_rows[:limit]
        ),
        current_paths=current_paths,
        next_cursor=(
            str(offset + limit)
            if len(dispatches) > limit or len(checkpoints) > limit or len(boundary_rows) > limit
            else None
        ),
    )


async def observability_ref(
    session: AsyncSession,
    task_id: str,
    filename: str,
    description: str,
) -> ObservabilityFileRef:
    dispatch_id = await _current_dispatch_id(session, task_id)
    if dispatch_id is None:
        raise ValueError("task has no dispatch history")
    paths = await load_task_root_paths(session, task_id)
    await materialize_dispatch_files(session, task_id, dispatch_id)
    return ObservabilityFileRef(
        path=paths.dispatch_path / dispatch_id / filename,
        description=description,
    )
