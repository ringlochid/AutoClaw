from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from autoclaw.config import get_settings
from autoclaw.definitions.authoring import (
    DefinitionDraftSetDetailResponse,
    DefinitionDraftSetListQuery,
    DefinitionDraftSetListResponse,
    list_definition_draft_sets,
    read_definition_draft_set,
)
from autoclaw.runtime.post_commit.operations import read_session_operation

from ..tool_teaching import read_only_tool_teaching

LIST_DEFINITION_DRAFT_SETS_TEACHING = read_only_tool_teaching(
    name="list_definition_draft_sets",
    summary="List backend-owned definition draft sets.",
    details=(
        "Use this operator MCP read to discover draft-set ids and compact "
        "saved draft refs. Mutating draft authoring stays on the HTTP "
        "/authoring workbench API.",
    ),
)
GET_DEFINITION_DRAFT_SET_TEACHING = read_only_tool_teaching(
    name="get_definition_draft_set",
    summary="Inspect one backend-owned definition draft set in detail.",
    details=(
        "This read-only operator MCP tool returns saved draft YAML bodies, "
        "normalized content, and preview state for inspection only. Mutating "
        "draft authoring stays on the HTTP /authoring workbench API.",
    ),
)


def register_authoring_tools(server: FastMCP) -> None:
    @server.tool(
        name="list_definition_draft_sets",
        title=LIST_DEFINITION_DRAFT_SETS_TEACHING.title,
        description=LIST_DEFINITION_DRAFT_SETS_TEACHING.description,
        annotations=LIST_DEFINITION_DRAFT_SETS_TEACHING.annotations,
    )
    async def list_definition_draft_sets_tool(
        cursor: str | None = None,
        limit: int = 50,
    ) -> DefinitionDraftSetListResponse:
        query = DefinitionDraftSetListQuery(cursor=cursor, limit=limit)
        return await read_session_operation(
            lambda session: list_definition_draft_sets(
                session,
                data_dir=get_settings().data_dir,
                query=query,
            )
        )

    @server.tool(
        name="get_definition_draft_set",
        title=GET_DEFINITION_DRAFT_SET_TEACHING.title,
        description=GET_DEFINITION_DRAFT_SET_TEACHING.description,
        annotations=GET_DEFINITION_DRAFT_SET_TEACHING.annotations,
    )
    async def get_definition_draft_set_tool(
        draft_set_id: str,
    ) -> DefinitionDraftSetDetailResponse:
        return await read_session_operation(
            lambda session: read_definition_draft_set(
                session,
                data_dir=get_settings().data_dir,
                draft_set_id=draft_set_id,
            )
        )
