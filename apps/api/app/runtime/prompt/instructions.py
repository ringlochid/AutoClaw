from __future__ import annotations

from app.runtime.contracts import (
    NodeKind,
    PromptFamily,
    PromptRenderRequest,
    validate_prompt_family_for_node_kind,
)
from app.runtime.prompt.asset_catalog import load_exact_prompt_block
from app.runtime.prompt.sections.rendering import (
    CURRENT_ONLY_DEFINITION_LOOKUP_GUIDANCE,
    DEFINITION_REVISION_HISTORY_EXCLUSION_GUIDANCE,
)
from app.runtime.prompt.structural_edit_palette import (
    parent_root_structural_edit_palette,
    structural_edit_palette_lines,
)

_COMMON_FULL_PROMPT_BLOCK_IDS = (
    "autoclaw_system_block_v1",
    "autoclaw_provider_continuity_block_v1",
    "autoclaw_parent_worker_split_v1",
    "runtime_boundary_rule_block_v1",
)
_FULL_PROMPT_LEGALITY_BLOCK_IDS = {
    PromptFamily.WORKER_DISPATCH: "runtime_legality_block_worker_v1",
    PromptFamily.PARENT_ROOT_DISPATCH: "runtime_legality_block_parent_v1",
}


def render_prompt_instructions(request: PromptRenderRequest) -> str:
    block_ids = _instruction_block_ids(
        prompt_family=request.prompt_family,
        node_kind=request.current_node.node_kind,
    )
    exact_blocks = tuple(load_exact_prompt_block(block_id) for block_id in block_ids)
    return "\n\n".join((*exact_blocks, _render_node_guidance_block(request)))


def live_instruction_block_inventory() -> dict[str, dict[str, tuple[str, ...]]]:
    return {
        prompt_family.value: {
            "full_prompt": _full_prompt_instruction_block_ids(prompt_family),
        }
        for prompt_family in PromptFamily
    }


def _full_prompt_instruction_block_ids(prompt_family: PromptFamily) -> tuple[str, ...]:
    return (
        *_COMMON_FULL_PROMPT_BLOCK_IDS,
        _FULL_PROMPT_LEGALITY_BLOCK_IDS[prompt_family],
    )


def _instruction_block_ids(
    *,
    prompt_family: PromptFamily,
    node_kind: NodeKind,
) -> tuple[str, ...]:
    validate_prompt_family_for_node_kind(
        prompt_family=prompt_family,
        node_kind=node_kind,
    )
    return _full_prompt_instruction_block_ids(prompt_family)


def _render_node_guidance_block(request: PromptRenderRequest) -> str:
    node = request.current_node
    lines = [
        "Current node-kind, role, and policy guidance for this dispatch:",
        f"- node kind: {node.node_kind.value}",
        f"- node key: {node.node_key}",
        f"- node description: {node.node_description}",
        f"- role: {node.role_key}",
        f"- role description: {node.role_description}",
    ]
    if node.role_instruction is not None:
        lines.append(f"- role instruction: {node.role_instruction}")
    if node.policy_key is not None:
        lines.append(f"- policy: {node.policy_key}")
    if node.policy_description is not None:
        lines.append(f"- policy description: {node.policy_description}")
    if node.policy_instruction is not None:
        lines.append(f"- policy instruction: {node.policy_instruction}")
    palette = parent_root_structural_edit_palette(
        node_kind=node.node_kind,
        palette=request.manifest.structural_edit_palette,
    )
    if palette is not None:
        lines.extend(structural_edit_palette_lines(palette))
        lines.append(
            "- structural edits stay palette-first: reread the current manifest and use "
            "the surfaced structural edit palette before any lookup"
        )
        lines.append(f"- {CURRENT_ONLY_DEFINITION_LOOKUP_GUIDANCE}")
        lines.append(f"- {DEFINITION_REVISION_HISTORY_EXCLUSION_GUIDANCE}")
    return "\n".join(lines)
