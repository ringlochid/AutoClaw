from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal, TypeVar

from mcp.server.fastmcp import FastMCP
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.db.session import get_session_factory
from autoclaw.registry.definition_catalog import (
    get_definition_detail,
    list_policy_definitions,
    list_role_definitions,
)
from autoclaw.runtime import NodeKind
from autoclaw.runtime.control.dispatch.authority import validate_node_session_key
from autoclaw.runtime.control.failures import illegal_caller_error
from autoclaw.runtime.projection import current_runtime_state
from autoclaw.schemas.definitions import (
    DefinitionKind,
    DefinitionListQuery,
    DefinitionListSort,
    DefinitionRevisionDetailResponse,
    DefinitionSummaryListResponse,
)

from .contracts import (
    GET_DEFINITION_TEACHING,
    SEARCH_DEFINITIONS_TEACHING,
)

T = TypeVar("T")


def register_current_definition_tools(server: FastMCP) -> None:
    @server.tool(
        name="search_definitions",
        title=SEARCH_DEFINITIONS_TEACHING.title,
        description=SEARCH_DEFINITIONS_TEACHING.description,
        annotations=SEARCH_DEFINITIONS_TEACHING.annotations,
    )
    async def search_definitions(
        session_key: str,
        task_id: str,
        kind: Literal["role", "policy"],
        query: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        sort: DefinitionListSort = DefinitionListSort.UPDATED_AT_DESC,
        allowed_node_kind: NodeKind | None = None,
        applies_to: NodeKind | None = None,
    ) -> DefinitionSummaryListResponse:
        filters = DefinitionListQuery(
            q=query,
            limit=limit,
            cursor=cursor,
            sort=sort,
            allowed_node_kind=allowed_node_kind,
            applies_to=applies_to,
        )
        return await read_node_definition_context(
            task_id=task_id,
            session_key=session_key,
            operation=lambda session: search_current_definitions(
                session,
                kind=kind,
                filters=filters,
            ),
        )

    @server.tool(
        name="get_definition",
        title=GET_DEFINITION_TEACHING.title,
        description=GET_DEFINITION_TEACHING.description,
        annotations=GET_DEFINITION_TEACHING.annotations,
    )
    async def get_definition(
        session_key: str,
        task_id: str,
        kind: Literal["role", "policy"],
        key: str,
    ) -> DefinitionRevisionDetailResponse:
        return await read_node_definition_context(
            task_id=task_id,
            session_key=session_key,
            operation=lambda session: get_definition_detail(session, DefinitionKind(kind), key),
        )


async def read_node_definition_context(
    *,
    task_id: str,
    session_key: str,
    operation: Callable[[AsyncSession], Awaitable[T]],
) -> T:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await validate_node_session_key(session, task_id=task_id, session_key=session_key)
        state = await current_runtime_state(session, task_id)
        if state.current_node.structural_kind == NodeKind.WORKER.value:
            raise illegal_caller_error(
                "worker nodes cannot use current-only structural definition lookup tools"
            )
        return await operation(session)


async def search_current_definitions(
    session: AsyncSession,
    *,
    kind: Literal["role", "policy"],
    filters: DefinitionListQuery,
) -> DefinitionSummaryListResponse:
    if kind == DefinitionKind.ROLE.value:
        return await list_role_definitions(session, filters)
    return await list_policy_definitions(session, filters)


__all__ = [
    "read_node_definition_context",
    "register_current_definition_tools",
    "search_current_definitions",
]
