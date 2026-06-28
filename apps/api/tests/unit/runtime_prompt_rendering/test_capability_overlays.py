from __future__ import annotations

from pathlib import Path

from autoclaw.runtime import PromptSendMode
from autoclaw.runtime.contracts import EffectiveCapabilitySet, HumanRequestCapabilitySet
from autoclaw.runtime.contracts.primitives import CapabilityDecision
from autoclaw.runtime.prompt import load_exact_prompt_block, render_prompt_bundle

from .support import extract_section, normalize_whitespace, worker_request


def _instruction_block_positions(
    instructions_text: str,
    *blocks: str,
) -> list[int]:
    normalized_instructions = normalize_whitespace(instructions_text)
    return [normalized_instructions.index(normalize_whitespace(block)) for block in blocks]


def test_capabilities_now_overlay_surfaces_explicit_decisions(tmp_path: Path) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT).model_copy(
        update={
            "effective_capabilities": EffectiveCapabilitySet(
                execution_scope="dispatch",
                human_request=HumanRequestCapabilitySet(review=CapabilityDecision.ALLOW),
                command_run=CapabilityDecision.ALLOW,
            )
        }
    )
    bundle = render_prompt_bundle(request)

    capabilities_section = extract_section(
        bundle.full_markdown,
        "### Capabilities Now",
        "### Workflow Manifest",
    )

    assert "controller-owned effective capability set for this dispatch is authoritative" in (
        capabilities_section
    )
    assert "generic adapter approval prompts" in capabilities_section
    assert "- human_request.direction: deny" in capabilities_section
    assert "- human_request.approval: deny" in capabilities_section
    assert "- human_request.input: deny" in capabilities_section
    assert "- human_request.review: allow" in capabilities_section
    assert "- command_run: allow" in capabilities_section
    assert "next legal action:" not in capabilities_section
    assert "choose_an_allowed_human_request_kind" not in capabilities_section
    assert bundle.instructions_text is not None
    assert "### Human Request Use Guide" in bundle.instructions_text
    assert "Use `open_human_request` only when the current effective capability allows" in (
        bundle.instructions_text
    )
    assert "### Command Run Use Guide" in bundle.instructions_text
    assert "expected to exceed about two minutes" in bundle.instructions_text


def test_capability_instruction_overlays_render_independently(tmp_path: Path) -> None:
    base_request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)

    no_capability_bundle = render_prompt_bundle(base_request)
    assert no_capability_bundle.instructions_text is not None
    assert "### Human Request Use Guide" not in no_capability_bundle.instructions_text
    assert "### Command Run Use Guide" not in no_capability_bundle.instructions_text

    human_only_bundle = render_prompt_bundle(
        base_request.model_copy(
            update={
                "effective_capabilities": EffectiveCapabilitySet(
                    execution_scope="dispatch",
                    human_request=HumanRequestCapabilitySet(
                        direction=CapabilityDecision.ALLOW,
                    ),
                    command_run=CapabilityDecision.DENY,
                )
            }
        )
    )
    assert human_only_bundle.instructions_text is not None
    assert "### Human Request Use Guide" in human_only_bundle.instructions_text
    assert "### Command Run Use Guide" not in human_only_bundle.instructions_text

    command_only_bundle = render_prompt_bundle(
        base_request.model_copy(
            update={
                "effective_capabilities": EffectiveCapabilitySet(
                    execution_scope="dispatch",
                    command_run=CapabilityDecision.ALLOW,
                )
            }
        )
    )
    assert command_only_bundle.instructions_text is not None
    assert "### Human Request Use Guide" not in command_only_bundle.instructions_text
    assert "### Command Run Use Guide" in command_only_bundle.instructions_text

    both_bundle = render_prompt_bundle(
        base_request.model_copy(
            update={
                "effective_capabilities": EffectiveCapabilitySet(
                    execution_scope="dispatch",
                    human_request=HumanRequestCapabilitySet(
                        review=CapabilityDecision.ALLOW,
                    ),
                    command_run=CapabilityDecision.ALLOW,
                )
            }
        )
    )
    assert both_bundle.instructions_text is not None
    overlay_positions = _instruction_block_positions(
        both_bundle.instructions_text,
        load_exact_prompt_block("human_request_use_guide_v1"),
        load_exact_prompt_block("command_run_use_guide_v1"),
    )
    assert overlay_positions == sorted(overlay_positions)


def test_capabilities_now_overlay_uses_readable_command_run_denial(tmp_path: Path) -> None:
    request = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    bundle = render_prompt_bundle(request)

    capabilities_section = extract_section(
        bundle.full_markdown,
        "### Capabilities Now",
        "### Workflow Manifest",
    )

    assert "choose_an_allowed_human_request_kind" not in capabilities_section
    assert "run_short_command_inline" not in capabilities_section
    assert "next legal action: avoid long command" in capabilities_section
    assert "run focused tests one by one rather than the whole test suite" in (capabilities_section)
