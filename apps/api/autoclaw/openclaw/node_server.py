from __future__ import annotations

from typing import Any

from app.db.session import get_session_factory
from app.runtime.contracts import EgressBoundary, ParentRootToolName
from app.runtime.control.node_operations import (
    BoundaryNodeOperation,
    CheckpointNodeOperation,
    NodeOperation,
    ParentToolNodeOperation,
    execute_bound_node_operation,
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

from autoclaw.openclaw.bindings import NodeMcpBinding, validate_node_mcp_binding
from autoclaw.openclaw.common import default_transport_security

NODE_TOOL_NAMES: tuple[str, ...] = (
    "record_checkpoint",
    "return_boundary",
    "call_parent_tool",
)


def create_node_mcp_server(
    binding: NodeMcpBinding,
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> FastMCP:
    server = FastMCP(
        "autoclaw-node",
        instructions=(
            "Dispatch-bound AutoClaw node surface. The bound task and callback authority are "
            "implicit in the server instance; callers do not pass task identifiers or session "
            "tokens in tool arguments."
        ),
        json_response=True,
        stateless_http=True,
        transport_security=transport_security or default_transport_security(host=host),
    )

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


__all__ = [
    "NODE_TOOL_NAMES",
    "create_node_mcp_app",
    "create_node_mcp_server",
]
