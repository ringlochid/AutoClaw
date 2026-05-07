from __future__ import annotations

from pathlib import Path
from typing import cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import (
    AssignmentModel,
    AttemptModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    TaskModel,
    TaskResourceBindingModel,
)
from app.runtime.contracts import (
    CheckpointKind,
    FlowStatus,
    PromptSendMode,
)
from app.runtime.control.release import (
    _dispatch_deadline_expired,
    _dispatch_inactivity_proven,
    _dispatch_waiting_for_inactivity,
    _flow_node_by_key,
    _mark_dispatch_ambiguous,
    _mark_dispatch_fenced,
    _open_dispatch_for_attempt,
)
from app.runtime.control.support import (
    _dispatch_control_deadline,
    _flow_by_task,
    _latest_checkpoint_for_attempt,
    _latest_closed_dispatch_for_task,
    _latest_resumable_dispatch_for_attempt,
    _now,
    _queue_dispatch_materialization,
    _release_workspace_root_lease,
    _revoke_callback_binding,
)
from app.runtime.projection import (
    current_runtime_state,
)
from app.schemas.runtime import (
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummary,
    RuntimeFlowSummaryListResponse,
    WorkflowManifestRef,
)


async def _runtime_root_paths_by_task(
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
        raise ValueError("missing runtime root binding for task(s): " + ", ".join(sorted(missing)))
    return runtime_paths


async def _open_dispatches_by_id(
    session: AsyncSession,
    dispatch_ids: tuple[str, ...],
) -> dict[str, DispatchTurnModel]:
    if not dispatch_ids:
        return {}
    dispatches = list(
        await session.scalars(
            select(DispatchTurnModel).where(DispatchTurnModel.dispatch_id.in_(dispatch_ids))
        )
    )
    open_dispatches = {dispatch.dispatch_id: dispatch for dispatch in dispatches}
    missing = set(dispatch_ids).difference(open_dispatches)
    if missing:
        raise ValueError("missing dispatch(es): " + ", ".join(sorted(missing)))
    return open_dispatches


def _foreground_inactivity_reason(dispatch: DispatchTurnModel) -> str:
    if dispatch.control_state == "abort_requested":
        reason = dispatch.control_state_reason or "abort_requested"
        return f"{reason}:inactive_proven"
    if dispatch.accepted_boundary is not None:
        return f"boundary:{dispatch.accepted_boundary}:inactive_proven"
    reason = dispatch.control_state_reason or "foreground_dispatch"
    return f"{reason}:inactive_proven"


async def _fence_foreground_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
) -> DispatchTurnModel:
    await _mark_dispatch_fenced(
        session,
        dispatch=dispatch,
        reason=_foreground_inactivity_reason(dispatch),
    )
    flow.current_open_dispatch_id = None
    if flow.status in {
        FlowStatus.SUCCEEDED.value,
        FlowStatus.BLOCKED.value,
        FlowStatus.CANCELLED.value,
    }:
        await _release_workspace_root_lease(session, task_id=task_id)
    _queue_dispatch_materialization(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
    )
    await session.flush()
    return dispatch


async def _resolve_foreground_dispatch_gate(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
) -> DispatchTurnModel | None:
    if flow.current_open_dispatch_id is None:
        return None
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
    if dispatch is None:
        raise ValueError(f"missing dispatch '{flow.current_open_dispatch_id}'")
    if _dispatch_inactivity_proven(dispatch) and (
        _dispatch_waiting_for_inactivity(dispatch) or dispatch.control_state == "abort_requested"
    ):
        return await _fence_foreground_dispatch(
            session,
            task_id=task_id,
            flow=flow,
            dispatch=dispatch,
        )
    if _dispatch_deadline_expired(dispatch):
        reason = dispatch.control_state_reason or "foreground_dispatch"
        await _mark_dispatch_ambiguous(
            session,
            dispatch=dispatch,
            reason=f"{reason}:timed_out",
        )
        _queue_dispatch_materialization(
            session,
            task_id=task_id,
            dispatch_id=dispatch.dispatch_id,
        )
        raise ValueError("foreground dispatch timed out before inactivity was proven")
    if dispatch.control_state == "abort_requested":
        raise ValueError("current dispatch is still awaiting inactivity proof after abort")
    if dispatch.control_state == "ambiguous":
        raise ValueError("foreground dispatch timed out before inactivity was proven")
    if dispatch.control_state == "fenced":
        flow.current_open_dispatch_id = None
        await session.flush()
        return dispatch
    raise ValueError("current dispatch is still awaiting inactivity proof")


async def runtime_flow_read(session: AsyncSession, task_id: str) -> RuntimeFlowRead:
    state = await current_runtime_state(session, task_id)
    runtime_paths = await _runtime_root_paths_by_task(session, (task_id,))
    return RuntimeFlowRead(
        task_id=state.task.task_id,
        task_title=state.task.title,
        task_summary=state.task.summary,
        workflow_key=state.task.workflow_key,
        status=FlowStatus(state.flow.status),
        active_flow_revision_id=state.flow.active_flow_revision_id or "",
        workflow_manifest_ref=WorkflowManifestRef(
            path=runtime_paths[task_id] / "workflow-manifest.md",
            description="Whole-workflow visible contract for the current task.",
        ),
        current_node_key=state.current_node.node_key,
        active_attempt_id=state.current_attempt.attempt_id,
        updated_at=state.flow.updated_at,
    )


async def list_runtime_flows(
    session: AsyncSession,
    *,
    q: str | None = None,
    cursor: str | None = None,
    status: str = "any",
    limit: int = 50,
    sort: str = "updated_at_desc",
) -> RuntimeFlowSummaryListResponse:
    if status not in {
        "any",
        FlowStatus.PENDING.value,
        FlowStatus.RUNNING.value,
        FlowStatus.BLOCKED.value,
        FlowStatus.PAUSED.value,
        FlowStatus.SUCCEEDED.value,
        FlowStatus.FAILED.value,
        FlowStatus.CANCELLED.value,
    }:
        raise ValueError(f"unknown status filter '{status}'")
    if sort not in {
        "updated_at_desc",
        "updated_at_asc",
        "task_title_asc",
        "task_title_desc",
    }:
        raise ValueError(f"unknown runtime task sort '{sort}'")
    offset = 0
    if cursor is not None:
        try:
            offset = int(cursor)
        except ValueError as exc:
            raise ValueError("cursor must be an integer offset") from exc
        if offset < 0:
            raise ValueError("cursor must be non-negative")

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
        query = query.order_by(FlowModel.updated_at.asc(), TaskModel.task_id.asc())
    elif sort == "task_title_asc":
        query = query.order_by(func.lower(TaskModel.title).asc(), TaskModel.task_id.asc())
    elif sort == "task_title_desc":
        query = query.order_by(func.lower(TaskModel.title).desc(), TaskModel.task_id.asc())
    else:
        query = query.order_by(FlowModel.updated_at.desc(), TaskModel.task_id.asc())

    rows = list((await session.execute(query.offset(offset).limit(limit + 1))).all())
    runtime_paths = await _runtime_root_paths_by_task(
        session,
        tuple(task.task_id for _, task, _ in rows[:limit]),
    )
    open_dispatches = await _open_dispatches_by_id(
        session,
        tuple(
            flow.current_open_dispatch_id
            for flow, _, _ in rows[:limit]
            if flow.current_open_dispatch_id is not None
        ),
    )
    items: list[RuntimeFlowSummary] = []
    for flow, task, active_attempt_id in rows[:limit]:
        open_dispatch = (
            None
            if flow.current_open_dispatch_id is None
            else open_dispatches[flow.current_open_dispatch_id]
        )
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
                    description="Whole-workflow visible contract for the current task.",
                ),
                current_node_key=(
                    open_dispatch.node_key if open_dispatch is not None else flow.current_node_key
                ),
                active_attempt_id=(
                    open_dispatch.attempt_id or active_attempt_id
                    if open_dispatch is not None
                    else active_attempt_id
                ),
                updated_at=flow.updated_at,
            )
        )
    next_cursor = str(offset + limit) if len(rows) > limit else None
    return RuntimeFlowSummaryListResponse(items=tuple(items), next_cursor=next_cursor)


async def continue_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowRead:
    flow = await _flow_by_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise ValueError("stale active flow revision")
    resolved_previous_dispatch = await _resolve_foreground_dispatch_gate(
        session,
        task_id=task_id,
        flow=flow,
    )
    if flow.status in {
        FlowStatus.BLOCKED.value,
        FlowStatus.CANCELLED.value,
        FlowStatus.SUCCEEDED.value,
    }:
        return await runtime_flow_read(session, task_id)
    node: FlowNodeModel | None = None
    assignment: AssignmentModel | None = None
    attempt: AttemptModel | None = None
    resumable_dispatch: DispatchTurnModel | None = None
    previous_dispatch: DispatchTurnModel | None = resolved_previous_dispatch
    if (
        flow.current_open_dispatch_id is None
        and previous_dispatch is not None
        and previous_dispatch.staged_child_assignment_id is not None
    ):
        assignment = await session.get(
            AssignmentModel, previous_dispatch.staged_child_assignment_id
        )
        if assignment is None:
            raise ValueError("staged child assignment is incomplete")
        if assignment.current_attempt_id is None:
            raise ValueError("staged child assignment is incomplete")
        node = await session.get(FlowNodeModel, assignment.flow_node_id)
        if node is None:
            raise ValueError(f"missing flow node '{assignment.flow_node_id}'")
        attempt = await session.get(AttemptModel, assignment.current_attempt_id)
        if attempt is None:
            raise ValueError(f"missing attempt '{assignment.current_attempt_id}'")
    elif flow.current_open_dispatch_id is None and flow.current_node_key is not None:
        node = await _flow_node_by_key(
            session,
            flow.active_flow_revision_id or "",
            flow.current_node_key,
        )
        if node.current_assignment_id is not None:
            assignment = await session.get(AssignmentModel, node.current_assignment_id)
            if assignment is not None and assignment.current_attempt_id is not None:
                attempt = await session.get(AttemptModel, assignment.current_attempt_id)
                if attempt is not None:
                    resumable_dispatch = await _latest_resumable_dispatch_for_attempt(
                        session,
                        task_id=task_id,
                        attempt_id=attempt.attempt_id,
                    )
                    if previous_dispatch is None:
                        previous_dispatch = resumable_dispatch
                    if previous_dispatch is None:
                        previous_dispatch = await _latest_closed_dispatch_for_task(
                            session,
                            task_id=task_id,
                        )
    if flow.status == FlowStatus.PAUSED.value:
        if attempt is not None:
            latest_checkpoint = await _latest_checkpoint_for_attempt(session, attempt)
            if (
                attempt.closed_at is not None
                or attempt.terminal_outcome is not None
                or (
                    latest_checkpoint is not None
                    and latest_checkpoint.checkpoint_kind == CheckpointKind.TERMINAL.value
                )
            ):
                raise ValueError("paused flow cannot continue after a terminal checkpoint")
        flow.status = FlowStatus.RUNNING.value
        flow.updated_at = _now()
        await session.flush()
    if (
        flow.current_open_dispatch_id is None
        and node is not None
        and assignment is not None
        and attempt is not None
    ):
        await _open_dispatch_for_attempt(
            session,
            task_id=task_id,
            node=node,
            assignment=assignment,
            attempt=attempt,
            send_mode=PromptSendMode.FULL_PROMPT,
            previous_dispatch_id=(
                None if previous_dispatch is None else previous_dispatch.dispatch_id
            ),
            staged_child_assignment_id=(
                None
                if previous_dispatch is None
                or previous_dispatch.attempt_id != attempt.attempt_id
                or previous_dispatch.node_key != node.node_key
                else previous_dispatch.staged_child_assignment_id
            ),
        )
    await session.flush()
    return await runtime_flow_read(session, task_id)


async def pause_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowPauseResponse:
    flow = await _flow_by_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise ValueError("stale active flow revision")
    if flow.status in {
        FlowStatus.SUCCEEDED.value,
        FlowStatus.BLOCKED.value,
        FlowStatus.CANCELLED.value,
    }:
        raise ValueError("terminal flow cannot be paused")
    paused_dispatch_id = flow.current_open_dispatch_id
    if paused_dispatch_id is not None:
        dispatch = await session.get(DispatchTurnModel, paused_dispatch_id)
        if dispatch is None:
            raise ValueError(f"missing dispatch '{paused_dispatch_id}'")
        dispatch.control_state = "fenced"
        dispatch.control_state_reason = "paused"
        dispatch.fenced_at = _now()
        dispatch.closed_at = dispatch.closed_at or _now()
        dispatch.status = "closed"
        await _revoke_callback_binding(
            session,
            task_id=task_id,
            dispatch_id=paused_dispatch_id,
        )
        delivery_state = await session.get(DispatchDeliveryStateModel, paused_dispatch_id)
        if delivery_state is not None:
            delivery_state.controller_observation_state = "paused"
            delivery_state.last_controller_terminal_at = _now()
            delivery_state.updated_at = _now()
        flow.current_open_dispatch_id = None
    flow.status = FlowStatus.PAUSED.value
    flow.updated_at = _now()
    await session.flush()
    if paused_dispatch_id is not None:
        _queue_dispatch_materialization(
            session,
            task_id=task_id,
            dispatch_id=paused_dispatch_id,
        )
    return RuntimeFlowPauseResponse(flow=await runtime_flow_read(session, task_id))


async def cancel_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowRead:
    flow = await _flow_by_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise ValueError("stale active flow revision")
    cancelled_dispatch_id = flow.current_open_dispatch_id
    if cancelled_dispatch_id is not None:
        dispatch = await session.get(DispatchTurnModel, cancelled_dispatch_id)
        if dispatch is None:
            raise ValueError(f"missing dispatch '{cancelled_dispatch_id}'")
        if dispatch.control_state == "abort_requested":
            if _dispatch_inactivity_proven(dispatch):
                await _fence_foreground_dispatch(
                    session,
                    task_id=task_id,
                    flow=flow,
                    dispatch=dispatch,
                )
            elif _dispatch_deadline_expired(dispatch):
                await _mark_dispatch_ambiguous(
                    session,
                    dispatch=dispatch,
                    reason="cancel_requested:timed_out",
                )
                _queue_dispatch_materialization(
                    session,
                    task_id=task_id,
                    dispatch_id=cancelled_dispatch_id,
                )
                await session.flush()
                return await runtime_flow_read(session, task_id)
            flow.status = FlowStatus.CANCELLED.value
            flow.updated_at = _now()
            if flow.current_open_dispatch_id is None:
                await _release_workspace_root_lease(session, task_id=task_id)
            await session.flush()
            _queue_dispatch_materialization(
                session,
                task_id=task_id,
                dispatch_id=cancelled_dispatch_id,
            )
            return await runtime_flow_read(session, task_id)
        closed_at = _now()
        dispatch.abort_requested_at = dispatch.abort_requested_at or closed_at
        dispatch.control_state = "abort_requested"
        dispatch.control_state_reason = "cancel_requested"
        dispatch.control_deadline_at = _dispatch_control_deadline(base=closed_at)
        dispatch.closed_at = dispatch.closed_at or closed_at
        dispatch.status = "closed"
        if dispatch.attempt_id is not None:
            attempt = await session.get(AttemptModel, dispatch.attempt_id)
            if attempt is not None and attempt.closed_at is None:
                attempt.closed_at = closed_at
                attempt.status = "cancelled"
        await _revoke_callback_binding(
            session,
            task_id=task_id,
            dispatch_id=cancelled_dispatch_id,
        )
        delivery_state = await session.get(DispatchDeliveryStateModel, cancelled_dispatch_id)
        if delivery_state is not None:
            delivery_state.controller_observation_state = "abort_requested"
            delivery_state.updated_at = closed_at
    flow.status = FlowStatus.CANCELLED.value
    flow.updated_at = _now()
    if flow.current_open_dispatch_id is None:
        await _release_workspace_root_lease(session, task_id=task_id)
    await session.flush()
    if cancelled_dispatch_id is not None:
        _queue_dispatch_materialization(
            session,
            task_id=task_id,
            dispatch_id=cancelled_dispatch_id,
        )
    return await runtime_flow_read(session, task_id)
