from __future__ import annotations

from typing import Literal, cast, overload

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DispatchTurnModel
from app.runtime.contracts import NodeKind, ParentRootToolName
from app.runtime.control.failures import (
    illegal_caller_error,
    invalid_request_shape_error,
    stale_flow_revision_error,
)
from app.runtime.control.parent_tool_actions import (
    handle_assign_child,
    handle_release_blocked,
    handle_release_green,
    handle_structural_add,
    handle_structural_remove,
    handle_structural_update,
    load_current_parent_dispatch,
)
from app.runtime.control.release.guards import (
    ensure_no_terminal_release_basis,
)
from app.runtime.effects.writes import DeferredRuntimeWrite
from app.runtime.projection.runtime_state import CurrentRuntimeState, current_runtime_state
from app.schemas.runtime import ParentToolCall, ParentToolSuccess
from app.schemas.runtime.parent_tools import (
    AddChildToolCall,
    AssignChildToolCall,
    ParentToolCallVariant,
    ReleaseBlockedToolCall,
    ReleaseGreenToolCall,
    RemoveChildToolCall,
    UpdateChildToolCall,
)


def validate_parent_tool_call(
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
) -> ParentToolCallVariant:
    if payload.tool_name != tool_name:
        raise invalid_request_shape_error("tool_name path/body mismatch")

    typed_call = payload.as_variant()
    if tool_name == ParentRootToolName.ASSIGN_CHILD:
        if not isinstance(typed_call, AssignChildToolCall):
            raise invalid_request_shape_error("assign_child requires AssignChildPayload")
        return typed_call
    if tool_name == ParentRootToolName.ADD_CHILD:
        if not isinstance(typed_call, AddChildToolCall):
            raise invalid_request_shape_error("add_child requires AddChildPayload")
        return typed_call
    if tool_name == ParentRootToolName.UPDATE_CHILD:
        if not isinstance(typed_call, UpdateChildToolCall):
            raise invalid_request_shape_error("update_child requires UpdateChildPayload")
        return typed_call
    if tool_name == ParentRootToolName.REMOVE_CHILD:
        if not isinstance(typed_call, RemoveChildToolCall):
            raise invalid_request_shape_error("remove_child requires RemoveChildPayload")
        return typed_call
    if tool_name == ParentRootToolName.RELEASE_GREEN:
        if not isinstance(typed_call, ReleaseGreenToolCall):
            raise invalid_request_shape_error("release_green requires ReleaseGreenPayload")
        return typed_call
    if not isinstance(typed_call, ReleaseBlockedToolCall):
        raise invalid_request_shape_error("release_blocked requires ReleaseBlockedPayload")
    return typed_call


@overload
async def call_parent_tool(
    session: AsyncSession,
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
    *,
    read_after_commit: Literal[False] = False,
    state: CurrentRuntimeState | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> ParentToolSuccess: ...


@overload
async def call_parent_tool(
    session: AsyncSession,
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
    *,
    read_after_commit: Literal[True],
    state: CurrentRuntimeState | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> DeferredRuntimeWrite[ParentToolSuccess]: ...


async def call_parent_tool(
    session: AsyncSession,
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
    *,
    read_after_commit: bool = False,
    state: CurrentRuntimeState | None = None,
    dispatch: DispatchTurnModel | None = None,
) -> ParentToolSuccess | DeferredRuntimeWrite[ParentToolSuccess]:
    typed_call = validate_parent_tool_call(tool_name, payload)
    state = state or await current_runtime_state(session, task_id)
    if state.current_node.structural_kind == NodeKind.WORKER.value:
        raise illegal_caller_error("worker nodes cannot call parent/root tools")
    if payload.expected_structural_revision_id is not None and (
        payload.expected_structural_revision_id != state.flow.active_flow_revision_id
    ):
        raise stale_flow_revision_error("stale structural revision")
    flow = state.flow
    if dispatch is None:
        dispatch = await load_current_parent_dispatch(session, flow=flow)
    ensure_no_terminal_release_basis(dispatch, action_name=tool_name.value)
    if tool_name == ParentRootToolName.ASSIGN_CHILD:
        return await handle_assign_child(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            typed_call=cast(AssignChildToolCall, typed_call),
            read_after_commit=read_after_commit,
        )
    if tool_name == ParentRootToolName.ADD_CHILD:
        return await handle_structural_add(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            typed_call=cast(AddChildToolCall, typed_call),
            read_after_commit=read_after_commit,
        )
    if tool_name == ParentRootToolName.UPDATE_CHILD:
        return await handle_structural_update(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            typed_call=cast(UpdateChildToolCall, typed_call),
            read_after_commit=read_after_commit,
        )
    if tool_name == ParentRootToolName.REMOVE_CHILD:
        return await handle_structural_remove(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            typed_call=cast(RemoveChildToolCall, typed_call),
            read_after_commit=read_after_commit,
        )
    if tool_name == ParentRootToolName.RELEASE_GREEN:
        return await handle_release_green(
            session,
            task_id,
            state=state,
            dispatch=dispatch,
            flow=flow,
            read_after_commit=read_after_commit,
        )
    return await handle_release_blocked(
        session,
        task_id,
        state=state,
        dispatch=dispatch,
        flow=flow,
        read_after_commit=read_after_commit,
    )
