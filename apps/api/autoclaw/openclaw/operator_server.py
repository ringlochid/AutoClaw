"""Temporary Phase 6 shim for the legacy operator MCP entrypoint."""

from __future__ import annotations

from autoclaw.integrations.openclaw.operator_mcp.server import (
    OPERATOR_TOOL_NAMES,
    create_operator_mcp_app,
    create_operator_mcp_server,
)

__all__ = [
    "OPERATOR_TOOL_NAMES",
    "create_operator_mcp_app",
    "create_operator_mcp_server",
]
