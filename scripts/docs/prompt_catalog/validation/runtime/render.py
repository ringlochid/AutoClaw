from __future__ import annotations

from scripts.docs.prompt_catalog.extract import normalize_whitespace
from scripts.docs.prompt_catalog.load import RenderedPromptOutputLike, load_exact_prompt_block
from scripts.docs.prompt_catalog.render import render_live_prompt_outputs


def run_runtime_render_checks(errors: list[str]) -> None:
    prompt_outputs = render_live_prompt_outputs()
    worker_prompt = prompt_outputs["worker_dispatch_prompt"]
    parent_prompt = prompt_outputs["parent_root_dispatch_prompt"]

    exact_blocks = {
        "system": load_exact_prompt_block("autoclaw_system_block_v1"),
        "provider": load_exact_prompt_block("autoclaw_provider_continuity_block_v1"),
        "split": load_exact_prompt_block("autoclaw_parent_worker_split_v1"),
        "boundary": load_exact_prompt_block("runtime_boundary_rule_block_v1"),
        "worker_legality": load_exact_prompt_block("runtime_legality_block_worker_v1"),
        "parent_legality": load_exact_prompt_block("runtime_legality_block_parent_v1"),
    }

    _validate_instruction_block_order(
        worker_prompt,
        prompt_name="worker",
        legality_block=exact_blocks["worker_legality"],
        exact_blocks=exact_blocks,
        errors=errors,
    )
    _validate_instruction_block_order(
        parent_prompt,
        prompt_name="parent",
        legality_block=exact_blocks["parent_legality"],
        exact_blocks=exact_blocks,
        errors=errors,
    )
    _validate_worker_instruction_rules(worker_prompt, errors)
    _validate_dispatch_local_node_tool_context(worker_prompt, parent_prompt, errors)
    _validate_assignment_claim_reduction(worker_prompt, errors)


def _validate_instruction_block_order(
    prompt_output: RenderedPromptOutputLike,
    *,
    prompt_name: str,
    legality_block: str,
    exact_blocks: dict[str, str],
    errors: list[str],
) -> None:
    if prompt_output.instructions_text is None:
        errors.append(f"live {prompt_name} instructions_text is unexpectedly null for full_prompt")
        return

    normalized_instructions = normalize_whitespace(prompt_output.instructions_text)
    ordered_blocks = (
        exact_blocks["system"],
        exact_blocks["provider"],
        exact_blocks["split"],
        exact_blocks["boundary"],
        legality_block,
    )
    try:
        positions = [
            normalized_instructions.index(normalize_whitespace(block)) for block in ordered_blocks
        ]
    except ValueError as exc:
        errors.append(f"live {prompt_name} instructions_text is missing an exact block: {exc}")
        return

    if positions != sorted(positions):
        errors.append(
            f"live {prompt_name} instructions_text renders exact blocks out of canonical order"
        )


def _validate_worker_instruction_rules(
    worker_prompt: RenderedPromptOutputLike,
    errors: list[str],
) -> None:
    worker_instructions = worker_prompt.instructions_text
    if worker_instructions is None:
        errors.append("live worker instructions_text is unexpectedly null for full_prompt")
        return
    if "- node description: Repair the bounded auth-refresh defect." not in worker_instructions:
        errors.append("live worker instructions_text is missing current node description guidance")

    required_rule = normalize_whitespace(
        "Before `green`, `retry`, or `blocked`, call `record_checkpoint` with the "
        "terminal handoff for this attempt."
    )
    if required_rule not in normalize_whitespace(worker_instructions):
        errors.append(
            "live worker instructions_text is missing the terminal checkpoint-before-boundary rule"
        )


def _validate_dispatch_local_node_tool_context(
    worker_prompt: RenderedPromptOutputLike,
    parent_prompt: RenderedPromptOutputLike,
    errors: list[str],
) -> None:
    required_lines = (
        "- task_id for node tools:",
        "- session_key for node tools:",
        "Do not print them in normal output, checkpoint prose, or artifacts.",
    )
    for prompt_name, prompt_output in (
        ("worker", worker_prompt),
        ("parent", parent_prompt),
    ):
        for required_line in required_lines:
            if required_line not in prompt_output.full_markdown:
                errors.append(
                    "live "
                    f"{prompt_name} prompt is missing dispatch-local node tool context "
                    f"`{required_line}`"
                )


def _validate_assignment_claim_reduction(
    worker_prompt: RenderedPromptOutputLike,
    errors: list[str],
) -> None:
    assignment_section = worker_prompt.full_markdown.split("## Current Assignment", maxsplit=1)[
        1
    ].split("## Latest Checkpoint Context", maxsplit=1)[0]

    subsection: str | None = None
    for line in assignment_section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- criteria:"):
            subsection = "criteria"
            continue
        if stripped.startswith("- consumes:"):
            subsection = "consumes"
            continue
        if stripped.startswith("- produces:"):
            subsection = "produces"
            continue
        if stripped.startswith("- transient_refs:") or stripped.startswith(
            "- task_memory_search_hints:"
        ):
            subsection = None
            continue
        if subsection in {"criteria", "consumes", "produces"} and (
            stripped.startswith("- path:")
            or stripped.startswith("path:")
            or stripped.startswith("- version:")
            or stripped.startswith("version:")
        ):
            errors.append(
                "live Current Assignment still leaks path/version metadata into reduced "
                "durable claims"
            )
            return
