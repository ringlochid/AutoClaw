"""Temporary Phase 6 shim for the legacy node MCP package surface."""

from __future__ import annotations

from autoclaw.integrations.openclaw.node_mcp import (
    NODE_TOOL_NAMES,
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
