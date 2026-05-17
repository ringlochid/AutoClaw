from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "accept_boundary": ("app.runtime.control.boundary.service", "accept_boundary"),
    "call_parent_tool": ("app.runtime.control.parent_tools", "call_parent_tool"),
    "cancel_runtime_flow": ("app.runtime.control.flow.service", "cancel_runtime_flow"),
    "continue_runtime_flow": ("app.runtime.control.flow.service", "continue_runtime_flow"),
    "list_runtime_flows": ("app.runtime.control.flow.service", "list_runtime_flows"),
    "observability_ref": ("app.runtime.control.observability", "observability_ref"),
    "operator_snapshot": ("app.runtime.control.observability", "operator_snapshot"),
    "operator_trace": ("app.runtime.control.observability", "operator_trace"),
    "pause_runtime_flow": ("app.runtime.control.flow.service", "pause_runtime_flow"),
    "record_checkpoint": ("app.runtime.control.checkpoint.recording", "record_checkpoint"),
    "runtime_flow_read": ("app.runtime.control.flow.service", "runtime_flow_read"),
}

accept_boundary: Any
call_parent_tool: Any
cancel_runtime_flow: Any
continue_runtime_flow: Any
list_runtime_flows: Any
observability_ref: Any
operator_snapshot: Any
operator_trace: Any
pause_runtime_flow: Any
record_checkpoint: Any
runtime_flow_read: Any


def __getattr__(name: str) -> Any:
    module_name, attribute_name = _LAZY_EXPORTS.get(name, (None, None))
    if module_name is None or attribute_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "accept_boundary",
    "call_parent_tool",
    "cancel_runtime_flow",
    "continue_runtime_flow",
    "list_runtime_flows",
    "observability_ref",
    "operator_snapshot",
    "operator_trace",
    "pause_runtime_flow",
    "record_checkpoint",
    "runtime_flow_read",
]
