from __future__ import annotations

from collections.abc import Iterable

from app.runtime.contracts import AssignmentConsumeRef, NodeRuntimeFileRef


def render_markdown_section(title: str, lines: Iterable[str]) -> str:
    collected = [line for line in lines if line]
    return f"## {title}\n" + "\n".join(collected)


def render_ref_without_path(ref: AssignmentConsumeRef) -> list[str]:
    if isinstance(ref, NodeRuntimeFileRef):
        return [
            f"- kind: {ref.kind.value}",
            f"  description: {ref.description}",
        ]
    lines = [f"- kind: {ref.kind.value}"]
    if ref.slot is not None:
        lines.append(f"  slot: {ref.slot}")
    lines.append(f"  description: {ref.description}")
    return lines


def render_ref_with_path(ref: AssignmentConsumeRef) -> list[str]:
    if isinstance(ref, NodeRuntimeFileRef):
        return render_node_runtime_ref(ref)
    lines = [f"- kind: {ref.kind.value}"]
    if ref.slot is not None:
        lines.append(f"  slot: {ref.slot}")
    if ref.version is not None:
        lines.append(f"  version: {ref.version}")
    lines.append(f"  path: {ref.path}")
    lines.append(f"  description: {ref.description}")
    return lines


def render_node_runtime_ref(ref: NodeRuntimeFileRef) -> list[str]:
    return [
        f"- kind: {ref.kind.value}",
        f"  path: {ref.path}",
        f"  description: {ref.description}",
    ]
