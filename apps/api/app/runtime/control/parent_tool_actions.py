from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import DispatchTurnModel, FlowModel
from app.runtime.contracts import NodeKind
from app.runtime.control.assignment.service import call_assign_child
from app.runtime.control.clock import utc_now
from app.runtime.control.failures import illegal_caller_error
from app.runtime.control.flow.service import runtime_flow_read
from app.runtime.control.release.guards import ensure_no_staged_child_assignment
from app.runtime.control.release.preconditions import (
    ensure_release_blocked_preconditions,
    ensure_release_green_preconditions,
)
from app.runtime.effects.cases import stage_structural_outputs
from app.runtime.effects.writes import DeferredRuntimeWrite
from app.runtime.projection.runtime_state import CurrentRuntimeState
from app.runtime.replan import (
    add_child_to_current_flow,
    remove_child_from_current_flow,
    update_child_in_current_flow,
)
from app.runtime.task_root.reads import load_task_root_paths
from app.schemas.runtime import ParentToolSuccess, WorkflowManifestRef
from app.schemas.runtime.parent_tools import (
    AddChildSuccess,
    AddChildToolCall,
    AssignChildToolCall,
    ReleaseBlockedSuccess,
    ReleaseGreenSuccess,
    RemoveChildSuccess,
    RemoveChildToolCall,
    UpdateChildSuccess,
    UpdateChildToolCall,
)


async def workflow_manifest_ref_for_task(
    session: AsyncSession,
    task_id: str,
) -> WorkflowManifestRef:
    return WorkflowManifestRef(
        path=(await load_task_root_paths(session, task_id)).runtime_path / "workflow-manifest.md",
        description="Whole-workflow visible contract for the current task.",
    )


def record_release_precondition(
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


async def load_current_parent_dispatch(
    session: AsyncSession,
    *,
    flow: FlowModel,
) -> DispatchTurnModel:
    dispatch = await session.get(
        DispatchTurnModel,
        flow.current_open_dispatch_id or "",
        options=(raiseload("*"),),
    )
    if dispatch is None:
        from app.runtime.control.failures import illegal_state_error

        raise illegal_state_error("no current open dispatch")
    return dispatch


async def handle_structural_add(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: AddChildToolCall,
    read_after_commit: bool = False,
) -> AddChildSuccess | DeferredRuntimeWrite[AddChildSuccess]:
    ensure_no_staged_child_assignment(dispatch, action_name="add_child")
    target_node_key = await add_child_to_current_flow(
        session,
        task_id,
        state,
        typed_call.payload.child,
    )
    stage_structural_outputs(session, task_id=task_id)

    async def read_after_commit_add() -> AddChildSuccess:
        return AddChildSuccess(
            tool_name="add_child",
            summary=f"Added child node '{target_node_key}'.",
            target_node_key=target_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=await workflow_manifest_ref_for_task(session, task_id),
        )

    if read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=read_after_commit_add)
    return await read_after_commit_add()


async def handle_structural_update(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: UpdateChildToolCall,
    read_after_commit: bool = False,
) -> UpdateChildSuccess | DeferredRuntimeWrite[UpdateChildSuccess]:
    ensure_no_staged_child_assignment(dispatch, action_name="update_child")
    update_payload = typed_call.payload
    await update_child_in_current_flow(
        session,
        task_id,
        state,
        update_payload.child_node_key,
        update_payload.patch,
    )
    stage_structural_outputs(session, task_id=task_id)

    async def read_after_commit_update() -> UpdateChildSuccess:
        return UpdateChildSuccess(
            tool_name="update_child",
            summary=f"Updated child node '{update_payload.child_node_key}'.",
            target_node_key=update_payload.child_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=await workflow_manifest_ref_for_task(session, task_id),
        )

    if read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=read_after_commit_update)
    return await read_after_commit_update()


async def handle_structural_remove(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: RemoveChildToolCall,
    read_after_commit: bool = False,
) -> RemoveChildSuccess | DeferredRuntimeWrite[RemoveChildSuccess]:
    ensure_no_staged_child_assignment(dispatch, action_name="remove_child")
    child_node_key = typed_call.payload.child_node_key
    await remove_child_from_current_flow(session, task_id, state, child_node_key)
    stage_structural_outputs(session, task_id=task_id)

    async def read_after_commit_remove() -> RemoveChildSuccess:
        return RemoveChildSuccess(
            tool_name="remove_child",
            summary=f"Removed child node '{child_node_key}'.",
            target_node_key=child_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=await workflow_manifest_ref_for_task(session, task_id),
        )

    if read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=read_after_commit_remove)
    return await read_after_commit_remove()


async def handle_release_green(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    flow: FlowModel,
    read_after_commit: bool = False,
) -> ReleaseGreenSuccess | DeferredRuntimeWrite[ReleaseGreenSuccess]:
    ensure_no_staged_child_assignment(dispatch, action_name="release_green")
    await ensure_release_green_preconditions(
        session,
        task_id=task_id,
        flow_revision_id=flow.active_flow_revision_id or "",
        current_node_key=state.current_node.node_key,
        current_assignment=state.current_assignment,
    )
    record_release_precondition(
        dispatch,
        kind="release_green",
        flow=flow,
        assignment_id=state.current_assignment.assignment_id,
    )
    await session.flush()

    async def read_after_commit_green() -> ReleaseGreenSuccess:
        return ReleaseGreenSuccess(
            tool_name="release_green",
            summary="Current assignment is marked green-release-ready.",
            target_node_key=state.current_node.node_key,
            flow=await runtime_flow_read(session, task_id),
        )

    if read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=read_after_commit_green)
    return await read_after_commit_green()


async def handle_release_blocked(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    flow: FlowModel,
    read_after_commit: bool = False,
) -> ReleaseBlockedSuccess | DeferredRuntimeWrite[ReleaseBlockedSuccess]:
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
    record_release_precondition(
        dispatch,
        kind="release_blocked",
        flow=flow,
        assignment_id=state.current_assignment.assignment_id,
    )
    await session.flush()

    async def read_after_commit_blocked() -> ReleaseBlockedSuccess:
        return ReleaseBlockedSuccess(
            tool_name="release_blocked",
            summary="Current root assignment is marked blocked-release-ready.",
            target_node_key=state.current_node.node_key,
            flow=await runtime_flow_read(session, task_id),
        )

    if read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=read_after_commit_blocked)
    return await read_after_commit_blocked()


async def handle_assign_child(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: AssignChildToolCall,
    read_after_commit: bool,
) -> ParentToolSuccess | DeferredRuntimeWrite[ParentToolSuccess]:
    return await call_assign_child(
        session,
        task_id,
        state=state,
        dispatch=dispatch,
        typed_call=typed_call,
        read_after_commit=read_after_commit,
    )


__all__ = [
    "handle_assign_child",
    "handle_release_blocked",
    "handle_release_green",
    "handle_structural_add",
    "handle_structural_remove",
    "handle_structural_update",
    "load_current_parent_dispatch",
]
