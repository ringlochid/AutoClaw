from __future__ import annotations

from pathlib import Path

import pytest
from app.runtime.contracts import PromptFamily, PromptSendMode, PromptTransportRequest
from app.runtime.prompt.asset_catalog import (
    list_exact_prompt_block_assets,
    load_exact_prompt_block,
)
from app.runtime.prompt.bundle import render_prompt_bundle
from tests.unit.test_runtime_prompt_rendering_support import (
    extract_section,
    normalize_whitespace,
    parent_request,
    section_index,
    worker_request,
)


def test_render_prompt_bundle_keeps_section_order_and_omits_only_static_sections(
    tmp_path: Path,
) -> None:
    full_prompt = render_prompt_bundle(
        worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )
    same_session = render_prompt_bundle(
        worker_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
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
    assert "## Operating Model" not in same_session.input_text
    assert "## Task Identity" not in same_session.input_text
    assert "## Node Purpose" not in same_session.input_text
    assert "## Current Dispatch" in same_session.input_text
    assert "## Consumed Durable Refs" in same_session.input_text
    assert "## Transient Refs" in same_session.input_text
    assert "## Task Memory" in same_session.input_text
    assert "## Allowed Actions Now" in same_session.input_text
    assert "send mode: same_session_continue" in same_session.full_markdown
    assert same_session.full_markdown.startswith("## Operating Model")


def test_same_session_transport_uses_exact_wrapper_asset(tmp_path: Path) -> None:
    worker_bundle = render_prompt_bundle(
        worker_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
    )
    parent_bundle = render_prompt_bundle(
        parent_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
    )

    wrapper_block = load_exact_prompt_block("autoclaw_same_session_continue_wrapper_v1")
    system_block = load_exact_prompt_block("autoclaw_system_block_v1")

    assert worker_bundle.instructions_text is None
    assert parent_bundle.instructions_text is None
    assert worker_bundle.input_text.startswith(wrapper_block)
    assert parent_bundle.input_text.startswith(wrapper_block)
    assert system_block not in worker_bundle.input_text
    assert system_block not in parent_bundle.input_text


def test_same_session_transport_request_requires_previous_response_id() -> None:
    with pytest.raises(
        ValueError,
        match="same_session_continue transport requests require previous_response_id",
    ):
        PromptTransportRequest(
            send_mode=PromptSendMode.SAME_SESSION_CONTINUE,
            input_text="Current same-attempt continuation body.",
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
    worker_bundle = render_prompt_bundle(
        worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT)
    )
    parent_bundle = render_prompt_bundle(
        parent_request(tmp_path, send_mode=PromptSendMode.SAME_SESSION_CONTINUE)
    )

    worker_dispatch = extract_section(
        worker_bundle.full_markdown,
        "## Current Dispatch",
        "## Workflow Manifest",
    )
    parent_dispatch = extract_section(
        parent_bundle.input_text,
        "## Current Dispatch",
        "## Workflow Manifest",
    )

    assert "- current bound turn: current worker turn (internal dispatch id hidden)" in (
        worker_dispatch
    )
    assert (
        "- closure expectation: call `record_checkpoint`, then emit `green | retry | blocked`"
        in worker_dispatch
    )
    assert "- current bound turn: same-attempt root continuation (internal dispatch id hidden)" in (
        parent_dispatch
    )
    assert (
        "- closure expectation: use control tools now, call `record_checkpoint` if the "
        "reasoning must persist, then later emit `yield` or a terminal boundary" in parent_dispatch
    )


def test_parent_allowed_actions_do_not_depend_on_registry_read_lane(tmp_path: Path) -> None:
    bundle = render_prompt_bundle(parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT))

    allowed_actions_section = extract_section(
        bundle.full_markdown,
        "## Allowed Actions Now",
        "## Publication Rule",
    )

    assert "registry read lane" not in allowed_actions_section
    assert "definition registry" not in allowed_actions_section
    assert "role/policy names already surfaced in the current prompt or manifest" in (
        allowed_actions_section
    )
    assert "if the needed role/policy name is still not surfaced after reread" in (
        allowed_actions_section
    )


def test_worker_prompt_rejects_root_node_family_mismatch(tmp_path: Path) -> None:
    request = parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT).model_copy(
        update={"prompt_family": PromptFamily.WORKER_DISPATCH}
    )

    with pytest.raises(ValueError, match="worker_dispatch_prompt"):
        render_prompt_bundle(request)
