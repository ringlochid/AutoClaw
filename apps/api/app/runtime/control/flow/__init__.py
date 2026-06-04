"""Flow-control package surface."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "WORKFLOW_MANIFEST_REF_DESCRIPTION": (
        "app.runtime.control.flow.listing",
        "WORKFLOW_MANIFEST_REF_DESCRIPTION",
    ),
    "cancel_runtime_flow": (
        "app.runtime.control.flow.service",
        "cancel_runtime_flow",
    ),
    "coerce_datetime_to_utc": (
        "app.runtime.control.flow.timestamps",
        "coerce_datetime_to_utc",
    ),
    "continue_runtime_flow": (
        "app.runtime.control.flow.service",
        "continue_runtime_flow",
    ),
    "current_semantic_flow_target": (
        "app.runtime.control.flow.queries",
        "current_semantic_flow_target",
    ),
    "flow_node_by_key": (
        "app.runtime.control.flow.queries",
        "flow_node_by_key",
    ),
    "latest_checkpoint_for_attempt": (
        "app.runtime.control.flow.queries",
        "latest_checkpoint_for_attempt",
    ),
    "latest_unreplaced_fenced_dispatch": (
        "app.runtime.control.flow.reads",
        "latest_unreplaced_fenced_dispatch",
    ),
    "list_runtime_flows": (
        "app.runtime.control.flow.reads",
        "list_runtime_flows",
    ),
    "next_node_sequence_number": (
        "app.runtime.control.flow.queries",
        "next_node_sequence_number",
    ),
    "pause_runtime_flow": (
        "app.runtime.control.flow.service",
        "pause_runtime_flow",
    ),
    "require_flow_for_task": (
        "app.runtime.control.flow.queries",
        "require_flow_for_task",
    ),
    "resolve_flow_resume_target": (
        "app.runtime.control.flow.resume",
        "resolve_flow_resume_target",
    ),
    "runtime_flow_read": (
        "app.runtime.control.flow.reads",
        "runtime_flow_read",
    ),
}

WORKFLOW_MANIFEST_REF_DESCRIPTION: Any
cancel_runtime_flow: Any
coerce_datetime_to_utc: Any
continue_runtime_flow: Any
current_semantic_flow_target: Any
flow_node_by_key: Any
latest_checkpoint_for_attempt: Any
latest_unreplaced_fenced_dispatch: Any
list_runtime_flows: Any
next_node_sequence_number: Any
pause_runtime_flow: Any
require_flow_for_task: Any
resolve_flow_resume_target: Any
runtime_flow_read: Any


def __getattr__(name: str) -> Any:
    module_name, attribute_name = _LAZY_EXPORTS.get(name, (None, None))
    if module_name is None or attribute_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "WORKFLOW_MANIFEST_REF_DESCRIPTION",
    "cancel_runtime_flow",
    "coerce_datetime_to_utc",
    "continue_runtime_flow",
    "current_semantic_flow_target",
    "flow_node_by_key",
    "latest_checkpoint_for_attempt",
    "latest_unreplaced_fenced_dispatch",
    "list_runtime_flows",
    "next_node_sequence_number",
    "pause_runtime_flow",
    "require_flow_for_task",
    "resolve_flow_resume_target",
    "runtime_flow_read",
]
