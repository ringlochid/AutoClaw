from __future__ import annotations

from typing import Any, Literal

from app.config import get_settings
from app.file_entrypoints import (
    definition_upload_request_from_path,
    task_start_request_from_path,
)
from app.registry.definition_catalog import (
    get_definition_detail,
    list_policy_definitions,
    list_role_definitions,
    list_workflow_definitions,
    upload_definition,
)
from app.registry.definition_history import get_definition_history
from app.registry.task_start import start_task_from_definition_service
from app.schemas.definitions import (
    DefinitionHistorySort,
    DefinitionKind,
    DefinitionListQuery,
    DefinitionListSort,
    DefinitionRevisionDetailResponse,
    DefinitionRevisionHistoryQuery,
    DefinitionRevisionHistoryResponse,
    DefinitionSummaryListResponse,
)
from app.schemas.runtime import TaskStartResponse
from mcp.server.fastmcp import FastMCP

from autoclaw.openclaw.common import (
    run_read_operation,
    run_runtime_write_operation_and_wait,
    run_session_write_operation,
)
from autoclaw.openclaw.tool_teaching import (
    AUDIT_ONLY_NOTE,
    DISCOVER_CANDIDATES_NOTE,
    INSPECT_CURRENT_REVISION_NOTE,
    INSPECT_IF_UNSURE_NOTE,
    LOCAL_FILE_PATH_NOTE,
    REAL_RUNTIME_EFFECTS_NOTE,
    RUNTIME_STATE_WARNING,
    mutating_tool_teaching,
    read_only_tool_teaching,
)

SEARCH_DEFINITIONS_TEACHING = read_only_tool_teaching(
    name="search_definitions",
    summary="Search current controller-owned role, policy, or workflow definitions.",
    details=(DISCOVER_CANDIDATES_NOTE,),
)
GET_DEFINITION_TEACHING = read_only_tool_teaching(
    name="get_definition",
    summary="Inspect one current definition revision.",
    details=(INSPECT_CURRENT_REVISION_NOTE,),
)
LIST_DEFINITION_VERSIONS_TEACHING = read_only_tool_teaching(
    name="list_definition_versions",
    summary="Inspect definition revision history.",
    details=(AUDIT_ONLY_NOTE,),
)
UPLOAD_DEFINITION_TEACHING = mutating_tool_teaching(
    name="upload_definition",
    summary="Load one definition file and create or update controller-owned definition truth.",
    details=(LOCAL_FILE_PATH_NOTE, RUNTIME_STATE_WARNING, INSPECT_IF_UNSURE_NOTE),
)
START_TASK_TEACHING = mutating_tool_teaching(
    name="start_task",
    summary="Load one task-compose file and create and start a real task.",
    details=(
        LOCAL_FILE_PATH_NOTE,
        RUNTIME_STATE_WARNING,
        REAL_RUNTIME_EFFECTS_NOTE,
        "This is not a dry run.",
    ),
)


def register_definition_tools(server: FastMCP) -> None:
    @server.tool(
        name="search_definitions",
        title=SEARCH_DEFINITIONS_TEACHING.title,
        description=SEARCH_DEFINITIONS_TEACHING.description,
        annotations=SEARCH_DEFINITIONS_TEACHING.annotations,
    )
    async def search_definitions(
        kind: DefinitionKind,
        query: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        sort: DefinitionListSort = DefinitionListSort.UPDATED_AT_DESC,
        allowed_node_kind: Literal["root", "parent", "worker"] | None = None,
        applies_to: Literal["root", "parent", "worker"] | None = None,
    ) -> DefinitionSummaryListResponse:
        filters = DefinitionListQuery(
            q=query,
            limit=limit,
            cursor=cursor,
            sort=sort,
            allowed_node_kind=allowed_node_kind,
            applies_to=applies_to,
        )
        return await run_read_operation(
            lambda session: _search_definitions(
                session,
                kind=kind,
                filters=filters,
            )
        )

    @server.tool(
        name="get_definition",
        title=GET_DEFINITION_TEACHING.title,
        description=GET_DEFINITION_TEACHING.description,
        annotations=GET_DEFINITION_TEACHING.annotations,
    )
    async def get_definition(
        kind: DefinitionKind,
        key: str,
    ) -> DefinitionRevisionDetailResponse:
        return await run_read_operation(lambda session: get_definition_detail(session, kind, key))

    @server.tool(
        name="list_definition_versions",
        title=LIST_DEFINITION_VERSIONS_TEACHING.title,
        description=LIST_DEFINITION_VERSIONS_TEACHING.description,
        annotations=LIST_DEFINITION_VERSIONS_TEACHING.annotations,
    )
    async def list_definition_versions(
        kind: DefinitionKind,
        key: str,
        limit: int = 50,
        cursor: str | None = None,
        sort: DefinitionHistorySort = DefinitionHistorySort.REVISION_NO_DESC,
    ) -> DefinitionRevisionHistoryResponse:
        query = DefinitionRevisionHistoryQuery(limit=limit, cursor=cursor, sort=sort)
        return await run_read_operation(
            lambda session: get_definition_history(session, kind, key, query)
        )

    @server.tool(
        name="upload_definition",
        title=UPLOAD_DEFINITION_TEACHING.title,
        description=UPLOAD_DEFINITION_TEACHING.description,
        annotations=UPLOAD_DEFINITION_TEACHING.annotations,
    )
    async def upload_definition_tool(definition_path: str) -> DefinitionRevisionDetailResponse:
        request = definition_upload_request_from_path(definition_path)
        result = await run_session_write_operation(
            lambda session: upload_definition(session, request)
        )
        return result.detail


def register_task_start_tool(server: FastMCP) -> None:
    @server.tool(
        name="start_task",
        title=START_TASK_TEACHING.title,
        description=START_TASK_TEACHING.description,
        annotations=START_TASK_TEACHING.annotations,
    )
    async def start_task(task_compose_path: str) -> TaskStartResponse:
        request = task_start_request_from_path(task_compose_path)
        data_dir = get_settings().data_dir
        return await run_runtime_write_operation_and_wait(
            lambda session: start_task_from_definition_service(
                session,
                request,
                data_dir=data_dir,
            ),
            task_id_getter=lambda response: response.task_id,
        )


async def _search_definitions(
    session: Any,
    *,
    kind: DefinitionKind,
    filters: DefinitionListQuery,
) -> DefinitionSummaryListResponse:
    if kind == DefinitionKind.ROLE:
        return await list_role_definitions(session, filters)
    if kind == DefinitionKind.POLICY:
        return await list_policy_definitions(session, filters)
    return await list_workflow_definitions(session, filters)
