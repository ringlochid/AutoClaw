from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

from autoclaw.runtime.contracts import NodeRuntimeFileRef


def render_markdown_section(title: str, lines: Iterable[str]) -> str:
    collected = [line for line in lines if line]
    return f"## {title}\n" + "\n".join(collected)


def render_ref_without_path(ref: object) -> list[str]:
    if isinstance(ref, NodeRuntimeFileRef):
        return [
            f"- kind: {ref.kind.value}",
            f"  description: {ref.description}",
        ]

    typed_ref = cast(Any, ref)
    kind = _kind_value(ref)
    lines = [f"- kind: {kind}"]
    slot = getattr(typed_ref, "slot", None)
    if slot is not None:
        lines.append(f"  slot: {slot}")
    lines.append(f"  description: {typed_ref.description}")
    return lines


def render_ref_with_path(ref: object) -> list[str]:
    if isinstance(ref, NodeRuntimeFileRef):
        return render_node_runtime_ref(ref)

    typed_ref = cast(Any, ref)
    kind = _kind_value(ref)
    lines = [f"- kind: {kind}"]
    slot = getattr(typed_ref, "slot", None)
    if slot is not None:
        lines.append(f"  slot: {slot}")
    version = getattr(typed_ref, "version", None)
    if version is not None:
        lines.append(f"  version: {version}")
    lines.append(f"  path: {typed_ref.path}")
    lines.append(f"  description: {typed_ref.description}")
    return lines


def render_node_runtime_ref(ref: NodeRuntimeFileRef) -> list[str]:
    return [
        f"- kind: {ref.kind.value}",
        f"  path: {ref.path}",
        f"  description: {ref.description}",
    ]


def _kind_value(ref: object) -> str:
    kind = cast(Any, ref).kind
    return kind.value if hasattr(kind, "value") else str(cast(Any, kind))
