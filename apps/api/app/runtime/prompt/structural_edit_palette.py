from __future__ import annotations

from app.runtime.contracts import (
    NodeKind,
    StructuralEditPaletteProjection,
)


def structural_edit_palette_lines(
    palette: StructuralEditPaletteProjection | None,
    *,
    indent: str = "",
) -> list[str]:
    if palette is None or (not palette.roles and not palette.policies):
        return []

    lines = [f"{indent}- structural edit palette:"]
    if palette.roles:
        lines.append(f"{indent}  - roles:")
        for role in palette.roles:
            allowed_node_kinds = ", ".join(node_kind.value for node_kind in role.allowed_node_kinds)
            lines.append(
                f"{indent}    - {role.role} (allowed node kinds: {allowed_node_kinds}): "
                f"{role.description}"
            )
    if palette.policies:
        lines.append(f"{indent}  - policies:")
        for policy in palette.policies:
            applies_to = ", ".join(node_kind.value for node_kind in policy.applies_to)
            lines.append(
                f"{indent}    - {policy.policy} (applies_to: {applies_to}): {policy.description}"
            )
    return lines


def parent_root_structural_edit_palette(
    *,
    node_kind: NodeKind,
    palette: StructuralEditPaletteProjection | None,
) -> StructuralEditPaletteProjection | None:
    if node_kind == NodeKind.WORKER:
        return None
    return palette
