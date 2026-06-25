from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.types import Message, Receive, Scope, Send

from ..mcp_operation_failures import ContractFastMCP
from ..transport import default_transport_security
from .contracts import NODE_TOOL_NAMES
from .definition_tools import register_current_definition_tools
from .runtime_tools import register_node_runtime_tools


class MountedNodeMcpApp:
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
) -> MountedNodeMcpApp:
    return MountedNodeMcpApp(
        host=host,
        transport_security=transport_security,
    )


def create_node_mcp_server(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> FastMCP:
    server = ContractFastMCP(
        "autoclaw-node",
        instructions=(
            "Static explicit-arg AutoClaw node surface.\n\n"
            "Lookup:\n"
            "- search_definitions and get_definition are read-only "
            "current-only lookup tools for the live structural-edit lane "
            "when surfaced prompt or manifest context is insufficient.\n\n"
            "Persist progress:\n"
            "- record_checkpoint publishes durable semantic progress for "
            "the current live node execution.\n\n"
            "Close the current turn:\n"
            "- return_boundary closes the current dispatch turn; yield is "
            "non-terminal workflow progress, while green, retry, and blocked "
            "are terminal for the current dispatch turn.\n"
            "- after a successful return_boundary call, stop the current outer "
            "assistant turn immediately rather than continuing with more tool "
            "calls or prose.\n\n"
            "Open external waits:\n"
            "- open_human_request opens a typed pending human request when "
            "the current node capability allows the requested kind.\n"
            "- open_human_request creates waiting_for_human_request directly; "
            "it is not a workflow boundary, generic chat continuation, "
            "operator note, or task continue action.\n\n"
            "- start_command_run starts a controller-managed long-running "
            "command run when the current node command_run capability allows it.\n"
            "- start_command_run creates waiting_for_command_run directly; "
            "it is not a workflow boundary, task continue action, concrete "
            "process runner, or raw log capture surface.\n\n"
            "Mutate parent/root state:\n"
            "- assign_child, add_child, update_child, remove_child, "
            "release_green, and release_blocked perform dispatch-local "
            "parent/root mutation only when the current dispatch allows "
            "them.\n\n"
            "Not for operator control:\n"
            "- every node tool call must pass the current dispatch-local "
            "session_key and task_id.\n"
            "- server-side authority validation resolves that session "
            "against the live NodeSession and current dispatch truth "
            "before any node read or write runs.\n"
            "- use operator MCP for runtime inspection, pause, continue, "
            "cancel, definition upload, and task start."
        ),
        json_response=True,
        stateless_http=True,
        transport_security=transport_security or default_transport_security(host=host),
    )
    register_current_definition_tools(server)
    register_node_runtime_tools(server)
    return server


__all__ = [
    "NODE_TOOL_NAMES",
    "create_node_mcp_app",
    "create_node_mcp_mount_app",
    "create_node_mcp_server",
]
