"""Temporary Phase 6 shim for the legacy OpenClaw bindings surface."""

from __future__ import annotations

from autoclaw.integrations.openclaw.bindings import (
    NodeToolContext,
    load_current_node_tool_context,
)

__all__ = ["NodeToolContext", "load_current_node_tool_context"]
