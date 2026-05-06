from __future__ import annotations

from app.runtime.contracts import (
    NodeKind,
    PromptFamily,
    PromptRenderRequest,
    PromptSendMode,
    validate_prompt_family_for_node_kind,
)
from app.runtime.prompt.asset_catalog import load_exact_prompt_block

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
_SAME_SESSION_WRAPPER_BLOCK_IDS = ("autoclaw_same_session_continue_wrapper_v1",)


def _full_prompt_instruction_block_ids(prompt_family: PromptFamily) -> tuple[str, ...]:
    return (
        *_COMMON_FULL_PROMPT_BLOCK_IDS,
        _FULL_PROMPT_LEGALITY_BLOCK_IDS[prompt_family],
    )


def _instruction_block_ids(
    *,
    prompt_family: PromptFamily,
    send_mode: PromptSendMode,
    node_kind: NodeKind,
) -> tuple[str, ...]:
    validate_prompt_family_for_node_kind(
        prompt_family=prompt_family,
        node_kind=node_kind,
    )
    if send_mode == PromptSendMode.SAME_SESSION_CONTINUE:
        return _SAME_SESSION_WRAPPER_BLOCK_IDS
    return _full_prompt_instruction_block_ids(prompt_family)


def live_instruction_block_inventory() -> dict[str, dict[str, tuple[str, ...]]]:
    return {
        prompt_family.value: {
            PromptSendMode.FULL_PROMPT.value: _full_prompt_instruction_block_ids(prompt_family),
            PromptSendMode.SAME_SESSION_CONTINUE.value: _SAME_SESSION_WRAPPER_BLOCK_IDS,
        }
        for prompt_family in PromptFamily
    }


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
    return "\n".join(lines)


def render_prompt_instructions(request: PromptRenderRequest) -> str:
    block_ids = _instruction_block_ids(
        prompt_family=request.prompt_family,
        send_mode=request.send_mode,
        node_kind=request.current_node.node_kind,
    )
    exact_blocks = tuple(load_exact_prompt_block(block_id) for block_id in block_ids)
    if request.send_mode == PromptSendMode.SAME_SESSION_CONTINUE:
        return exact_blocks[0]
    return "\n\n".join((*exact_blocks, _render_node_guidance_block(request)))
