"""Temporary Phase 6 shims for the legacy compiler owner."""

from __future__ import annotations

from autoclaw.compiler.compile import compile_workflow
from autoclaw.compiler.contracts import (
    DependencyKind,
    NormalizedChildDefaults,
    NormalizedCompiledNode,
    NormalizedCompiledPlan,
    NormalizedConsumeBuckets,
    NormalizedConsumeSelector,
    NormalizedCriteriaDeclaration,
    NormalizedDependencyEdge,
    NormalizedProduceBuckets,
    NormalizedProduceSlot,
    WorkflowRevisionMetadata,
)
from autoclaw.compiler.role_policy_lookup import (
    MappingRolePolicyLookup,
    PolicyRevisionDefinition,
    RolePolicyLookup,
    RoleRevisionDefinition,
)

__all__ = [
    "DependencyKind",
    "MappingRolePolicyLookup",
    "NormalizedChildDefaults",
    "NormalizedCompiledNode",
    "NormalizedCompiledPlan",
    "NormalizedConsumeBuckets",
    "NormalizedConsumeSelector",
    "NormalizedCriteriaDeclaration",
    "NormalizedDependencyEdge",
    "NormalizedProduceBuckets",
    "NormalizedProduceSlot",
    "PolicyRevisionDefinition",
    "RolePolicyLookup",
    "RoleRevisionDefinition",
    "WorkflowRevisionMetadata",
    "compile_workflow",
]
