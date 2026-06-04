from __future__ import annotations

from autoclaw.config import get_settings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

from ..common import default_transport_security
from ..mcp_operation_failures import ContractFastMCP
from .auth import add_operator_auth_middleware
from .definition_tools import (
    register_definition_tools,
    register_task_start_tool,
)
from .observability_tools import register_observability_ref_tools
from .runtime_tools import (
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


def create_operator_mcp_server(
    *,
    host: str = "127.0.0.1",
    transport_security: TransportSecuritySettings | None = None,
) -> FastMCP:
    server = ContractFastMCP(
        "autoclaw-operator",
        instructions=(
            "Operator-safe AutoClaw surface.\n\n"
            "Observe first:\n"
            "- use get_runtime_task for current task status checks.\n"
            "- then use get_operator_snapshot and get_operator_trace for "
            "current state and timeline detail.\n\n"
            "Mutating controls:\n"
            "- pause_task, continue_task, and cancel_task change runtime state.\n"
            "- continue_task is not a status-check or polling tool and "
            "should use a fresh expected_active_flow_revision_id from a current runtime read.\n\n"
            "Support-state refs:\n"
            "- get_delivery_state_ref, get_continuity_state_ref, "
            "get_watchdog_state_ref, and get_provider_events_ref return "
            "support file refs/paths, not parsed status answers.\n"
            "- if a support reread disagrees with controller/runtime truth, "
            "controller/runtime truth wins.\n\n"
            "Definition/task-start writes:\n"
            "- search_definitions, get_definition, and list_definition_versions "
            "are read-only.\n"
            "- upload_definition and start_task load local files on the "
            "AutoClaw host and mutate controller-owned state.\n\n"
            "Phase boundary:\n"
            "- the runtime/operator/support subset remains the Phase 4B closure "
            "surface.\n"
            "- Phase 5A later extends this same operator MCP surface with "
            "definition/task-start parity without changing node-tool separation."
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
