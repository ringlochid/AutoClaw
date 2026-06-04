"""Temporary Phase 6 shim for the legacy compiler normalization owner."""

from __future__ import annotations

from app.compiler.normalize import (
    build_artifact_slot_map,
    build_authored_node_map,
    build_criteria_slot_map,
    build_dependency_edges,
    expand_consumes,
    expand_criteria,
    flatten_and_index_workflow,
    merge_consume_selectors,
    model_from_attrs,
    normalize_child_defaults,
    normalize_consume_buckets,
    normalize_node,
    normalize_produces,
    resolve_policy,
    resolve_role,
    validate_compiled_dependency_graph,
)

__all__ = [
    "build_artifact_slot_map",
    "build_authored_node_map",
    "build_criteria_slot_map",
    "build_dependency_edges",
    "expand_consumes",
    "expand_criteria",
    "flatten_and_index_workflow",
    "merge_consume_selectors",
    "model_from_attrs",
    "normalize_child_defaults",
    "normalize_consume_buckets",
    "normalize_node",
    "normalize_produces",
    "resolve_policy",
    "resolve_role",
    "validate_compiled_dependency_graph",
]
