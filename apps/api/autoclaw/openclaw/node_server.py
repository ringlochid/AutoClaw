from __future__ import annotations

from typing import Any, Literal

from app.db.session import get_session_factory
from app.registry.definition_catalog import (
    get_definition_detail,
    list_policy_definitions,
    list_role_definitions,
)
from app.runtime.contracts import EgressBoundary, ParentRootToolName
from app.runtime.control.node_operations import (
    BoundaryNodeOperation,
    CheckpointNodeOperation,
    NodeOperation,
    ParentToolNodeOperation,
    execute_bound_node_operation,
)
from app.schemas.definitions import (
    DefinitionKind,
    DefinitionListQuery,
    DefinitionListSort,
    DefinitionRevisionDetailResponse,
    DefinitionSummaryListResponse,
)
from app.schemas.runtime import (
    BoundaryWrite,
    CheckpointWrite,
    CheckpointWriteBody,
)
from app.schemas.runtime.parent_tools import ParentToolCall
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import Message, Receive, Scope, Send

from autoclaw.openclaw.bindings import (
    NodeMcpBinding,
    load_validated_node_mcp_binding_by_session_key,
    validate_node_mcp_binding,
)
from autoclaw.openclaw.common import default_transport_security, run_read_operation

NODE_TOOL_NAMES: tuple[str, ...] = (
    "search_definitions",
    "get_definition",
    "record_checkpoint",
    "return_boundary",
    "call_parent_tool",
)

_NODE_SESSION_KEY_HEADER = "x-session-key"
_NODE_TASK_ID_HEADER = "x-task-id"


def create_node_mcp_server(
    binding: NodeMcpBinding,
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> FastMCP:
    server = FastMCP(
        "autoclaw-node",
        instructions=(
            "Dispatch-bound AutoClaw node surface. This server exposes current-only role/policy "
            "lookup plus the bound callback operations. Task, dispatch, and callback authority "
            "are implicit in the server instance; callers do not pass task identifiers or "
            "session tokens in tool arguments."
        ),
        json_response=True,
        stateless_http=True,
        transport_security=transport_security or default_transport_security(host=host),
    )
    _register_current_definition_tools(server)

    @server.tool(name="record_checkpoint")
    async def record_checkpoint_tool(checkpoint: CheckpointWriteBody) -> dict[str, Any]:
        return await _run_node_operation(
            binding=binding,
            operation=CheckpointNodeOperation(payload=CheckpointWrite(checkpoint=checkpoint)),
        )

    @server.tool(name="return_boundary")
    async def return_boundary(boundary: EgressBoundary) -> dict[str, Any]:
        return await _run_node_operation(
            binding=binding,
            operation=BoundaryNodeOperation(payload=BoundaryWrite(boundary=boundary)),
        )

    @server.tool(name="call_parent_tool")
    async def call_parent_tool_tool(
        tool_name: ParentRootToolName,
        payload: dict[str, Any],
        expected_structural_revision_id: str | None = None,
    ) -> dict[str, Any]:
        return await _run_node_operation(
            binding=binding,
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
        return await run_read_operation(
            lambda session: _search_current_definitions(
                session,
                kind=kind,
                filters=filters,
            )
        )

    @server.tool(name="get_definition")
    async def get_definition(
        kind: Literal["role", "policy"],
        key: str,
    ) -> DefinitionRevisionDetailResponse:
        return await run_read_operation(
            lambda session: get_definition_detail(session, DefinitionKind(kind), key)
        )


def create_node_mcp_app(
    binding: NodeMcpBinding,
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> Starlette:
    return create_node_mcp_server(
        binding,
        host=host,
        transport_security=transport_security,
    ).streamable_http_app()


def create_task_bound_node_mcp_proxy_app(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> _TaskBoundNodeMcpProxyApp:
    return _TaskBoundNodeMcpProxyApp(
        host=host,
        transport_security=transport_security,
    )


async def _run_node_operation(
    binding: NodeMcpBinding,
    operation: NodeOperation,
) -> dict[str, Any]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await validate_node_mcp_binding(session, binding)
        result = await execute_bound_node_operation(
            session,
            task_id=binding.task_id,
            operation=operation,
        )
        return result.model_dump(mode="json")


async def _search_current_definitions(
    session: Any,
    *,
    kind: Literal["role", "policy"],
    filters: DefinitionListQuery,
) -> DefinitionSummaryListResponse:
    if kind == DefinitionKind.ROLE.value:
        return await list_role_definitions(session, filters)
    return await list_policy_definitions(session, filters)


class _TaskBoundNodeMcpProxyApp:
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
        if scope["type"] != "http":
            response = JSONResponse(
                status_code=500,
                content={"error": "unsupported node MCP scope"},
            )
            await response(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        session_key = request.headers.get(_NODE_SESSION_KEY_HEADER, "").strip()
        if not session_key:
            response = JSONResponse(
                status_code=400,
                content={"error": f"missing {_NODE_SESSION_KEY_HEADER} header"},
            )
            await response(scope, receive, send)
            return

        expected_task_id = request.headers.get(_NODE_TASK_ID_HEADER, "").strip() or None

        try:
            binding = await load_validated_node_mcp_binding_by_session_key(
                session_key,
                expected_task_id=expected_task_id,
            )
        except ValueError as exc:
            response = JSONResponse(
                status_code=409,
                content={"error": str(exc)},
            )
            await response(scope, receive, send)
            return
        except RuntimeError as exc:
            response = JSONResponse(
                status_code=404,
                content={"error": str(exc)},
            )
            await response(scope, receive, send)
            return

        app = create_node_mcp_app(
            binding,
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
    "create_node_mcp_server",
    "create_task_bound_node_mcp_proxy_app",
]
