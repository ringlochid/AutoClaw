from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchTurnModel
from app.runtime.contracts import NodeKind, ParentRootToolName
from app.runtime.control.assign_child import _call_assign_child
from app.runtime.control.flows import runtime_flow_read
from app.runtime.control.release import (
    _ensure_release_blocked_preconditions,
    _ensure_release_green_preconditions,
)
from app.runtime.control.support import (
    _ensure_no_staged_child_assignment,
    _ensure_no_terminal_release_basis,
    _now,
    _queue_manifest_materialization,
)
from app.runtime.projection import current_runtime_state, load_task_root_paths
from app.runtime.replan import (
    add_child_to_current_flow,
    remove_child_from_current_flow,
    update_child_in_current_flow,
)
from app.schemas.runtime import (
    ParentToolCall,
    ParentToolSuccess,
    WorkflowManifestRef,
)
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


async def call_parent_tool(
    session: AsyncSession,
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
) -> ParentToolSuccess:
    typed_call = payload.as_variant()
    state = await current_runtime_state(session, task_id)
    if state.current_node.structural_kind == NodeKind.WORKER.value:
        raise ValueError("worker nodes cannot call parent/root tools")
    if payload.expected_structural_revision_id is not None and (
        payload.expected_structural_revision_id != state.flow.active_flow_revision_id
    ):
        raise ValueError("stale structural revision")
    flow = state.flow
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id or "")
    if dispatch is None:
        raise ValueError("no current open dispatch")
    _ensure_no_terminal_release_basis(dispatch, action_name=tool_name.value)
    if tool_name == ParentRootToolName.ASSIGN_CHILD:
        if not isinstance(typed_call, AssignChildToolCall):
            raise ValueError("assign_child requires AssignChildPayload")
        return await _call_assign_child(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            typed_call=typed_call,
        )

    if tool_name == ParentRootToolName.ADD_CHILD:
        if not isinstance(typed_call, AddChildToolCall):
            raise ValueError("add_child requires AddChildPayload")
        add_payload = typed_call.payload
        _ensure_no_staged_child_assignment(dispatch, action_name="add_child")
        target_node_key = await add_child_to_current_flow(
            session, task_id, state, add_payload.child
        )
        _queue_manifest_materialization(session, task_id=task_id)
        return AddChildSuccess(
            tool_name="add_child",
            summary=f"Added child node '{target_node_key}'.",
            target_node_key=target_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=WorkflowManifestRef(
                path=(await load_task_root_paths(session, task_id)).runtime_path
                / "workflow-manifest.md",
                description="Whole-workflow visible contract for the current task.",
            ),
        )
    if tool_name == ParentRootToolName.UPDATE_CHILD:
        if not isinstance(typed_call, UpdateChildToolCall):
            raise ValueError("update_child requires UpdateChildPayload")
        update_payload = typed_call.payload
        _ensure_no_staged_child_assignment(dispatch, action_name="update_child")
        await update_child_in_current_flow(
            session, task_id, state, update_payload.child_node_key, update_payload.patch
        )
        _queue_manifest_materialization(session, task_id=task_id)
        return UpdateChildSuccess(
            tool_name="update_child",
            summary=f"Updated child node '{update_payload.child_node_key}'.",
            target_node_key=update_payload.child_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=WorkflowManifestRef(
                path=(await load_task_root_paths(session, task_id)).runtime_path
                / "workflow-manifest.md",
                description="Whole-workflow visible contract for the current task.",
            ),
        )
    if tool_name == ParentRootToolName.REMOVE_CHILD:
        if not isinstance(typed_call, RemoveChildToolCall):
            raise ValueError("remove_child requires RemoveChildPayload")
        remove_payload = typed_call.payload
        _ensure_no_staged_child_assignment(dispatch, action_name="remove_child")
        await remove_child_from_current_flow(session, task_id, state, remove_payload.child_node_key)
        _queue_manifest_materialization(session, task_id=task_id)
        return RemoveChildSuccess(
            tool_name="remove_child",
            summary=f"Removed child node '{remove_payload.child_node_key}'.",
            target_node_key=remove_payload.child_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=WorkflowManifestRef(
                path=(await load_task_root_paths(session, task_id)).runtime_path
                / "workflow-manifest.md",
                description="Whole-workflow visible contract for the current task.",
            ),
        )
    if tool_name == ParentRootToolName.RELEASE_GREEN:
        if not isinstance(typed_call, ReleaseGreenToolCall):
            raise ValueError("release_green requires ReleaseGreenPayload")
        _ensure_no_staged_child_assignment(dispatch, action_name="release_green")
        await _ensure_release_green_preconditions(
            session,
            task_id=task_id,
            flow_revision_id=flow.active_flow_revision_id or "",
            current_node_key=state.current_node.node_key,
            current_assignment=state.current_assignment,
        )
        dispatch.release_precondition_kind = "release_green"
        dispatch.release_precondition_flow_revision_id = flow.active_flow_revision_id
        dispatch.release_precondition_assignment_id = state.current_assignment.assignment_id
        dispatch.release_precondition_recorded_at = _now()
        await session.flush()
        return ReleaseGreenSuccess(
            tool_name="release_green",
            summary="Current assignment is marked green-release-ready.",
            target_node_key=state.current_node.node_key,
            flow=await runtime_flow_read(session, task_id),
        )
    if not isinstance(typed_call, ReleaseBlockedToolCall):
        raise ValueError("release_blocked requires ReleaseBlockedPayload")
    if state.current_node.structural_kind != NodeKind.ROOT.value:
        raise ValueError("release_blocked is root-only")
    _ensure_no_staged_child_assignment(dispatch, action_name="release_blocked")
    await _ensure_release_blocked_preconditions(
        session,
        task_id=task_id,
        flow_revision_id=flow.active_flow_revision_id or "",
        current_node_key=state.current_node.node_key,
        current_assignment=state.current_assignment,
    )
    dispatch.release_precondition_kind = "release_blocked"
    dispatch.release_precondition_flow_revision_id = flow.active_flow_revision_id
    dispatch.release_precondition_assignment_id = state.current_assignment.assignment_id
    dispatch.release_precondition_recorded_at = _now()
    await session.flush()
    return ReleaseBlockedSuccess(
        tool_name="release_blocked",
        summary="Current root assignment is marked blocked-release-ready.",
        target_node_key=state.current_node.node_key,
        flow=await runtime_flow_read(session, task_id),
    )
