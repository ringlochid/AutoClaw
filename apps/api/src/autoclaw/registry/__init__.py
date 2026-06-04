"""Temporary Phase 6 shims for the legacy registry owner."""

from __future__ import annotations

from autoclaw.registry.current import (
    RegistryWorkflowDefinition,
    build_role_policy_lookup,
    compile_current_workflow,
    compile_current_workflow_launch_snapshot,
    load_current_policy,
    load_current_role,
    load_current_workflow,
    load_policy_revision,
    load_role_revision,
)
from autoclaw.registry.seeds import seed_definition_registry
from autoclaw.registry.upsert import (
    upsert_policy_definition,
    upsert_role_definition,
    upsert_workflow_definition,
)

__all__ = [
    "RegistryWorkflowDefinition",
    "build_role_policy_lookup",
    "compile_current_workflow",
    "compile_current_workflow_launch_snapshot",
    "load_current_policy",
    "load_current_role",
    "load_current_workflow",
    "load_policy_revision",
    "load_role_revision",
    "seed_definition_registry",
    "upsert_policy_definition",
    "upsert_role_definition",
    "upsert_workflow_definition",
]
