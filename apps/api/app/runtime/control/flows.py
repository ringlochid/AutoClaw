from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AttemptModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
)
from app.runtime.contracts import FlowStatus, PromptSendMode
from app.runtime.control.callbacks import revoke_callback_binding
from app.runtime.control.clock import dispatch_control_deadline, utc_now
from app.runtime.control.dispatch_control import (
    dispatch_deadline_expired,
    dispatch_inactivity_proven,
    dispatch_waiting_for_inactivity,
    fence_foreground_dispatch,
    mark_dispatch_ambiguous,
    open_dispatch_for_attempt,
    resolve_foreground_dispatch_gate,
)
from app.runtime.control.flow_listing import (
    RUNTIME_FLOW_LIST_SORTS,
    RUNTIME_FLOW_LIST_STATUSES,
    WORKFLOW_MANIFEST_REF_DESCRIPTION,
    parse_runtime_flow_cursor,
    runtime_flow_summary_page,
    runtime_root_paths_by_task,
)
from app.runtime.control.flow_queries import require_flow_for_task
from app.runtime.control.flow_resume import (
    ensure_flow_resumeable,
    resolve_flow_resume_target,
)
from app.runtime.control.surfaces import queue_dispatch_materialization
from app.runtime.control.workspace_leases import release_workspace_root_lease
from app.runtime.projection import current_runtime_state
from app.schemas.runtime import (
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummaryListResponse,
    WorkflowManifestRef,
)


async def runtime_flow_read(session: AsyncSession, task_id: str) -> RuntimeFlowRead:
    state = await current_runtime_state(session, task_id)
    runtime_paths = await runtime_root_paths_by_task(session, (task_id,))
    return RuntimeFlowRead(
        task_id=state.task.task_id,
        task_title=state.task.title,
        task_summary=state.task.summary,
        workflow_key=state.task.workflow_key,
        status=FlowStatus(state.flow.status),
        active_flow_revision_id=state.flow.active_flow_revision_id or "",
        workflow_manifest_ref=WorkflowManifestRef(
            path=runtime_paths[task_id] / "workflow-manifest.md",
            description=WORKFLOW_MANIFEST_REF_DESCRIPTION,
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
    if status not in RUNTIME_FLOW_LIST_STATUSES:
        raise ValueError(f"unknown status filter '{status}'")
    if sort not in RUNTIME_FLOW_LIST_SORTS:
        raise ValueError(f"unknown runtime task sort '{sort}'")
    return await runtime_flow_summary_page(
        session,
        q=q,
        status=status,
        sort=sort,
        offset=parse_runtime_flow_cursor(cursor),
        limit=limit,
    )


async def continue_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowRead:
    flow = await require_flow_for_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise ValueError("stale active flow revision")
    resolved_previous_dispatch = await resolve_foreground_dispatch_gate(
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
    resume_target = await resolve_flow_resume_target(
        session,
        flow=flow,
        previous_dispatch=resolved_previous_dispatch,
    )
    if flow.status == FlowStatus.PAUSED.value:
        await ensure_flow_resumeable(session, resume_target.attempt)
        flow.status = FlowStatus.RUNNING.value
        flow.updated_at = utc_now()
        await session.flush()
    dispatch_open_inputs = resume_target.dispatch_open_inputs()
    if flow.current_open_dispatch_id is None and dispatch_open_inputs is not None:
        node, assignment, attempt, previous_dispatch_id, staged_child_assignment_id = (
            dispatch_open_inputs
        )
        await open_dispatch_for_attempt(
            session,
            task_id=task_id,
            node=node,
            assignment=assignment,
            attempt=attempt,
            send_mode=PromptSendMode.FULL_PROMPT,
            previous_dispatch_id=previous_dispatch_id,
            staged_child_assignment_id=staged_child_assignment_id,
        )
    await session.flush()
    return await runtime_flow_read(session, task_id)


async def pause_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowPauseResponse:
    flow = await require_flow_for_task(session, task_id)
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
        paused_at = utc_now()
        delivery_state = await session.get(DispatchDeliveryStateModel, paused_dispatch_id)
        if dispatch_inactivity_proven(dispatch) and (
            dispatch_waiting_for_inactivity(dispatch) or dispatch.control_state == "abort_requested"
        ):
            await fence_foreground_dispatch(
                session,
                task_id=task_id,
                flow=flow,
                dispatch=dispatch,
            )
        elif dispatch_deadline_expired(dispatch):
            reason = dispatch.control_state_reason or "pause_requested"
            await mark_dispatch_ambiguous(
                session,
                dispatch=dispatch,
                reason=f"{reason}:timed_out",
            )
        elif dispatch.control_state == "fenced":
            flow.current_open_dispatch_id = None
        else:
            dispatch.closed_at = dispatch.closed_at or paused_at
            dispatch.status = "closed"
            if dispatch.accepted_boundary is None:
                dispatch.abort_requested_at = dispatch.abort_requested_at or paused_at
                dispatch.control_state = "abort_requested"
                dispatch.control_state_reason = "pause_requested"
                dispatch.control_deadline_at = (
                    dispatch.control_deadline_at or dispatch_control_deadline(base=paused_at)
                )
            await revoke_callback_binding(
                session,
                task_id=task_id,
                dispatch_id=paused_dispatch_id,
            )
            if delivery_state is not None:
                delivery_state.controller_observation_state = dispatch.control_state
                delivery_state.updated_at = paused_at
    flow.status = FlowStatus.PAUSED.value
    flow.updated_at = utc_now()
    await session.flush()
    if paused_dispatch_id is not None:
        queue_dispatch_materialization(
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
    flow = await require_flow_for_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise ValueError("stale active flow revision")
    cancelled_dispatch_id = flow.current_open_dispatch_id
    if cancelled_dispatch_id is not None:
        dispatch = await session.get(DispatchTurnModel, cancelled_dispatch_id)
        if dispatch is None:
            raise ValueError(f"missing dispatch '{cancelled_dispatch_id}'")
        if dispatch.control_state == "abort_requested":
            if dispatch_inactivity_proven(dispatch):
                await fence_foreground_dispatch(
                    session,
                    task_id=task_id,
                    flow=flow,
                    dispatch=dispatch,
                )
            elif dispatch_deadline_expired(dispatch):
                await mark_dispatch_ambiguous(
                    session,
                    dispatch=dispatch,
                    reason="cancel_requested:timed_out",
                )
                queue_dispatch_materialization(
                    session,
                    task_id=task_id,
                    dispatch_id=cancelled_dispatch_id,
                )
                await session.flush()
                return await runtime_flow_read(session, task_id)
            flow.status = FlowStatus.CANCELLED.value
            flow.updated_at = utc_now()
            if flow.current_open_dispatch_id is None:
                await release_workspace_root_lease(session, task_id=task_id)
            await session.flush()
            queue_dispatch_materialization(
                session,
                task_id=task_id,
                dispatch_id=cancelled_dispatch_id,
            )
            return await runtime_flow_read(session, task_id)
        closed_at = utc_now()
        dispatch.abort_requested_at = dispatch.abort_requested_at or closed_at
        dispatch.control_state = "abort_requested"
        dispatch.control_state_reason = "cancel_requested"
        dispatch.control_deadline_at = dispatch_control_deadline(base=closed_at)
        dispatch.closed_at = dispatch.closed_at or closed_at
        dispatch.status = "closed"
        if dispatch.attempt_id is not None:
            attempt = await session.get(AttemptModel, dispatch.attempt_id)
            if attempt is not None and attempt.closed_at is None:
                attempt.closed_at = closed_at
                attempt.status = "cancelled"
        await revoke_callback_binding(
            session,
            task_id=task_id,
            dispatch_id=cancelled_dispatch_id,
        )
        delivery_state = await session.get(DispatchDeliveryStateModel, cancelled_dispatch_id)
        if delivery_state is not None:
            delivery_state.controller_observation_state = "abort_requested"
            delivery_state.updated_at = closed_at
    flow.status = FlowStatus.CANCELLED.value
    flow.updated_at = utc_now()
    if flow.current_open_dispatch_id is None:
        await release_workspace_root_lease(session, task_id=task_id)
    await session.flush()
    if cancelled_dispatch_id is not None:
        queue_dispatch_materialization(
            session,
            task_id=task_id,
            dispatch_id=cancelled_dispatch_id,
        )
    return await runtime_flow_read(session, task_id)
