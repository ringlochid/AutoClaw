from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from autoclaw.persistence.models import DispatchTurnModel, FlowModel
from autoclaw.runtime.assignment.service import call_assign_child
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import NodeKind, ParentToolSuccess, WorkflowManifestRef
from autoclaw.runtime.contracts.parent_tools import (
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
from autoclaw.runtime.errors import illegal_caller_error
from autoclaw.runtime.flow.service import runtime_flow_read
from autoclaw.runtime.post_commit.cases import stage_structural_outputs
from autoclaw.runtime.post_commit.writes import DeferredRuntimeWrite
from autoclaw.runtime.projection.runtime_state import CurrentRuntimeState
from autoclaw.runtime.release.guards import ensure_no_staged_child_assignment
from autoclaw.runtime.release.preconditions import (
    ensure_release_blocked_preconditions,
    ensure_release_green_preconditions,
)
from autoclaw.runtime.replan import (
    add_child_to_current_flow,
    remove_child_from_current_flow,
    update_child_in_current_flow,
)
from autoclaw.runtime.task_root.reads import load_task_root_paths


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
        from autoclaw.runtime.errors import illegal_state_error

        raise illegal_state_error("no current open dispatch")
    return dispatch


async def perform_structural_add(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: AddChildToolCall,
    should_read_after_commit: bool = False,
) -> AddChildSuccess | DeferredRuntimeWrite[AddChildSuccess]:
    ensure_no_staged_child_assignment(dispatch, action_name="add_child")
    target_node_key = await add_child_to_current_flow(
        session,
        task_id,
        state,
        typed_call.payload.child,
    )
    stage_structural_outputs(session, task_id=task_id)

    async def should_read_after_commit_add() -> AddChildSuccess:
        return AddChildSuccess(
            tool_name="add_child",
            summary=f"Added workflow node '{target_node_key}'.",
            target_node_key=target_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=await _workflow_manifest_ref_for_task(session, task_id),
        )

    if should_read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=should_read_after_commit_add)
    return await should_read_after_commit_add()


async def perform_structural_update(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: UpdateChildToolCall,
    should_read_after_commit: bool = False,
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

    async def should_read_after_commit_update() -> UpdateChildSuccess:
        return UpdateChildSuccess(
            tool_name="update_child",
            summary=f"Updated workflow node '{update_payload.child_node_key}'.",
            target_node_key=update_payload.child_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=await _workflow_manifest_ref_for_task(session, task_id),
        )

    if should_read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=should_read_after_commit_update)
    return await should_read_after_commit_update()


async def perform_structural_remove(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: RemoveChildToolCall,
    should_read_after_commit: bool = False,
) -> RemoveChildSuccess | DeferredRuntimeWrite[RemoveChildSuccess]:
    ensure_no_staged_child_assignment(dispatch, action_name="remove_child")
    child_node_key = typed_call.payload.child_node_key
    await remove_child_from_current_flow(session, task_id, state, child_node_key)
    stage_structural_outputs(session, task_id=task_id)

    async def should_read_after_commit_remove() -> RemoveChildSuccess:
        return RemoveChildSuccess(
            tool_name="remove_child",
            summary=f"Removed workflow node '{child_node_key}'.",
            target_node_key=child_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=await _workflow_manifest_ref_for_task(session, task_id),
        )

    if should_read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=should_read_after_commit_remove)
    return await should_read_after_commit_remove()


async def perform_release_green(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    flow: FlowModel,
    should_read_after_commit: bool = False,
) -> ReleaseGreenSuccess | DeferredRuntimeWrite[ReleaseGreenSuccess]:
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

    async def should_read_after_commit_green() -> ReleaseGreenSuccess:
        return ReleaseGreenSuccess(
            tool_name="release_green",
            summary="Current assignment is marked green-release-ready.",
            target_node_key=state.current_node.node_key,
            flow=await runtime_flow_read(session, task_id),
        )

    if should_read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=should_read_after_commit_green)
    return await should_read_after_commit_green()


async def perform_release_blocked(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    flow: FlowModel,
    should_read_after_commit: bool = False,
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
    _record_release_precondition(
        dispatch,
        kind="release_blocked",
        flow=flow,
        assignment_id=state.current_assignment.assignment_id,
    )
    await session.flush()

    async def should_read_after_commit_blocked() -> ReleaseBlockedSuccess:
        return ReleaseBlockedSuccess(
            tool_name="release_blocked",
            summary="Current root assignment is marked blocked-release-ready.",
            target_node_key=state.current_node.node_key,
            flow=await runtime_flow_read(session, task_id),
        )

    if should_read_after_commit:
        return DeferredRuntimeWrite(read_after_commit=should_read_after_commit_blocked)
    return await should_read_after_commit_blocked()


async def perform_assign_child(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: AssignChildToolCall,
    should_read_after_commit: bool,
) -> ParentToolSuccess | DeferredRuntimeWrite[ParentToolSuccess]:
    return await call_assign_child(
        session,
        task_id,
        state=state,
        dispatch=dispatch,
        typed_call=typed_call,
        should_read_after_commit=should_read_after_commit,
    )


async def _workflow_manifest_ref_for_task(
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


__all__ = [
    "load_current_parent_dispatch",
    "perform_assign_child",
    "perform_release_blocked",
    "perform_release_green",
    "perform_structural_add",
    "perform_structural_remove",
    "perform_structural_update",
]
