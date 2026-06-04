"""Explicit Phase 6 bridge for the legacy parent-tool control owner."""

from __future__ import annotations

from app.runtime.control import parent_tools as legacy_parent_tools

call_parent_tool = legacy_parent_tools.call_parent_tool
validate_parent_tool_call = legacy_parent_tools.validate_parent_tool_call

__all__ = ["call_parent_tool", "validate_parent_tool_call"]
