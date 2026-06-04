from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autoclaw.integrations.openclaw.node_mcp.contracts import NODE_TOOL_NAMES
    from autoclaw.integrations.openclaw.node_mcp.server import (
        create_node_mcp_app,
        create_node_mcp_mount_app,
        create_node_mcp_server,
    )

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "NODE_TOOL_NAMES": ("autoclaw.integrations.openclaw.node_mcp.contracts", "NODE_TOOL_NAMES"),
    "create_node_mcp_app": (
        "autoclaw.integrations.openclaw.node_mcp.server",
        "create_node_mcp_app",
    ),
    "create_node_mcp_mount_app": (
        "autoclaw.integrations.openclaw.node_mcp.server",
        "create_node_mcp_mount_app",
    ),
    "create_node_mcp_server": (
        "autoclaw.integrations.openclaw.node_mcp.server",
        "create_node_mcp_server",
    ),
}


def __getattr__(name: str) -> Any:
    module_name, attribute_name = _LAZY_EXPORTS.get(name, (None, None))
    if module_name is None or attribute_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "NODE_TOOL_NAMES",
    "create_node_mcp_app",
    "create_node_mcp_mount_app",
    "create_node_mcp_server",
]
