from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchTurnModel, FlowModel
from app.runtime.contracts import NodeKind, ParentRootToolName
from app.runtime.control.assignment.service import call_assign_child
from app.runtime.control.clock import utc_now
from app.runtime.control.failures import (
    illegal_caller_error,
    illegal_state_error,
    invalid_request_shape_error,
    stale_flow_revision_error,
)
from app.runtime.control.flow.service import runtime_flow_read
from app.runtime.control.release.guards import (
    ensure_no_staged_child_assignment,
    ensure_no_terminal_release_basis,
)
from app.runtime.control.release.preconditions import (
    ensure_release_blocked_preconditions,
    ensure_release_green_preconditions,
)
from app.runtime.effects.queue import queue_manifest_materialization
from app.runtime.projection import CurrentRuntimeState, current_runtime_state, load_task_root_paths
from app.runtime.replan import (
    add_child_to_current_flow,
    remove_child_from_current_flow,
    update_child_in_current_flow,
)
from app.schemas.runtime import ParentToolCall, ParentToolSuccess, WorkflowManifestRef
from app.schemas.runtime.parent_tools import (
    AddChildSuccess,
    AddChildToolCall,
    AssignChildToolCall,
    ReleaseBlockedSuccess,
    ReleaseBlockedToolCall,
    ReleaseGreenSuccess,
    ReleaseGreenToolCall,
    RemoveChildSuccess,
    RemoveChildToolCall,
    UpdateChildSuccess,
    UpdateChildToolCall,
)


async def _workflow_manifest_ref(
    session: AsyncSession,
    task_id: str,
) -> WorkflowManifestRef:
    return WorkflowManifestRef(
        path=(await load_task_root_paths(session, task_id)).runtime_path / "workflow-manifest.md",
        description="Whole-workflow visible contract for the current task.",
    )


def _record_release_precondition(
    dispatch: DispatchTurnModel,
    *,
    kind: str,
    flow: FlowModel,
    assignment_id: str,
) -> None:
    dispatch.release_precondition_kind = kind
    dispatch.release_precondition_flow_revision_id = flow.active_flow_revision_id
    dispatch.release_precondition_assignment_id = assignment_id
    dispatch.release_precondition_recorded_at = utc_now()


async def _handle_structural_add(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: AddChildToolCall,
) -> AddChildSuccess:
    ensure_no_staged_child_assignment(dispatch, action_name="add_child")
    target_node_key = await add_child_to_current_flow(
        session,
        task_id,
        state,
        typed_call.payload.child,
    )
    queue_manifest_materialization(session, task_id=task_id)
    return AddChildSuccess(
        tool_name="add_child",
        summary=f"Added child node '{target_node_key}'.",
        target_node_key=target_node_key,
        flow=await runtime_flow_read(session, task_id),
        workflow_manifest_ref=await _workflow_manifest_ref(session, task_id),
    )


async def _handle_structural_update(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: UpdateChildToolCall,
) -> UpdateChildSuccess:
    ensure_no_staged_child_assignment(dispatch, action_name="update_child")
    update_payload = typed_call.payload
    await update_child_in_current_flow(
        session,
        task_id,
        state,
        update_payload.child_node_key,
        update_payload.patch,
    )
    queue_manifest_materialization(session, task_id=task_id)
    return UpdateChildSuccess(
        tool_name="update_child",
        summary=f"Updated child node '{update_payload.child_node_key}'.",
        target_node_key=update_payload.child_node_key,
        flow=await runtime_flow_read(session, task_id),
        workflow_manifest_ref=await _workflow_manifest_ref(session, task_id),
    )


async def _handle_structural_remove(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: RemoveChildToolCall,
) -> RemoveChildSuccess:
    ensure_no_staged_child_assignment(dispatch, action_name="remove_child")
    child_node_key = typed_call.payload.child_node_key
    await remove_child_from_current_flow(session, task_id, state, child_node_key)
    queue_manifest_materialization(session, task_id=task_id)
    return RemoveChildSuccess(
        tool_name="remove_child",
        summary=f"Removed child node '{child_node_key}'.",
        target_node_key=child_node_key,
        flow=await runtime_flow_read(session, task_id),
        workflow_manifest_ref=await _workflow_manifest_ref(session, task_id),
    )


async def _handle_release_green(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    flow: FlowModel,
) -> ReleaseGreenSuccess:
    ensure_no_staged_child_assignment(dispatch, action_name="release_green")
    await ensure_release_green_preconditions(
        session,
        task_id=task_id,
        flow_revision_id=flow.active_flow_revision_id or "",
        current_node_key=state.current_node.node_key,
        current_assignment=state.current_assignment,
    )
    _record_release_precondition(
        dispatch,
        kind="release_green",
        flow=flow,
        assignment_id=state.current_assignment.assignment_id,
    )
    await session.flush()
    return ReleaseGreenSuccess(
        tool_name="release_green",
        summary="Current assignment is marked green-release-ready.",
        target_node_key=state.current_node.node_key,
        flow=await runtime_flow_read(session, task_id),
    )


async def _handle_release_blocked(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    flow: FlowModel,
) -> ReleaseBlockedSuccess:
    if state.current_node.structural_kind != NodeKind.ROOT.value:
        raise illegal_caller_error("release_blocked is root-only")
    ensure_no_staged_child_assignment(dispatch, action_name="release_blocked")
    await ensure_release_blocked_preconditions(
        session,
        task_id=task_id,
        flow_revision_id=flow.active_flow_revision_id or "",
        current_node_key=state.current_node.node_key,
        current_assignment=state.current_assignment,
    )
    _record_release_precondition(
        dispatch,
        kind="release_blocked",
        flow=flow,
        assignment_id=state.current_assignment.assignment_id,
    )
    await session.flush()
    return ReleaseBlockedSuccess(
        tool_name="release_blocked",
        summary="Current root assignment is marked blocked-release-ready.",
        target_node_key=state.current_node.node_key,
        flow=await runtime_flow_read(session, task_id),
    )


async def call_parent_tool(
    session: AsyncSession,
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
) -> ParentToolSuccess:
    typed_call = payload.as_variant()
    state = await current_runtime_state(session, task_id)
    if state.current_node.structural_kind == NodeKind.WORKER.value:
        raise illegal_caller_error("worker nodes cannot call parent/root tools")
    if payload.expected_structural_revision_id is not None and (
        payload.expected_structural_revision_id != state.flow.active_flow_revision_id
    ):
        raise stale_flow_revision_error("stale structural revision")
    flow = state.flow
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id or "")
    if dispatch is None:
        raise illegal_state_error("no current open dispatch")
    ensure_no_terminal_release_basis(dispatch, action_name=tool_name.value)

    if tool_name == ParentRootToolName.ASSIGN_CHILD:
        if not isinstance(typed_call, AssignChildToolCall):
            raise invalid_request_shape_error("assign_child requires AssignChildPayload")
        return await call_assign_child(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            typed_call=typed_call,
        )
    if tool_name == ParentRootToolName.ADD_CHILD:
        if not isinstance(typed_call, AddChildToolCall):
            raise invalid_request_shape_error("add_child requires AddChildPayload")
        return await _handle_structural_add(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            typed_call=typed_call,
        )
    if tool_name == ParentRootToolName.UPDATE_CHILD:
        if not isinstance(typed_call, UpdateChildToolCall):
            raise invalid_request_shape_error("update_child requires UpdateChildPayload")
        return await _handle_structural_update(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            typed_call=typed_call,
        )
    if tool_name == ParentRootToolName.REMOVE_CHILD:
        if not isinstance(typed_call, RemoveChildToolCall):
            raise invalid_request_shape_error("remove_child requires RemoveChildPayload")
        return await _handle_structural_remove(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            typed_call=typed_call,
        )
    if tool_name == ParentRootToolName.RELEASE_GREEN:
        if not isinstance(typed_call, ReleaseGreenToolCall):
            raise invalid_request_shape_error("release_green requires ReleaseGreenPayload")
        return await _handle_release_green(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            flow=flow,
        )
    if not isinstance(typed_call, ReleaseBlockedToolCall):
        raise invalid_request_shape_error("release_blocked requires ReleaseBlockedPayload")
    return await _handle_release_blocked(
        session,
        task_id,
        state=state,
        dispatch=dispatch,
        flow=flow,
    )
