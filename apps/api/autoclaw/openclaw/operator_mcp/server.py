from __future__ import annotations

from app.config import get_settings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

from autoclaw.openclaw.common import default_transport_security
from autoclaw.openclaw.mcp_operation_failures import ContractFastMCP
from autoclaw.openclaw.operator_mcp.auth import add_operator_auth_middleware
from autoclaw.openclaw.operator_mcp.definition_tools import (
    register_definition_tools,
    register_task_start_tool,
)
from autoclaw.openclaw.operator_mcp.observability_tools import register_observability_ref_tools
from autoclaw.openclaw.operator_mcp.runtime_tools import (
    register_operator_read_tools,
    register_runtime_control_tools,
    register_runtime_task_tools,
)

OPERATOR_TOOL_NAMES: tuple[str, ...] = (
    "search_definitions",
    "get_definition",
    "list_definition_versions",
    "upload_definition",
    "start_task",
    "list_runtime_tasks",
    "get_runtime_task",
    "get_operator_snapshot",
    "get_operator_trace",
    "pause_task",
    "continue_task",
    "cancel_task",
    "get_delivery_state_ref",
    "get_continuity_state_ref",
    "get_watchdog_state_ref",
    "get_provider_events_ref",
)


def create_operator_mcp_server(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> FastMCP:
    server = ContractFastMCP(
        "autoclaw-operator",
        instructions=(
            "Operator-safe AutoClaw surface. This server exposes definition discovery, "
            "guarded definition upload, task start, task-scoped runtime reads and "
            "controls, operator snapshot/trace, and support-state refs."
        ),
        json_response=True,
        stateless_http=True,
        transport_security=transport_security or default_transport_security(host=host),
    )
    register_definition_tools(server)
    register_task_start_tool(server)
    register_runtime_task_tools(server)
    register_operator_read_tools(server)
    register_runtime_control_tools(server)
    register_observability_ref_tools(server)
    return server


def create_operator_mcp_app(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> Starlette:
    app = create_operator_mcp_server(
        host=host,
        transport_security=transport_security,
    ).streamable_http_app()
    add_operator_auth_middleware(
        app,
        expected_token=get_settings().api_key,
    )
    return app
