from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import DispatchTurnModel, FlowModel
from autoclaw.runtime.contracts import (
    ObservabilityFileRef,
    OperatorFlowSnapshotResponse,
    OperatorSupportSurfaceRef,
    TopActionableItem,
    WorkflowManifestRef,
)
from autoclaw.runtime.errors import missing_resource_error
from autoclaw.runtime.flow.queries import (
    current_semantic_flow_target,
    require_flow_for_task,
)
from autoclaw.runtime.flow.reads import runtime_flow_read
from autoclaw.runtime.task_root.reads import read_task_root_paths

OBSERVABILITY_FILE_SPECS: tuple[tuple[str, str], ...] = (
    ("delivery-state.json", "Latest task-scoped delivery-state projection."),
    ("continuity-state.json", "Latest task-scoped continuity-state projection."),
    ("watchdog-state.json", "Latest task-scoped watchdog-state projection."),
    ("provider-events.ndjson", "Normalized provider-event history for the selected task."),
)
type OperatorCurrentPath = WorkflowManifestRef | ObservabilityFileRef


async def operator_snapshot(
    session: AsyncSession,
    task_id: str,
) -> OperatorFlowSnapshotResponse:
    from autoclaw.runtime.contracts import FlowStatus

    flow = await runtime_flow_read(session, task_id)
    current_paths = await operator_current_paths(session, task_id)
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


async def observability_ref(
    session: AsyncSession,
    task_id: str,
    filename: str,
    description: str,
) -> ObservabilityFileRef:
    dispatch_id = await _observability_dispatch_id(session, task_id)
    if dispatch_id is None:
        raise missing_resource_error("task has no dispatch history")
    paths = await read_task_root_paths(session, task_id)
    return ObservabilityFileRef(
        path=paths.dispatch_path / dispatch_id / filename,
        description=description,
    )


async def operator_current_paths(
    session: AsyncSession,
    task_id: str,
) -> tuple[OperatorSupportSurfaceRef, ...]:
    paths = await read_task_root_paths(session, task_id)
    current_paths: list[OperatorCurrentPath] = [
        WorkflowManifestRef(
            path=paths.runtime_path / "workflow-manifest.md",
            description="Whole-workflow visible contract for the current task.",
        )
    ]
    dispatch_id = await _current_open_dispatch_id(session, task_id)
    if dispatch_id is None:
        return tuple(OperatorSupportSurfaceRef.model_validate(path) for path in current_paths)
    current_paths.extend(
        ObservabilityFileRef(
            path=paths.dispatch_path / dispatch_id / filename,
            description=description,
        )
        for filename, description in OBSERVABILITY_FILE_SPECS
    )
    return tuple(OperatorSupportSurfaceRef.model_validate(path) for path in current_paths)


async def current_trace_scope(
    session: AsyncSession,
    flow: FlowModel,
) -> tuple[str | None, str | None]:
    semantic_target = await current_semantic_flow_target(
        session,
        flow=flow,
        incomplete_summary="current semantic target is incomplete",
        suggested_next_step=(
            "Inspect the current node assignment and attempt currentness, then repair the "
            "incomplete semantic target before rereading current trace scope."
        ),
    )
    if semantic_target is None:
        return flow.current_node_key, None
    return semantic_target.node.node_key, semantic_target.attempt.attempt_id


async def _latest_dispatch_id(session: AsyncSession, task_id: str) -> str | None:
    return cast(
        str | None,
        await session.scalar(
            select(DispatchTurnModel.dispatch_id)
            .where(DispatchTurnModel.task_id == task_id)
            .order_by(DispatchTurnModel.rendered_at.desc())
        ),
    )


async def _current_open_dispatch_id(session: AsyncSession, task_id: str) -> str | None:
    flow = await require_flow_for_task(session, task_id)
    return flow.current_open_dispatch_id


async def _observability_dispatch_id(session: AsyncSession, task_id: str) -> str | None:
    dispatch_id = await _current_open_dispatch_id(session, task_id)
    if dispatch_id is not None:
        return dispatch_id
    return await _latest_dispatch_id(session, task_id)


__all__ = [
    "OBSERVABILITY_FILE_SPECS",
    "current_trace_scope",
    "observability_ref",
    "operator_current_paths",
    "operator_snapshot",
]
