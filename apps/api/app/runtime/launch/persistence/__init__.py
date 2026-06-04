"""Launch-persistence package surface."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "build_flow_edge_row": (
        "app.runtime.launch.persistence.flows",
        "build_flow_edge_row",
    ),
    "build_flow_node_row": (
        "app.runtime.launch.persistence.flows",
        "build_flow_node_row",
    ),
    "build_flow_revision_row": (
        "app.runtime.launch.persistence.flows",
        "build_flow_revision_row",
    ),
    "build_flow_row": (
        "app.runtime.launch.persistence.flows",
        "build_flow_row",
    ),
    "build_node_plan_revision_row": (
        "app.runtime.launch.persistence.flows",
        "build_node_plan_revision_row",
    ),
    "materialize_bootstrap_runtime_outputs": (
        "app.runtime.launch.persistence.runtime",
        "materialize_bootstrap_runtime_outputs",
    ),
    "persist_bootstrap_runtime_from_precomputed": (
        "app.runtime.launch.persistence.runtime",
        "persist_bootstrap_runtime_from_precomputed",
    ),
    "stage_launch_attempt_rows": (
        "app.runtime.launch.persistence.attempts",
        "stage_launch_attempt_rows",
    ),
    "write_bootstrap_runtime_outputs": (
        "app.runtime.launch.persistence.runtime",
        "write_bootstrap_runtime_outputs",
    ),
}

build_flow_edge_row: Any
build_flow_node_row: Any
build_flow_revision_row: Any
build_flow_row: Any
build_node_plan_revision_row: Any
materialize_bootstrap_runtime_outputs: Any
persist_bootstrap_runtime_from_precomputed: Any
stage_launch_attempt_rows: Any
write_bootstrap_runtime_outputs: Any


def __getattr__(name: str) -> Any:
    module_name, attribute_name = _LAZY_EXPORTS.get(name, (None, None))
    if module_name is None or attribute_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "build_flow_edge_row",
    "build_flow_node_row",
    "build_flow_revision_row",
    "build_flow_row",
    "build_node_plan_revision_row",
    "materialize_bootstrap_runtime_outputs",
    "persist_bootstrap_runtime_from_precomputed",
    "stage_launch_attempt_rows",
    "write_bootstrap_runtime_outputs",
]
