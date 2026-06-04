"""Temporary Phase 6 shim for the legacy node MCP entrypoint."""

from __future__ import annotations

from autoclaw.integrations.openclaw.node_mcp.contracts import NODE_TOOL_NAMES
from autoclaw.integrations.openclaw.node_mcp.server import (
    create_node_mcp_app,
    create_node_mcp_mount_app,
    create_node_mcp_server,
)

__all__ = [
    "NODE_TOOL_NAMES",
    "create_node_mcp_app",
    "create_node_mcp_mount_app",
    "create_node_mcp_server",
]
