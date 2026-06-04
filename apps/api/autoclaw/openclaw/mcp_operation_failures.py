"""Temporary Phase 6 shim for the legacy OpenClaw MCP failure helpers."""

from __future__ import annotations

from autoclaw.integrations.openclaw.mcp_operation_failures import (
    OPERATION_FAILURE_OUTPUT_SCHEMA,
    ContractFastMCP,
    operation_failure_tool_result,
    success_or_failure_output_schema,
)

__all__ = [
    "OPERATION_FAILURE_OUTPUT_SCHEMA",
    "ContractFastMCP",
    "operation_failure_tool_result",
    "success_or_failure_output_schema",
]
