from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypeVar

from app.db.session import get_session_factory
from app.registry.definition_catalog import (
    get_definition_detail,
    list_policy_definitions,
    list_role_definitions,
)
from app.runtime.contracts import EgressBoundary, ParentRootToolName
from app.runtime.control.dispatch.authority import validate_node_session_key
from app.runtime.control.node_operations import (
    BoundaryNodeOperation,
    CheckpointNodeOperation,
    NodeOperation,
    ParentToolNodeOperation,
    execute_node_operation,
)
from app.schemas.definitions import (
    DefinitionKind,
    DefinitionListQuery,
    DefinitionListSort,
    DefinitionRevisionDetailResponse,
    DefinitionSummaryListResponse,
)
from app.schemas.runtime import BoundaryWrite, CheckpointWrite, CheckpointWriteBody
from app.schemas.runtime.parent_tools import ParentToolCall
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.applications import Starlette
from starlette.types import Message, Receive, Scope, Send

from autoclaw.openclaw.common import default_transport_security
from autoclaw.openclaw.mcp_operation_failures import ContractFastMCP

NODE_TOOL_NAMES: tuple[str, ...] = (
    "search_definitions",
    "get_definition",
    "record_checkpoint",
    "return_boundary",
    "call_parent_tool",
)

T = TypeVar("T")


def create_node_mcp_server(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> FastMCP:
    server = ContractFastMCP(
        "autoclaw-node",
        instructions=(
            "Static explicit-arg AutoClaw node surface. Every node tool call must pass "
            "the current dispatch-local session_key and task_id. Server-side authority "
            "validation resolves that session against the live NodeSession and current "
            "dispatch truth before any node read or write runs."
        ),
        json_response=True,
        stateless_http=True,
        transport_security=transport_security or default_transport_security(host=host),
    )
    _register_current_definition_tools(server)

    @server.tool(name="record_checkpoint")
    async def record_checkpoint_tool(
        session_key: str,
        task_id: str,
        checkpoint: CheckpointWriteBody,
    ) -> dict[str, Any]:
        return await _run_node_operation(
            task_id=task_id,
            session_key=session_key,
            operation=CheckpointNodeOperation(payload=CheckpointWrite(checkpoint=checkpoint)),
        )

    @server.tool(name="return_boundary")
    async def return_boundary(
        session_key: str,
        task_id: str,
        boundary: EgressBoundary,
    ) -> dict[str, Any]:
        return await _run_node_operation(
            task_id=task_id,
            session_key=session_key,
            operation=BoundaryNodeOperation(payload=BoundaryWrite(boundary=boundary)),
        )

    @server.tool(name="call_parent_tool")
    async def call_parent_tool_tool(
        session_key: str,
        task_id: str,
        tool_name: ParentRootToolName,
        payload: dict[str, Any],
        expected_structural_revision_id: str | None = None,
    ) -> dict[str, Any]:
        return await _run_node_operation(
            task_id=task_id,
            session_key=session_key,
            operation=ParentToolNodeOperation(
                tool_name=tool_name,
                payload=ParentToolCall(
                    tool_name=tool_name,
                    payload=payload,
                    expected_structural_revision_id=expected_structural_revision_id,
                ),
            ),
        )

    return server


def _register_current_definition_tools(server: FastMCP) -> None:
    @server.tool(name="search_definitions")
    async def search_definitions(
        session_key: str,
        task_id: str,
        kind: Literal["role", "policy"],
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
        return await _run_node_read(
            task_id=task_id,
            session_key=session_key,
            operation=lambda session: _search_current_definitions(
                session,
                kind=kind,
                filters=filters,
            ),
        )

    @server.tool(name="get_definition")
    async def get_definition(
        session_key: str,
        task_id: str,
        kind: Literal["role", "policy"],
        key: str,
    ) -> DefinitionRevisionDetailResponse:
        return await _run_node_read(
            task_id=task_id,
            session_key=session_key,
            operation=lambda session: get_definition_detail(session, DefinitionKind(kind), key),
        )


def create_node_mcp_app(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> Starlette:
    return create_node_mcp_server(
        host=host,
        transport_security=transport_security,
    ).streamable_http_app()


def create_node_mcp_mount_app(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> _MountedNodeMcpApp:
    return _MountedNodeMcpApp(
        host=host,
        transport_security=transport_security,
    )


async def _run_node_operation(
    *,
    task_id: str,
    session_key: str,
    operation: NodeOperation,
) -> dict[str, Any]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await execute_node_operation(
            session,
            task_id=task_id,
            session_key=session_key,
            operation=operation,
            invalid_summary="invalid node session key",
            stale_summary="stale node session key",
            inactive_summary="inactive node session key",
        )
        return result.model_dump(mode="json")


async def _run_node_read(
    *,
    task_id: str,
    session_key: str,
    operation: Callable[[AsyncSession], Awaitable[T]],
) -> T:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await validate_node_session_key(session, task_id=task_id, session_key=session_key)
        return await operation(session)


async def _search_current_definitions(
    session: Any,
    *,
    kind: Literal["role", "policy"],
    filters: DefinitionListQuery,
) -> DefinitionSummaryListResponse:
    if kind == DefinitionKind.ROLE.value:
        return await list_role_definitions(session, filters)
    return await list_policy_definitions(session, filters)


class _MountedNodeMcpApp:
    def __init__(
        self,
        *,
        host: str,
        transport_security: TransportSecuritySettings | None,
    ) -> None:
        self._host = host
        self._transport_security = transport_security

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(receive, send)
            return

        app = create_node_mcp_app(
            host=self._host,
            transport_security=self._transport_security,
        )
        proxied_scope = dict(scope)
        proxied_scope["path"] = "/mcp"
        proxied_scope["raw_path"] = b"/mcp"
        async with app.router.lifespan_context(app):
            await app(proxied_scope, receive, send)

    async def _handle_lifespan(self, receive: Receive, send: Send) -> None:
        while True:
            message: Message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
                continue
            if message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return


__all__ = [
    "NODE_TOOL_NAMES",
    "create_node_mcp_app",
    "create_node_mcp_mount_app",
    "create_node_mcp_server",
]
