from __future__ import annotations

from typing import Literal, assert_never, cast

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.contracts import DefinitionKind, DefinitionListQuery
from autoclaw.runtime.dispatch.authority import NodeOperationAuthority
from autoclaw.runtime.node_operations.catalog import (
    list_node_operation_descriptors_for_kind,
)
from autoclaw.runtime.node_operations.contracts import (
    AssignmentContextRead,
    AttemptContextRead,
    EffectiveCapabilitySetRead,
    EffectiveValueRead,
    EmptyNodeOperationRequest,
    FileEntryRead,
    GetCurrentContextResponse,
    GetDefinitionRequest,
    HumanRequestCapabilityRead,
    ListFilesRequest,
    ListFilesResponse,
    NodeOperationName,
    ReadFileRequest,
    ReadFileResponse,
    SearchDefinitionsRequest,
    SlotContextRead,
)
from autoclaw.runtime.node_operations.state_legality import (
    read_state_legal_node_operations,
)
from autoclaw.runtime.task_root.file_access import (
    list_logical_directory,
    read_logical_text_file,
)
from autoclaw.runtime.task_root.reads import read_task_root_paths
from autoclaw.runtime.work_plan import (
    SetWorkPlanRequest,
    read_assignment_work_plan,
    set_assignment_work_plan,
)

type CapabilityDecisionValue = Literal["allow", "deny"]
type SlotKind = Literal["artifact", "criteria", "checkpoint", "transient", "workspace"]


async def execute_core_node_operation(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    operation_name: NodeOperationName,
    request: BaseModel,
) -> BaseModel | None:
    if operation_name == NodeOperationName.GET_CURRENT_CONTEXT:
        assert isinstance(request, EmptyNodeOperationRequest)
        return await _get_current_context(session, authority)
    if operation_name == NodeOperationName.LIST_FILES:
        assert isinstance(request, ListFilesRequest)
        return await _list_files(session, authority, request)
    if operation_name == NodeOperationName.READ_FILE:
        assert isinstance(request, ReadFileRequest)
        return await _read_file(session, authority, request)
    if operation_name == NodeOperationName.SET_WORK_PLAN:
        assert isinstance(request, SetWorkPlanRequest)
        return await set_assignment_work_plan(
            session,
            authority=authority,
            request=request,
        )
    if operation_name == NodeOperationName.SEARCH_DEFINITIONS:
        from autoclaw.definitions.registry.definition_catalog import (
            list_policy_definitions,
            list_role_definitions,
        )

        assert isinstance(request, SearchDefinitionsRequest)
        query = DefinitionListQuery(
            q=request.query,
            limit=request.limit,
            cursor=request.cursor,
            sort=request.sort,
            allowed_node_kind=request.allowed_node_kind,
            applies_to=request.applies_to,
        )
        if request.kind == DefinitionKind.ROLE:
            return await list_role_definitions(session, query)
        if request.kind == DefinitionKind.POLICY:
            return await list_policy_definitions(session, query)
        assert_never(request.kind)
    if operation_name == NodeOperationName.GET_DEFINITION:
        from autoclaw.definitions.registry.definition_catalog import get_definition_detail

        assert isinstance(request, GetDefinitionRequest)
        if request.kind == DefinitionKind.ROLE:
            return await get_definition_detail(session, DefinitionKind.ROLE, request.key)
        if request.kind == DefinitionKind.POLICY:
            return await get_definition_detail(session, DefinitionKind.POLICY, request.key)
        assert_never(request.kind)
    return None


async def _get_current_context(
    session: AsyncSession,
    authority: NodeOperationAuthority,
) -> GetCurrentContextResponse:
    plan = await read_assignment_work_plan(session, assignment_id=authority.assignment_id)
    capabilities = authority.capabilities
    state_legal_actions = await read_state_legal_node_operations(session, authority)
    allowed_actions = tuple(
        descriptor.name
        for descriptor in list_node_operation_descriptors_for_kind(authority.node_kind)
        if descriptor.name in state_legal_actions
        and _capability_allows(descriptor.name, capabilities)
    )
    return GetCurrentContextResponse(
        task_id=authority.task_id,
        dispatch_id=authority.dispatch_id,
        assignment=AssignmentContextRead(
            assignment_id=authority.assignment_id,
            node_key=authority.node_key,
            node_kind=authority.node_kind,
            summary=authority.assignment.summary,
            instruction=authority.assignment.instruction,
            criteria=tuple(authority.assignment.criteria_json),
        ),
        attempt=AttemptContextRead(
            attempt_id=authority.attempt_id,
            assignment_id=authority.assignment_id,
            retry_of_attempt_id=authority.attempt.retry_of_attempt_id,
        ),
        trigger={
            "kind": authority.opened_reason,
            "source_dispatch_id": authority.predecessor_dispatch_id,
        },
        plan=plan,
        capabilities=EffectiveCapabilitySetRead(
            dispatch_id=authority.dispatch_id,
            provider_native_access=EffectiveValueRead(
                effective=capabilities.provider_native_access,
                source=capabilities.provider_native_access_source,
            ),
            network_access=EffectiveValueRead(
                effective=capabilities.network_access,
                source=capabilities.network_access_source,
            ),
            human_request=HumanRequestCapabilityRead(
                direction=cast(CapabilityDecisionValue, capabilities.human_direction),
                approval=cast(CapabilityDecisionValue, capabilities.human_approval),
                input=cast(CapabilityDecisionValue, capabilities.human_input),
                review=cast(CapabilityDecisionValue, capabilities.human_review),
            ),
            command_run=cast(CapabilityDecisionValue, capabilities.command_run),
        ),
        allowed_actions=allowed_actions,
        consume_slots=_slot_reads(authority.assignment.consumes_json, default_kind="artifact"),
        produce_slots=_slot_reads(authority.assignment.produces_json, default_kind="artifact"),
    )


async def _list_files(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    request: ListFilesRequest,
) -> ListFilesResponse:
    paths = await read_task_root_paths(session, authority.task_id)
    directory, entries = list_logical_directory(paths, request.directory)
    return ListFilesResponse(
        directory=directory,
        entries=tuple(
            FileEntryRead(name=name, path=path, kind=kind, size_bytes=size)
            for name, path, kind, size in entries
        ),
    )


async def _read_file(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    request: ReadFileRequest,
) -> ReadFileResponse:
    paths = await read_task_root_paths(session, authority.task_id)
    path, content, line_count, has_more, next_line = read_logical_text_file(
        paths,
        request.path,
        start_line=request.start_line,
        max_lines=request.max_lines,
    )
    return ReadFileResponse(
        path=path,
        start_line=request.start_line,
        max_lines=request.max_lines,
        content=content,
        lines_returned=line_count,
        has_more=has_more,
        next_start_line=next_line,
    )


def _slot_reads(
    values: list[dict[str, object]],
    *,
    default_kind: str,
) -> tuple[SlotContextRead, ...]:
    result: list[SlotContextRead] = []
    for value in values:
        slot = value.get("slot")
        if not isinstance(slot, str) or not slot.strip():
            continue
        description = value.get("description")
        kind = value.get("kind", default_kind)
        if kind not in {"artifact", "criteria", "checkpoint", "transient", "workspace"}:
            kind = default_kind
        path = value.get("path")
        version = value.get("version")
        result.append(
            SlotContextRead(
                slot=slot,
                kind=cast(SlotKind, kind),
                description=(
                    description if isinstance(description, str) and description.strip() else slot
                ),
                path=path if isinstance(path, str) and path.strip() else None,
                version=version if isinstance(version, int) and version >= 1 else None,
            )
        )
    return tuple(result)


def _capability_allows(operation_name: NodeOperationName, capabilities: object) -> bool:
    if operation_name == NodeOperationName.START_COMMAND_RUN:
        return getattr(capabilities, "command_run", "deny") == "allow"
    if operation_name == NodeOperationName.OPEN_HUMAN_REQUEST:
        return any(
            getattr(capabilities, field_name, "deny") == "allow"
            for field_name in ("human_direction", "human_approval", "human_input", "human_review")
        )
    return True


__all__ = ["execute_core_node_operation"]
