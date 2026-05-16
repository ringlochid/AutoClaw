from __future__ import annotations

from typing import Any

from .examples import (
    render_generated_example_bodies as build_generated_example_bodies,
)
from .examples import render_live_prompt_outputs as build_live_prompt_outputs
from .load import (
    GENERATED_EXAMPLE_SCENARIOS,
    PROMPT_ASSET_DISPLAY_ROOT,
    SECTION_HEADINGS,
    RenderedPromptOutputLike,
    get_exact_prompt_block_asset,
)


def render_live_prompt_outputs() -> dict[str, RenderedPromptOutputLike]:
    return build_live_prompt_outputs()


def render_generated_example_bodies() -> dict[str, str]:
    return build_generated_example_bodies()


def render_inventory_md(data: dict[str, Any]) -> str:
    send_mode_ids = [send_mode["id"] for send_mode in data["send_modes"]]
    lines = [
        "# Generated Prompt Inventory",
        "",
        "Status: Generated reference",
        "",
        "This page inventories the current generated prompt contract surfaces.",
        "Static exact blocks are shipped from app-owned assets under "
        f"`{PROMPT_ASSET_DISPLAY_ROOT}/`, while the prompt-pack docs remain "
        "human-readable mirrors.",
        "",
        "## Canonical Section Order",
        "",
    ]
    for index, section in enumerate(data["section_order"], start=1):
        lines.append(f"{index}. `{section}`")
    lines.extend(["", "## Static Continuation Sections", ""])
    lines.extend(f"- `{section}`" for section in data["static_sections"])
    lines.extend(["", "## Canonical Prompt Families", ""])
    lines.extend(f"- `{family['id']}`" for family in data["prompt_families"])
    lines.extend(["", "## Canonical Send Modes", ""])
    lines.extend(f"- `{send_mode_id}`" for send_mode_id in send_mode_ids)
    lines.extend(["", "## Exact Block Registry", ""])
    for block in data["exact_blocks"]:
        asset = get_exact_prompt_block_asset(block["id"])
        lines.extend(
            [
                f"- `{block['id']}`",
                f"  - asset: `{PROMPT_ASSET_DISPLAY_ROOT}/{asset.asset_path}`",
                f"  - mirror doc: `{block['owner_file']}`",
                f"  - role: `{block['role']}`",
                f"  - consumption: `{block['consumption']}`",
            ]
        )
    lines.extend(["", "## Generated Artifact Registry", ""])
    for artifact in data["generated_artifacts"]:
        lines.extend([f"- `{artifact['id']}`", f"  - file: `{artifact['path']}`"])
    lines.extend(["", "## Generated Example Registry", ""])
    for example in data["generated_examples"]:
        lines.extend(
            [
                f"- `{example['id']}`",
                f"  - rendered heading: `{example['rendered_heading']}`",
                f"  - family: `{example['family']}`",
                f"  - send mode: `{example['send_mode']}`",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_generated_examples_md(data: dict[str, Any]) -> str:
    rendered_examples = render_generated_example_bodies()
    lines = [
        "# Generated Rendered Prompt Examples",
        "",
        "Status: Generated reference",
        "",
        "This page is generated from app-owned prompt assets under "
        f"`{PROMPT_ASSET_DISPLAY_ROOT}/` plus live prompt-render output from "
        "`render_prompt_bundle()`.",
        "If this page drifts from the runtime renderer, regenerate it from "
        "`python -m scripts.docs.prompt_catalog.cli generate` and then rerun validation.",
        "",
    ]
    for example in data["generated_examples"]:
        heading = example["rendered_heading"]
        lines.extend([f"## `{heading}`", "", "Scenario:", ""])
        lines.extend(
            f"- {scenario_line}" for scenario_line in GENERATED_EXAMPLE_SCENARIOS.get(heading, [])
        )
        lines.extend(["", "```text", rendered_examples[heading], "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_inventory_debug(data: dict[str, Any]) -> str:
    send_mode_ids = [
        send_mode["id"]
        for send_mode in data.get("send_modes", [])
        if isinstance(send_mode, dict) and isinstance(send_mode.get("id"), str)
    ]
    lines = [
        "Prompt catalog inventory:",
        f"- version: {data.get('version')}",
        f"- owner docs: {len(data.get('owner_docs', []))}",
        f"- sections: {len(data.get('section_order', []))}",
    ]
    for section in data.get("section_order", []):
        lines.append(f"  - section: {section} -> {SECTION_HEADINGS.get(section, 'UNKNOWN')}")
    lines.append(f"- static sections: {len(data.get('static_sections', []))}")
    lines.extend(f"  - {section}" for section in data.get("static_sections", []))
    lines.append(f"- send modes: {', '.join(send_mode_ids)}")
    lines.append(f"- exact blocks: {len(data.get('exact_blocks', []))}")
    for block in data.get("exact_blocks", []):
        if not isinstance(block, dict):
            continue
        asset_path = "UNKNOWN"
        block_id = block.get("id")
        if isinstance(block_id, str):
            try:
                asset_path = get_exact_prompt_block_asset(block_id).asset_path
            except ValueError:
                asset_path = "MISSING"
        lines.append(
            f"  - {block.get('id')} | asset={asset_path} | owner={block.get('owner_file')} | "
            f"role={block.get('role')} | consumption={block.get('consumption')}"
        )
    lines.append(f"- prompt families: {len(data.get('prompt_families', []))}")
    for family in data.get("prompt_families", []):
        if not isinstance(family, dict):
            continue
        lines.append(
            "  - "
            f"{family.get('id')} | "
            f"send_modes={','.join(family.get('allowed_send_modes', []))} | "
            f"required_sections={','.join(family.get('required_sections', []))}"
        )
    lines.extend(
        [
            f"- generated artifacts: {len(data.get('generated_artifacts', []))}",
            f"- generated examples: {len(data.get('generated_examples', []))}",
            f"- validation references: {len(data.get('validation_references', []))}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
