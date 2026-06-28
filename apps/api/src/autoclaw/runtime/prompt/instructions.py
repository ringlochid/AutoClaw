from __future__ import annotations

from autoclaw.runtime.contracts import (
    NodeKind,
    PromptFamily,
    PromptRenderRequest,
    validate_prompt_family_for_node_kind,
)
from autoclaw.runtime.prompt.asset_catalog import load_exact_prompt_block
from autoclaw.runtime.prompt.document import (
    INSTRUCTIONS_SECTION_TITLE,
    PROMPT_FRAGMENT_HEADING_LEVEL,
)
from autoclaw.runtime.prompt.sections.primitives import render_markdown_section
from autoclaw.runtime.prompt.sections.rendering import (
    CURRENT_ONLY_DEFINITION_LOOKUP_GUIDANCE,
    DEFINITION_REVISION_HISTORY_EXCLUSION_GUIDANCE,
)
from autoclaw.runtime.prompt.structural_edit_palette import (
    parent_root_structural_edit_palette,
    structural_edit_palette_lines,
)

_FULL_PROMPT_INSTRUCTION_BLOCK_IDS = {
    PromptFamily.WORKER_DISPATCH: (
        "autoclaw_system_block_v1",
        "runtime_concept_glossary_v1",
        "runtime_read_order_rule_v1",
        "artifact_render_rule_v1",
        "task_memory_rule_v1",
        "monitoring_not_task_truth_v1",
        "autoclaw_provider_continuity_block_v1",
        "worker_dispatch_opening_v1",
        "worker_assignment_doctrine_v1",
        "checkpoint_authoring_guide_v1",
        "runtime_boundary_rule_block_v1",
        "runtime_legality_block_worker_v1",
    ),
    PromptFamily.PARENT_ROOT_DISPATCH: (
        "autoclaw_system_block_v1",
        "runtime_concept_glossary_v1",
        "runtime_read_order_rule_v1",
        "artifact_render_rule_v1",
        "task_memory_rule_v1",
        "monitoring_not_task_truth_v1",
        "autoclaw_provider_continuity_block_v1",
        "parent_root_dispatch_opening_v1",
        "parent_root_orchestration_doctrine_v1",
        "parent_root_assignment_guide_v1",
        "checkpoint_authoring_guide_v1",
        "runtime_boundary_rule_block_v1",
        "runtime_legality_block_parent_v1",
    ),
}


def render_prompt_instructions(request: PromptRenderRequest) -> str:
    block_ids = _instruction_block_ids(
        prompt_family=request.prompt_family,
        node_kind=request.current_node.node_kind,
    )
    exact_blocks = tuple(load_exact_prompt_block(block_id) for block_id in block_ids)
    body = "\n\n".join((*exact_blocks, _render_node_guidance_block(request))).rstrip()
    return render_markdown_section(INSTRUCTIONS_SECTION_TITLE, (body,), level=2) + "\n"


def live_instruction_block_inventory() -> dict[str, dict[str, tuple[str, ...]]]:
    return {
        prompt_family.value: {
            "full_prompt": _full_prompt_instruction_block_ids(prompt_family),
        }
        for prompt_family in PromptFamily
    }


def _full_prompt_instruction_block_ids(prompt_family: PromptFamily) -> tuple[str, ...]:
    return _FULL_PROMPT_INSTRUCTION_BLOCK_IDS[prompt_family]


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
        f"- node kind: {node.node_kind.value}",
        f"- node key: {node.node_key}",
        f"- node description: {node.node_description}",
        f"- role: {node.role_key}",
        f"- role description: {node.role_description}",
    ]
    if node.node_instruction is not None:
        lines.append(f"- node instruction: {node.node_instruction}")
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
    return render_markdown_section(
        "Current Node Guidance",
        lines,
        level=PROMPT_FRAGMENT_HEADING_LEVEL,
    )
