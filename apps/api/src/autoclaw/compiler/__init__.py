from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
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

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "DependencyKind": ("autoclaw.compiler.contracts", "DependencyKind"),
    "MappingRolePolicyLookup": (
        "autoclaw.compiler.role_policy_lookup",
        "MappingRolePolicyLookup",
    ),
    "NormalizedChildDefaults": ("autoclaw.compiler.contracts", "NormalizedChildDefaults"),
    "NormalizedCompiledNode": ("autoclaw.compiler.contracts", "NormalizedCompiledNode"),
    "NormalizedCompiledPlan": ("autoclaw.compiler.contracts", "NormalizedCompiledPlan"),
    "NormalizedConsumeBuckets": ("autoclaw.compiler.contracts", "NormalizedConsumeBuckets"),
    "NormalizedConsumeSelector": ("autoclaw.compiler.contracts", "NormalizedConsumeSelector"),
    "NormalizedCriteriaDeclaration": (
        "autoclaw.compiler.contracts",
        "NormalizedCriteriaDeclaration",
    ),
    "NormalizedDependencyEdge": ("autoclaw.compiler.contracts", "NormalizedDependencyEdge"),
    "NormalizedProduceBuckets": ("autoclaw.compiler.contracts", "NormalizedProduceBuckets"),
    "NormalizedProduceSlot": ("autoclaw.compiler.contracts", "NormalizedProduceSlot"),
    "PolicyRevisionDefinition": (
        "autoclaw.compiler.role_policy_lookup",
        "PolicyRevisionDefinition",
    ),
    "RolePolicyLookup": ("autoclaw.compiler.role_policy_lookup", "RolePolicyLookup"),
    "RoleRevisionDefinition": (
        "autoclaw.compiler.role_policy_lookup",
        "RoleRevisionDefinition",
    ),
    "WorkflowRevisionMetadata": ("autoclaw.compiler.contracts", "WorkflowRevisionMetadata"),
    "compile_workflow": ("autoclaw.compiler.compile", "compile_workflow"),
}


def __getattr__(name: str) -> Any:
    module_name, attribute_name = _LAZY_EXPORTS.get(name, (None, None))
    if module_name is None or attribute_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


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
