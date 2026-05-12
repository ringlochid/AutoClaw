from __future__ import annotations

from ...extract import normalize_whitespace
from ...load import RenderedPromptOutputLike, load_exact_prompt_block
from ...render import render_live_prompt_outputs


def run_runtime_render_checks(errors: list[str]) -> None:
    prompt_outputs = render_live_prompt_outputs()
    worker_prompt = prompt_outputs["worker_dispatch_prompt"]
    parent_prompt = prompt_outputs["parent_root_dispatch_prompt"]
    same_session_prompt = prompt_outputs["parent_root_dispatch_prompt same_session_continue"]

    exact_blocks = {
        "system": load_exact_prompt_block("autoclaw_system_block_v1"),
        "provider": load_exact_prompt_block("autoclaw_provider_continuity_block_v1"),
        "split": load_exact_prompt_block("autoclaw_parent_worker_split_v1"),
        "boundary": load_exact_prompt_block("runtime_boundary_rule_block_v1"),
        "worker_legality": load_exact_prompt_block("runtime_legality_block_worker_v1"),
        "parent_legality": load_exact_prompt_block("runtime_legality_block_parent_v1"),
        "wrapper": load_exact_prompt_block("autoclaw_same_session_continue_wrapper_v1"),
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
    _validate_same_session_prompt(
        same_session_prompt,
        wrapper_block=exact_blocks["wrapper"],
        errors=errors,
    )
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


def _validate_same_session_prompt(
    same_session_prompt: RenderedPromptOutputLike,
    *,
    wrapper_block: str,
    errors: list[str],
) -> None:
    if same_session_prompt.instructions_text is not None:
        errors.append("live same_session_continue instructions_text should be null")
    if not same_session_prompt.input_text.startswith(wrapper_block):
        errors.append("live same_session_continue input is missing the exact wrapper prefix")
    if "## Operating Model" in same_session_prompt.input_text:
        errors.append(
            "live same_session_continue input still includes the static Operating Model section"
        )
    for heading in (
        "## Current Dispatch",
        "## Workflow Manifest",
        "## Current Assignment",
        "## Latest Checkpoint Context",
        "## Consumed Durable Refs",
        "## Transient Refs",
        "## Task Memory",
        "## Allowed Actions Now",
        "## Publication Rule",
    ):
        if heading not in same_session_prompt.input_text:
            errors.append(
                f"live same_session_continue input is missing non-static section `{heading}`"
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
