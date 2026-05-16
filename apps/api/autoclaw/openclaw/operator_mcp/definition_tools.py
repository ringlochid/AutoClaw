from __future__ import annotations

from typing import Any, Literal

from app.config import get_settings
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
    DefinitionUploadRequest,
    PolicyDefinitionFile,
    RoleDefinitionFile,
    WorkflowDefinitionFile,
)
from app.schemas.runtime import TaskStartRequest, TaskStartResponse
from mcp.server.fastmcp import FastMCP

from autoclaw.openclaw.common import (
    load_yaml_mapping,
    run_read_operation,
    run_runtime_write_operation_and_wait,
    run_session_write_operation,
)


def register_definition_tools(server: FastMCP) -> None:
    @server.tool(name="search_definitions")
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

    @server.tool(name="get_definition")
    async def get_definition(
        kind: DefinitionKind,
        key: str,
    ) -> DefinitionRevisionDetailResponse:
        return await run_read_operation(lambda session: get_definition_detail(session, kind, key))

    @server.tool(name="list_definition_versions")
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

    @server.tool(name="upload_definition")
    async def upload_definition_tool(definition_path: str) -> DefinitionRevisionDetailResponse:
        request = _definition_upload_request_from_path(definition_path)
        result = await run_session_write_operation(
            lambda session: upload_definition(session, request)
        )
        return result.detail


def register_task_start_tool(server: FastMCP) -> None:
    @server.tool(name="start_task")
    async def start_task(task_compose_path: str) -> TaskStartResponse:
        request = TaskStartRequest.model_validate(load_yaml_mapping(task_compose_path))
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


def _definition_upload_request_from_path(definition_path: str) -> DefinitionUploadRequest:
    payload = load_yaml_mapping(definition_path)
    kind = DefinitionKind(payload["kind"])
    content: RoleDefinitionFile | PolicyDefinitionFile | WorkflowDefinitionFile
    if kind == DefinitionKind.ROLE:
        content = RoleDefinitionFile.model_validate(payload)
    elif kind == DefinitionKind.POLICY:
        content = PolicyDefinitionFile.model_validate(payload)
    else:
        content = WorkflowDefinitionFile.model_validate(payload)
    return DefinitionUploadRequest(kind=kind, content=content)
