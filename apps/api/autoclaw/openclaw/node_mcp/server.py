"""Temporary Phase 6 shim for the legacy node MCP server module."""

from __future__ import annotations

from autoclaw.integrations.openclaw.node_mcp.server import (
    create_node_mcp_app,
    create_node_mcp_mount_app,
    create_node_mcp_server,
)

__all__ = [
    "create_node_mcp_app",
    "create_node_mcp_mount_app",
    "create_node_mcp_server",
]
