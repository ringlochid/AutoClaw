"""Temporary Phase 6 shim for the legacy runtime contract projection owner."""

from __future__ import annotations

from app.schemas.runtime.contracts.projection import (
    AssignmentProjection,
    CheckpointHandoff,
    CheckpointProjection,
    ManifestCurrentContextProjection,
    ManifestDependencyProjection,
    ManifestFilesystemRootsProjection,
    ManifestNodeConsumeProjection,
    ManifestNodeCriteriaProjection,
    ManifestNodeProduceProjection,
    ManifestNodeProjection,
    ManifestProjection,
    ManifestTaskProjection,
    ManifestWorkflowProjection,
    ProduceRequirement,
    ResolvedNodeContext,
    StructuralEditPaletteProjection,
    StructuralEditPolicyProjection,
    StructuralEditRoleProjection,
)

__all__ = [
    "AssignmentProjection",
    "CheckpointHandoff",
    "CheckpointProjection",
    "ManifestCurrentContextProjection",
    "ManifestDependencyProjection",
    "ManifestFilesystemRootsProjection",
    "ManifestNodeConsumeProjection",
    "ManifestNodeCriteriaProjection",
    "ManifestNodeProduceProjection",
    "ManifestNodeProjection",
    "ManifestProjection",
    "ManifestTaskProjection",
    "ManifestWorkflowProjection",
    "ProduceRequirement",
    "ResolvedNodeContext",
    "StructuralEditPaletteProjection",
    "StructuralEditPolicyProjection",
    "StructuralEditRoleProjection",
]
