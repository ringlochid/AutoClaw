from __future__ import annotations

from typing import Any

from .load import (
    NodeKind,
    StructuralEditPaletteProjection,
    StructuralEditPolicyProjection,
    StructuralEditRoleProjection,
)


def build_structural_edit_palette() -> Any:
    return StructuralEditPaletteProjection(
        roles=(
            StructuralEditRoleProjection(
                role="architect",
                allowed_node_kinds=(NodeKind.WORKER,),
                description="Run a bounded QA sweep over current implementation evidence.",
            ),
            StructuralEditRoleProjection(
                role="planning_lead",
                allowed_node_kinds=(NodeKind.PARENT, NodeKind.WORKER),
                description="Coordinate a bounded implementation or review subtree.",
            ),
        ),
        policies=(
            StructuralEditPolicyProjection(
                policy="standard-parent-planning",
                applies_to=(NodeKind.PARENT,),
                description="Default planning policy for bounded parent coordination.",
            ),
            StructuralEditPolicyProjection(
                policy="standard-review",
                applies_to=(NodeKind.WORKER,),
                description="Default review policy for worker evidence checks.",
            ),
        ),
    )
