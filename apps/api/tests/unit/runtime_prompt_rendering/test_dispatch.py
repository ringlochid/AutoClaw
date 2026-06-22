from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.runtime import PromptFamily, PromptSendMode, PromptTransportRequest
from autoclaw.runtime.prompt import (
    list_exact_prompt_block_assets,
    load_exact_prompt_block,
    render_prompt_bundle,
)

from .support import (
    extract_section,
    non_root_parent_request,
    normalize_whitespace,
    parent_request,
    section_index,
    worker_request,
)


def test_render_prompt_bundle_keeps_canonical_section_order(tmp_path: Path) -> None:
    full_prompt = render_prompt_bundle(
        worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )

    ordered_headings = [
        "## Operating Model",
        "## Task Identity",
        "## Node Purpose",
        "## Current Dispatch",
        "## Workflow Manifest",
        "## Current Assignment",
        "## Latest Checkpoint Context",
        "## Consumed Durable Refs",
        "## Transient Refs",
        "## Task Memory",
        "## Allowed Actions Now",
        "## Publication Rule",
    ]
    assert [
        section_index(full_prompt.full_markdown, heading) for heading in ordered_headings
    ] == sorted(section_index(full_prompt.full_markdown, heading) for heading in ordered_headings)
    assert full_prompt.input_text == full_prompt.full_markdown
    assert full_prompt.full_markdown.startswith("## Operating Model")


def test_full_prompt_transport_request_requires_instructions_text() -> None:
    with pytest.raises(
        ValueError,
        match="full_prompt transport requests require instructions_text",
    ):
        PromptTransportRequest(
            send_mode=PromptSendMode.FULL_PROMPT,
            input_text="Current dispatch body.",
        )


def test_instructions_text_assembles_system_provider_and_worker_blocks(tmp_path: Path) -> None:
    worker_bundle = render_prompt_bundle(
        worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )
    parent_bundle = render_prompt_bundle(
        parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )

    system_block = load_exact_prompt_block("autoclaw_system_block_v1")
    provider_block = load_exact_prompt_block("autoclaw_provider_continuity_block_v1")
    split_block = load_exact_prompt_block("autoclaw_parent_worker_split_v1")
    boundary_block = load_exact_prompt_block("runtime_boundary_rule_block_v1")
    worker_legality_block = load_exact_prompt_block("runtime_legality_block_worker_v1")
    parent_legality_block = load_exact_prompt_block("runtime_legality_block_parent_v1")

    assert worker_bundle.instructions_text is not None
    assert parent_bundle.instructions_text is not None
    normalized_worker_instructions = normalize_whitespace(worker_bundle.instructions_text)
    normalized_parent_instructions = normalize_whitespace(parent_bundle.instructions_text)
    worker_positions = [
        normalized_worker_instructions.index(normalize_whitespace(system_block)),
        normalized_worker_instructions.index(normalize_whitespace(provider_block)),
        normalized_worker_instructions.index(normalize_whitespace(split_block)),
        normalized_worker_instructions.index(normalize_whitespace(boundary_block)),
        normalized_worker_instructions.index(normalize_whitespace(worker_legality_block)),
    ]
    parent_positions = [
        normalized_parent_instructions.index(normalize_whitespace(system_block)),
        normalized_parent_instructions.index(normalize_whitespace(provider_block)),
        normalized_parent_instructions.index(normalize_whitespace(split_block)),
        normalized_parent_instructions.index(normalize_whitespace(boundary_block)),
        normalized_parent_instructions.index(normalize_whitespace(parent_legality_block)),
    ]
    assert worker_positions == sorted(worker_positions)
    assert parent_positions == sorted(parent_positions)
    assert (
        "- node description: Repair the bounded auth-refresh defect."
        in worker_bundle.instructions_text
    )
    assert (
        "- node description: Coordinate the whole flow and decide the next bounded child step."
        in parent_bundle.instructions_text
    )
    assert "registry read lane" not in normalized_parent_instructions
    assert "definition registry/tool read surface" not in normalized_parent_instructions
    assert (
        "`autoclaw-node__search_definitions` / `autoclaw-node__get_definition`"
        in parent_bundle.instructions_text
    )
    assert "read-only lookup lane before guessing" in parent_bundle.instructions_text
    assert (
        "Your primary job on a parent/root turn is to prepare the next child or "
        "release decision from current evidence."
        in parent_bundle.instructions_text
    )
    assert (
        "Use bounded research to improve delegation quality" in parent_bundle.instructions_text
    )
    assert (
        "Research is for writing a better child assignment, not for quietly doing "
        "the child's implementation in place." in parent_bundle.instructions_text
    )
    assert (
        "- parent/root focus: understand the task, do only bounded research, "
        "and turn that into a tighter child assignment plus the right surfaced refs"
        in parent_bundle.instructions_text
    )
    assert (
        "- if you start solving the child task in place, step back and improve "
        "the child brief unless delegation is clearly the wrong tool"
        in parent_bundle.instructions_text
    )
    assert (
        "If the surfaced manifest, assignment, checkpoints, and current refs are still "
        "insufficient, do more bounded inspection" in parent_bundle.instructions_text
    )
    assert "doing direct implementation work yourself" not in parent_bundle.instructions_text
    assert "Your first duty on a parent/root turn is orchestration" not in (
        parent_bundle.instructions_text
    )
    assert "do not use definition revision history as dispatched planning input" in (
        parent_bundle.instructions_text
    )
    assert (
        "use only role and policy names from the surfaced structural edit palette"
        not in parent_bundle.instructions_text
    )
    assert (
        "role and policy names must come only from the surfaced structural edit palette"
        not in parent_bundle.instructions_text
    )
    assert "list_definition_versions" not in parent_bundle.instructions_text


def test_exact_prompt_blocks_load_from_packaged_assets_not_prompt_docs() -> None:
    assets = list_exact_prompt_block_assets()

    assert assets
    assert all(asset.asset_path.endswith(".txt") for asset in assets)
    assert all(not asset.asset_path.endswith(".md") for asset in assets)
    assert all(asset.mirror_doc.endswith(".md") for asset in assets)

    system_asset = next(asset for asset in assets if asset.id == "autoclaw_system_block_v1")
    assert system_asset.asset_path == "blocks/autoclaw_system_block_v1.txt"
    assert system_asset.mirror_doc == "prompt-pack/system-and-provider-block.md"
    assert load_exact_prompt_block(system_asset.id).startswith(
        "You are AutoClaw, a delegated node inside a controller-first runtime."
    )


def test_current_dispatch_uses_exact_worker_and_parent_boundary_wording(tmp_path: Path) -> None:
    worker_request_model = worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    parent_request_model = parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    worker_bundle = render_prompt_bundle(worker_request_model)
    parent_bundle = render_prompt_bundle(parent_request_model)

    worker_dispatch = extract_section(
        worker_bundle.full_markdown,
        "## Current Dispatch",
        "## Workflow Manifest",
    )
    parent_dispatch = extract_section(
        parent_bundle.full_markdown,
        "## Current Dispatch",
        "## Workflow Manifest",
    )

    assert "- current bound turn: current worker turn (internal dispatch id hidden)" in (
        worker_dispatch
    )
    assert "- send mode: full_prompt" in worker_dispatch
    assert (
        "- closure expectation: call `autoclaw-node__record_checkpoint`, then emit "
        "`green | retry | blocked`" in worker_dispatch
    )
    assert "- current bound turn: current root turn (internal dispatch id hidden)" in (
        parent_dispatch
    )
    assert "- send mode: full_prompt" in parent_dispatch
    assert (
        "- closure expectation: use control tools now, call "
        "`autoclaw-node__record_checkpoint` if the reasoning must persist, then later emit "
        "`yield` or a terminal boundary" in parent_dispatch
    )
    assert f"- task_id for node tools: {worker_request_model.task_id}" in worker_dispatch
    assert f"- session_key for node tools: {worker_request_model.session_key}" in worker_dispatch
    assert f"- task_id for node tools: {parent_request_model.task_id}" in parent_dispatch
    assert f"- session_key for node tools: {parent_request_model.session_key}" in parent_dispatch
    assert "`autoclaw-node__*` prefix" in worker_dispatch
    assert "Do not print them in normal output, checkpoint prose, or artifacts." in worker_dispatch
    assert "X-Autoclaw-Session-Key" not in worker_dispatch
    assert "X-Autoclaw-Session-Key" not in parent_dispatch


def test_parent_allowed_actions_stay_palette_first_and_allow_current_only_lookup(
    tmp_path: Path,
) -> None:
    bundle = render_prompt_bundle(parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT))

    allowed_actions_section = extract_section(
        bundle.full_markdown,
        "## Allowed Actions Now",
        "## Publication Rule",
    )

    assert "registry read lane" not in allowed_actions_section
    assert "definition registry" not in allowed_actions_section
    assert (
        "start with role/policy names from the surfaced structural edit palette in "
        "this prompt or manifest" in allowed_actions_section
    )
    assert (
        "role/policy names only from the surfaced structural edit palette in this "
        "prompt or manifest" not in allowed_actions_section
    )
    assert (
        "if the surfaced structural edit palette is still insufficient after reread, "
        "use the current-only `autoclaw-node__search_definitions` / "
        "`autoclaw-node__get_definition` read-only lookup lane before guessing"
        in allowed_actions_section
    )
    assert (
        "do bounded research to sharpen delegation: read only the minimum "
        "additional workspace, context, or source files needed to understand "
        "the task, choose the right refs, and tighten the next child brief"
        in allowed_actions_section
    )
    assert (
        "make the child brief specific about: the exact objective or question, "
        "scope boundaries and what not to touch, and the key surfaced refs and "
        "constraints" in allowed_actions_section
    )
    assert (
        "research is for better assignment quality; if you are drifting into "
        "doing the child task yourself, step back and improve the child brief "
        "unless delegation is clearly the wrong tool" in allowed_actions_section
    )
    assert (
        "reassign the same child for another bounded delta when the same role still fits"
        in allowed_actions_section
    )
    assert (
        "assign a different specialist child when the work type changed"
        in allowed_actions_section
    )
    assert "use structural edits when the subtree shape itself is wrong" in (
        allowed_actions_section
    )
    assert (
        "proactively use the current-only `autoclaw-node__search_definitions` / "
        "`autoclaw-node__get_definition` read-only lookup lane to inspect "
        "available roles or policies"
        in allowed_actions_section
    )
    assert (
        "if the needed role/policy name is still not surfaced after palette reread "
        "and current-only lookup" in allowed_actions_section
    )
    assert (
        "do not use definition revision history as dispatched planning input"
        in allowed_actions_section
    )
    assert (
        "if the surfaced manifest, assignment, checkpoints, and current refs "
        "are still insufficient, do more bounded inspection aimed at writing a "
        "tighter child assignment or making a release or routing decision; stop "
        "once you have enough to choose the next move well" in allowed_actions_section
    )
    assert "doing direct implementation work yourself" not in allowed_actions_section
    assert "emit `green | blocked`" not in allowed_actions_section
    assert "list_definition_versions" not in allowed_actions_section
    assert (
        "emit `green` only when this root node is closing its own current assignment; "
        "emit `blocked` only for root whole-flow terminal closure after committed "
        "`release_blocked`" in allowed_actions_section
    )


def test_parent_prompt_surfaces_structural_edit_palette_in_manifest_and_instructions(
    tmp_path: Path,
) -> None:
    bundle = render_prompt_bundle(parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT))

    workflow_manifest_section = extract_section(
        bundle.full_markdown,
        "## Workflow Manifest",
        "## Current Assignment",
    )
    assert bundle.instructions_text is not None
    assert "- structural edit palette:" in workflow_manifest_section
    assert "architect (allowed node kinds: worker)" in workflow_manifest_section
    assert "planning_lead (allowed node kinds: parent, worker)" in workflow_manifest_section
    assert "standard-parent-planning (applies_to: parent)" in workflow_manifest_section
    assert "standard-review (applies_to: worker)" in workflow_manifest_section
    assert "- structural edit palette:" in bundle.instructions_text
    assert "architect (allowed node kinds: worker)" in bundle.instructions_text
    assert "standard-parent-planning (applies_to: parent)" in bundle.instructions_text


def test_non_root_parent_prompt_excludes_root_only_actions_and_blocked_closure(
    tmp_path: Path,
) -> None:
    bundle = render_prompt_bundle(
        non_root_parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )

    allowed_actions_section = extract_section(
        bundle.full_markdown,
        "## Allowed Actions Now",
        "## Publication Rule",
    )

    assert (
        "- tools: `autoclaw-node__assign_child`, `autoclaw-node__add_child`, "
        "`autoclaw-node__update_child`, `autoclaw-node__remove_child`, "
        "`autoclaw-node__release_green`, `autoclaw-node__release_blocked`, "
        "`autoclaw-node__record_checkpoint`"
    ) not in allowed_actions_section
    assert "choose a legal blocked path" not in allowed_actions_section
    assert "emit `green | blocked`" not in allowed_actions_section
    assert "emit `green` only when this parent node is closing its own current assignment" in (
        allowed_actions_section
    )


def test_worker_prompt_rejects_root_node_family_mismatch(tmp_path: Path) -> None:
    request = parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT).model_copy(
        update={"prompt_family": PromptFamily.WORKER_DISPATCH}
    )

    with pytest.raises(ValueError, match="worker_dispatch_prompt"):
        render_prompt_bundle(request)
