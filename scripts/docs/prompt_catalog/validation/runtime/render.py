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
        "concept_glossary": load_exact_prompt_block("runtime_concept_glossary_v1"),
        "read_order": load_exact_prompt_block("runtime_read_order_rule_v1"),
        "artifact_rule": load_exact_prompt_block("artifact_render_rule_v1"),
        "task_memory_rule": load_exact_prompt_block("task_memory_rule_v1"),
        "monitoring_rule": load_exact_prompt_block("monitoring_not_task_truth_v1"),
        "provider": load_exact_prompt_block("autoclaw_provider_continuity_block_v1"),
        "worker_opening": load_exact_prompt_block("worker_dispatch_opening_v1"),
        "parent_opening": load_exact_prompt_block("parent_root_dispatch_opening_v1"),
        "parent_current_assignment_doctrine": load_exact_prompt_block(
            "parent_root_current_assignment_doctrine_v1"
        ),
        "parent_child_assignment_guide": load_exact_prompt_block(
            "parent_root_child_assignment_writing_guide_v1"
        ),
        "checkpoint_guide": load_exact_prompt_block("checkpoint_authoring_guide_v1"),
        "boundary": load_exact_prompt_block("runtime_boundary_rule_block_v1"),
        "worker_legality": load_exact_prompt_block("runtime_legality_block_worker_v1"),
        "parent_legality": load_exact_prompt_block("runtime_legality_block_parent_v1"),
    }

    _validate_instruction_block_order(
        worker_prompt,
        prompt_name="worker",
        ordered_blocks=(
            exact_blocks["system"],
            exact_blocks["concept_glossary"],
            exact_blocks["read_order"],
            exact_blocks["artifact_rule"],
            exact_blocks["task_memory_rule"],
            exact_blocks["monitoring_rule"],
            exact_blocks["provider"],
            exact_blocks["worker_opening"],
            exact_blocks["checkpoint_guide"],
            exact_blocks["boundary"],
            exact_blocks["worker_legality"],
        ),
        errors=errors,
    )
    _validate_instruction_block_order(
        parent_prompt,
        prompt_name="parent",
        ordered_blocks=(
            exact_blocks["system"],
            exact_blocks["concept_glossary"],
            exact_blocks["read_order"],
            exact_blocks["artifact_rule"],
            exact_blocks["task_memory_rule"],
            exact_blocks["monitoring_rule"],
            exact_blocks["provider"],
            exact_blocks["parent_opening"],
            exact_blocks["parent_current_assignment_doctrine"],
            exact_blocks["parent_child_assignment_guide"],
            exact_blocks["checkpoint_guide"],
            exact_blocks["boundary"],
            exact_blocks["parent_legality"],
        ),
        errors=errors,
    )
    _validate_worker_instruction_rules(worker_prompt, errors)
    _validate_parent_instruction_rules(parent_prompt, errors)
    _validate_dispatch_local_node_tool_context(worker_prompt, parent_prompt, errors)
    _validate_assignment_claim_reduction(worker_prompt, errors)


def _validate_instruction_block_order(
    prompt_output: RenderedPromptOutputLike,
    *,
    prompt_name: str,
    ordered_blocks: tuple[str, ...],
    errors: list[str],
) -> None:
    if prompt_output.instructions_text is None:
        errors.append(f"live {prompt_name} instructions_text is unexpectedly null for full_prompt")
        return

    normalized_instructions = normalize_whitespace(prompt_output.instructions_text)
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
    checkpoint_quality_rule = normalize_whitespace(
        "Treat every checkpoint as a durable handoff, not a diary entry or polished status report."
    )
    if checkpoint_quality_rule not in normalize_whitespace(worker_instructions):
        errors.append(
            "live worker instructions_text is missing the durable-checkpoint-quality guidance"
        )


def _validate_parent_instruction_rules(
    parent_prompt: RenderedPromptOutputLike,
    errors: list[str],
) -> None:
    parent_instructions = parent_prompt.instructions_text
    if parent_instructions is None:
        errors.append("live parent instructions_text is unexpectedly null for full_prompt")
        return

    required_rules = (
        "Read the current assignment as the scope contract for the subtree you own now.",
        "Write the child brief as an acquisition plan, not just loose assignment prose.",
        "Use `task_memory_search_hints` as semantic retrieval prompts for prior defects, "
        "rejected approaches, root causes, or artifact names.",
    )
    normalized_parent_instructions = normalize_whitespace(parent_instructions)
    for rule in required_rules:
        if normalize_whitespace(rule) not in normalized_parent_instructions:
            errors.append(f"live parent instructions_text is missing expected rule: {rule}")


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
    assignment_section = worker_prompt.full_markdown.split("### Current Assignment", maxsplit=1)[
        1
    ].split("### Latest Checkpoint Context", maxsplit=1)[0]

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
