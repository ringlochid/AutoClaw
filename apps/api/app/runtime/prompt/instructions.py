from __future__ import annotations

from app.runtime.contracts import NodeKind, PromptRenderRequest, PromptSendMode
from app.runtime.prompt.asset_catalog import load_exact_prompt_block


def _render_system_block() -> str:
    return load_exact_prompt_block("autoclaw_system_block_v1")


def _render_provider_continuity_block() -> str:
    return load_exact_prompt_block("autoclaw_provider_continuity_block_v1")


def _render_parent_worker_split_block() -> str:
    return load_exact_prompt_block("autoclaw_parent_worker_split_v1")


def _render_runtime_boundary_block() -> str:
    return load_exact_prompt_block("runtime_boundary_rule_block_v1")


def _render_runtime_legality_block(node_kind: NodeKind) -> str:
    return load_exact_prompt_block(
        "runtime_legality_block_worker_v1"
        if node_kind == NodeKind.WORKER
        else "runtime_legality_block_parent_v1",
    )


def _render_same_session_continue_wrapper() -> str:
    return load_exact_prompt_block("autoclaw_same_session_continue_wrapper_v1")


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
    if request.send_mode == PromptSendMode.SAME_SESSION_CONTINUE:
        return _render_same_session_continue_wrapper()
    return "\n\n".join(
        (
            _render_system_block(),
            _render_provider_continuity_block(),
            _render_parent_worker_split_block(),
            _render_runtime_boundary_block(),
            _render_runtime_legality_block(request.current_node.node_kind),
            _render_node_guidance_block(request),
        )
    )
