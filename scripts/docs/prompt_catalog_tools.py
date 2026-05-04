from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
PROMPT_LAYER_ROOT = ROOT / "docs" / "redesign" / "prompt-layer"
CATALOG_PATH = PROMPT_LAYER_ROOT / "prompt-catalog.yaml"
INVENTORY_PATH = PROMPT_LAYER_ROOT / "generated" / "inventory.md"
EXAMPLES_PATH = PROMPT_LAYER_ROOT / "generated" / "rendered-examples.md"
COMPOSITION_PATH = PROMPT_LAYER_ROOT / "composition-example.md"

SECTION_HEADINGS = {
    "operating_model": "Operating Model",
    "task_identity": "Task Identity",
    "node_purpose": "Node Purpose",
    "current_dispatch": "Current Dispatch",
    "workflow_manifest": "Workflow Manifest",
    "current_assignment": "Current Assignment",
    "latest_checkpoint_context": "Latest Checkpoint Context",
    "consumed_durable_refs": "Consumed Durable Refs",
    "transient_refs": "Transient Refs",
    "task_memory": "Task Memory",
    "allowed_actions_now": "Allowed Actions Now",
    "publication_rule": "Publication Rule",
}

CANONICAL_SEND_MODE_IDS = [
    "full_prompt",
    "same_session_continue",
]

LIVE_PROMPT_SURFACE_PATHS = [
    PROMPT_LAYER_ROOT / "README.md",
    PROMPT_LAYER_ROOT / "INDEX.md",
    PROMPT_LAYER_ROOT / "contract.md",
    PROMPT_LAYER_ROOT / "source-and-sections.md",
    PROMPT_LAYER_ROOT / "field-renderers.md",
    PROMPT_LAYER_ROOT / "render-and-persistence.md",
    PROMPT_LAYER_ROOT / "machine-contract.md",
    PROMPT_LAYER_ROOT / "legality-and-coverage.md",
    PROMPT_LAYER_ROOT / "prompt-resource-usage-appendix.md",
    COMPOSITION_PATH,
    PROMPT_LAYER_ROOT / "generated" / "README.md",
    INVENTORY_PATH,
    EXAMPLES_PATH,
    PROMPT_LAYER_ROOT / "prompt-pack" / "README.md",
    PROMPT_LAYER_ROOT / "prompt-pack" / "runtime-rule-blocks.md",
    PROMPT_LAYER_ROOT / "prompt-pack" / "system-and-provider-block.md",
    PROMPT_LAYER_ROOT / "prompt-pack" / "validation-and-reject-blocks.md",
    CATALOG_PATH,
]

EXPECTED_CLOSURE_MODES = {
    "worker_dispatch_prompt": ["green", "retry", "blocked"],
    "parent_root_dispatch_prompt": ["yield", "green", "blocked"],
}


def load_catalog() -> dict[str, Any]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("prompt catalog must be a mapping")
    return data


def _as_string_list(
    value: Any,
    *,
    field_name: str,
    errors: list[str],
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{field_name} must be a list")
        return []
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            errors.append(f"{field_name} entries must be strings")
            return []
        items.append(item)
    if not allow_empty and not items:
        errors.append(f"{field_name} must be non-empty")
    if len(items) != len(set(items)):
        errors.append(f"{field_name} contains duplicates")
    return items


def _owner_doc_paths(owner_docs: list[str]) -> list[Path]:
    return [PROMPT_LAYER_ROOT / owner_doc for owner_doc in owner_docs]


def _extract_markdown_section(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    capture = False
    collected: list[str] = []
    for line in lines:
        if line.strip() == heading:
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture:
            collected.append(line)
    if not capture:
        return None
    return "\n".join(collected)


def _validate_live_prompt_surface_paths(errors: list[str], *, skip_inventory: bool = False) -> None:
    for path in LIVE_PROMPT_SURFACE_PATHS:
        if skip_inventory and path == INVENTORY_PATH:
            continue
        text = path.read_text(encoding="utf-8")
        if "lock_next/" in text or "lock_next\\" in text:
            errors.append(
                f"{path.relative_to(ROOT)} still routes live prompt semantics "
                "to lock_next/"
            )


def _validate_current_assignment_examples(errors: list[str]) -> None:
    example_paths = [
        PROMPT_LAYER_ROOT / "field-renderers.md",
        EXAMPLES_PATH,
        COMPOSITION_PATH,
    ]
    for path in example_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        in_current_assignment = False
        subsection: str | None = None
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped == "Current Assignment":
                in_current_assignment = True
                subsection = None
                continue
            if not in_current_assignment:
                continue
            if stripped in SECTION_HEADINGS.values() and stripped != "Current Assignment":
                in_current_assignment = False
                subsection = None
                continue
            if stripped.startswith("## ") or stripped == "```":
                in_current_assignment = False
                subsection = None
                continue
            if stripped.startswith("- criteria:"):
                subsection = "criteria"
                continue
            if stripped.startswith("- consumes:"):
                subsection = "consumes"
                continue
            if stripped.startswith("- produces:"):
                subsection = "produces"
                continue
            if stripped.startswith("- transient_refs:"):
                subsection = "transient_refs"
                continue
            if stripped.startswith("- task_memory_search_hints:"):
                subsection = "task_memory_search_hints"
                continue
            if subsection in {"criteria", "consumes", "produces"} and (
                stripped.startswith("path:") or stripped.startswith("version:")
            ):
                leaked_field = stripped.split(":", 1)[0]
                errors.append(
                    f"{path.relative_to(ROOT)} leaks `{leaked_field}` into "
                    f"Current Assignment `{subsection}` at line {line_number}"
                )


def _validate_same_session_examples(data: dict[str, Any], errors: list[str]) -> None:
    dynamic_headings = [
        SECTION_HEADINGS[section_id]
        for section_id in data.get("section_order", [])
        if section_id not in data.get("static_sections", [])
    ]
    rendered_examples_text = EXAMPLES_PATH.read_text(encoding="utf-8")
    same_session_examples = [
        example
        for example in data.get("generated_examples", [])
        if isinstance(example, dict) and example.get("send_mode") == "same_session_continue"
    ]
    for example in same_session_examples:
        heading = example.get("rendered_heading")
        if not isinstance(heading, str):
            continue
        section = _extract_markdown_section(rendered_examples_text, f"## `{heading}`")
        if section is None:
            errors.append(f"generated/rendered-examples.md is missing section `## `{heading}``")
            continue
        for heading_text in dynamic_headings:
            if heading_text not in section:
                errors.append(
                    "generated/rendered-examples.md same-session example "
                    f"`{heading}` is missing non-static section `{heading_text}`"
                )

    composition_text = COMPOSITION_PATH.read_text(encoding="utf-8")
    composition_headings = [
        "## Exact assembly: `worker_dispatch_prompt` `same_session_continue`",
        "## Exact assembly: `parent_root_dispatch_prompt` `same_session_continue`",
    ]
    for heading in composition_headings:
        section = _extract_markdown_section(composition_text, heading)
        if section is None:
            errors.append(f"composition-example.md is missing section `{heading}`")
            continue
        for heading_text in dynamic_headings:
            if heading_text not in section:
                errors.append(
                    "composition-example.md same-session example "
                    f"`{heading}` is missing non-static section `{heading_text}`"
                )


def _validate_catalog(data: dict[str, Any], *, skip_inventory_checks: bool = False) -> list[str]:
    errors: list[str] = []

    if data.get("version") != 1:
        errors.append("catalog version must be 1")

    owner_docs = _as_string_list(data.get("owner_docs"), field_name="owner_docs", errors=errors)
    for owner_doc_path in _owner_doc_paths(owner_docs):
        if not owner_doc_path.exists():
            errors.append(f"owner doc is missing: {owner_doc_path.relative_to(ROOT)}")

    section_order = _as_string_list(
        data.get("section_order"),
        field_name="section_order",
        errors=errors,
    )
    unknown_sections = [section for section in section_order if section not in SECTION_HEADINGS]
    if unknown_sections:
        errors.append(f"unknown section ids: {', '.join(unknown_sections)}")

    static_sections = _as_string_list(
        data.get("static_sections"),
        field_name="static_sections",
        errors=errors,
        allow_empty=True,
    )
    for section in static_sections:
        if section not in section_order:
            errors.append(f"static section `{section}` is not in section_order")

    send_modes = data.get("send_modes")
    if not isinstance(send_modes, list) or not send_modes:
        errors.append("send_modes must be a non-empty list of mappings")
        send_modes = []
    send_mode_ids: list[str] = []
    for index, send_mode in enumerate(send_modes):
        prefix = f"send_modes[{index}]"
        if not isinstance(send_mode, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        send_mode_id = send_mode.get("id")
        if not isinstance(send_mode_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        send_mode_ids.append(send_mode_id)
    if len(send_mode_ids) != len(set(send_mode_ids)):
        errors.append("send mode ids contain duplicates")
    if send_mode_ids != CANONICAL_SEND_MODE_IDS:
        errors.append("send mode ids must be exactly [full_prompt, same_session_continue] in order")

    exact_blocks = data.get("exact_blocks")
    if not isinstance(exact_blocks, list) or not exact_blocks:
        errors.append("exact_blocks must be a non-empty list")
        exact_blocks = []
    exact_block_ids: list[str] = []
    for index, block in enumerate(exact_blocks):
        prefix = f"exact_blocks[{index}]"
        if not isinstance(block, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        block_id = block.get("id")
        owner_file = block.get("owner_file")
        role = block.get("role")
        purpose = block.get("purpose")
        if not isinstance(block_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        exact_block_ids.append(block_id)
        if not isinstance(owner_file, str):
            errors.append(f"{prefix}.owner_file must be a string")
        else:
            owner_path = PROMPT_LAYER_ROOT / owner_file
            if not owner_path.exists():
                errors.append(f"{prefix}.owner_file is missing: {owner_path.relative_to(ROOT)}")
            elif block_id not in owner_path.read_text(encoding="utf-8"):
                errors.append(f"{prefix}.owner_file does not mention `{block_id}`")
        if not isinstance(role, str):
            errors.append(f"{prefix}.role must be a string")
        if not isinstance(purpose, str):
            errors.append(f"{prefix}.purpose must be a string")
    if len(exact_block_ids) != len(set(exact_block_ids)):
        errors.append("exact block ids contain duplicates")

    generated_artifacts = data.get("generated_artifacts")
    if not isinstance(generated_artifacts, list) or not generated_artifacts:
        errors.append("generated_artifacts must be a non-empty list")
        generated_artifacts = []
    generated_artifact_ids: list[str] = []
    for index, artifact in enumerate(generated_artifacts):
        prefix = f"generated_artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        artifact_id = artifact.get("id")
        artifact_path = artifact.get("path")
        if not isinstance(artifact_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        generated_artifact_ids.append(artifact_id)
        if not isinstance(artifact_path, str):
            errors.append(f"{prefix}.path must be a string")
        else:
            resolved_path = PROMPT_LAYER_ROOT / artifact_path
            if not resolved_path.exists():
                errors.append(f"{prefix}.path is missing: {resolved_path.relative_to(ROOT)}")
    if len(generated_artifact_ids) != len(set(generated_artifact_ids)):
        errors.append("generated artifact ids contain duplicates")

    generated_examples = data.get("generated_examples")
    if not isinstance(generated_examples, list) or not generated_examples:
        errors.append("generated_examples must be a non-empty list")
        generated_examples = []
    generated_example_ids: list[str] = []
    generated_example_records: list[dict[str, str]] = []
    for index, example in enumerate(generated_examples):
        prefix = f"generated_examples[{index}]"
        if not isinstance(example, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        example_id = example.get("id")
        family = example.get("family")
        send_mode = example.get("send_mode")
        rendered_heading = example.get("rendered_heading")
        source_file = example.get("source_file")
        if not isinstance(example_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        generated_example_ids.append(example_id)
        if not isinstance(rendered_heading, str):
            errors.append(f"{prefix}.rendered_heading must be a string")
            rendered_heading = ""
        if not isinstance(family, str):
            errors.append(f"{prefix}.family must be a string")
            family = ""
        if not isinstance(send_mode, str):
            errors.append(f"{prefix}.send_mode must be a string")
            send_mode = ""
        elif send_mode not in send_mode_ids:
            errors.append(f"{prefix}.send_mode uses unknown send mode `{send_mode}`")
        if not isinstance(source_file, str):
            errors.append(f"{prefix}.source_file must be a string")
        else:
            source_path = PROMPT_LAYER_ROOT / source_file
            if not source_path.exists():
                errors.append(f"{prefix}.source_file is missing: {source_path.relative_to(ROOT)}")
        generated_example_records.append(
            {
                "id": example_id,
                "family": family,
                "send_mode": send_mode,
                "rendered_heading": rendered_heading,
            }
        )
    if len(generated_example_ids) != len(set(generated_example_ids)):
        errors.append("generated example ids contain duplicates")

    validation_references = data.get("validation_references")
    if not isinstance(validation_references, list) or not validation_references:
        errors.append("validation_references must be a non-empty list")
        validation_references = []
    validation_reference_ids: list[str] = []
    for index, reference in enumerate(validation_references):
        prefix = f"validation_references[{index}]"
        if not isinstance(reference, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        reference_id = reference.get("id")
        owner_ref_docs = reference.get("owner_docs")
        if not isinstance(reference_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        validation_reference_ids.append(reference_id)
        owner_doc_list = _as_string_list(
            owner_ref_docs,
            field_name=f"{prefix}.owner_docs",
            errors=errors,
            allow_empty=False,
        )
        for owner_doc in owner_doc_list:
            owner_path = (PROMPT_LAYER_ROOT / owner_doc).resolve()
            if not owner_path.exists():
                errors.append(
                    f"{prefix}.owner_docs entry is missing: "
                    f"{owner_path.relative_to(ROOT)}"
                )
    if len(validation_reference_ids) != len(set(validation_reference_ids)):
        errors.append("validation reference ids contain duplicates")

    prompt_families = data.get("prompt_families")
    if not isinstance(prompt_families, list) or not prompt_families:
        errors.append("prompt_families must be a non-empty list")
        prompt_families = []
    family_ids: list[str] = []
    for index, family in enumerate(prompt_families):
        prefix = f"prompt_families[{index}]"
        if not isinstance(family, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        family_id = family.get("id")
        if not isinstance(family_id, str):
            errors.append(f"{prefix}.id must be a string")
            continue
        family_ids.append(family_id)

        _as_string_list(
            family.get("node_kinds"),
            field_name=f"{family_id}.node_kinds",
            errors=errors,
        )

        allowed_send_modes = _as_string_list(
            family.get("allowed_send_modes"),
            field_name=f"{family_id}.allowed_send_modes",
            errors=errors,
        )
        for send_mode in allowed_send_modes:
            if send_mode not in send_mode_ids:
                errors.append(
                    f"{family_id}.allowed_send_modes contains unknown send "
                    f"mode `{send_mode}`"
                )

        required_sections = _as_string_list(
            family.get("required_sections"),
            field_name=f"{family_id}.required_sections",
            errors=errors,
        )
        for section in required_sections:
            if section not in section_order:
                errors.append(f"{family_id}.required_sections contains unknown section `{section}`")

        conditional_sections = family.get("conditionally_required_sections")
        if not isinstance(conditional_sections, list):
            errors.append(f"{family_id}.conditionally_required_sections must be a list")
            conditional_sections = []
        for conditional_index, conditional in enumerate(conditional_sections):
            conditional_prefix = f"{family_id}.conditionally_required_sections[{conditional_index}]"
            if not isinstance(conditional, dict):
                errors.append(f"{conditional_prefix} must be a mapping")
                continue
            conditional_section = conditional.get("section")
            when = conditional.get("when")
            if not isinstance(conditional_section, str):
                errors.append(f"{conditional_prefix}.section must be a string")
            elif conditional_section not in section_order:
                errors.append(
                    f"{conditional_prefix}.section is not in section_order: "
                    f"{conditional_section}"
                )
            if not isinstance(when, str):
                errors.append(f"{conditional_prefix}.when must be a string")

        _as_string_list(
            family.get("closure_modes"),
            field_name=f"{family_id}.closure_modes",
            errors=errors,
        )
        expected_closure_modes = EXPECTED_CLOSURE_MODES.get(family_id)
        if expected_closure_modes is not None:
            actual_closure_modes = family.get("closure_modes")
            if actual_closure_modes != expected_closure_modes:
                errors.append(
                    f"{family_id}.closure_modes must be exactly "
                    f"{expected_closure_modes}, found {actual_closure_modes}"
                )

        family_exact_blocks = family.get("exact_blocks")
        if not isinstance(family_exact_blocks, dict):
            errors.append(f"{family_id}.exact_blocks must be a mapping")
        else:
            for block_bucket, block_ids in family_exact_blocks.items():
                    normalized_ids = _as_string_list(
                        block_ids,
                        field_name=f"{family_id}.exact_blocks.{block_bucket}",
                        errors=errors,
                    )
                    for block_id in normalized_ids:
                        if block_id not in exact_block_ids:
                            errors.append(
                                f"{family_id}.exact_blocks.{block_bucket} "
                                f"references unknown block `{block_id}`"
                            )

        family_generated_examples = _as_string_list(
            family.get("generated_examples"),
            field_name=f"{family_id}.generated_examples",
            errors=errors,
        )
        for example_id in family_generated_examples:
            if example_id not in generated_example_ids:
                errors.append(
                    f"{family_id}.generated_examples references unknown "
                    f"example `{example_id}`"
                )

    if len(family_ids) != len(set(family_ids)):
        errors.append("prompt family ids contain duplicates")
    if sorted(family_ids) != ["parent_root_dispatch_prompt", "worker_dispatch_prompt"]:
        errors.append(
            "prompt family ids must be exactly "
            "parent_root_dispatch_prompt and worker_dispatch_prompt"
        )

    rules = _as_string_list(data.get("rules"), field_name="rules", errors=errors)
    validator_checks = _as_string_list(
        data.get("validator_checks"),
        field_name="validator_checks",
        errors=errors,
    )
    if (
        rules
        and "same_session_continue is a transport-only optimization inside the same attempt"
        not in rules
    ):
        errors.append("rules is missing the same_session_continue transport-only rule")
    if (
        validator_checks
        and "freeze exactly two canonical dispatch prompt families"
        not in validator_checks
    ):
        errors.append("validator_checks is missing the canonical prompt-family freeze rule")

    if not skip_inventory_checks:
        inventory_text = INVENTORY_PATH.read_text(encoding="utf-8")
        for family_id in family_ids:
            if family_id not in inventory_text:
                errors.append(f"generated/inventory.md is missing prompt family `{family_id}`")
        for send_mode_id in send_mode_ids:
            if send_mode_id not in inventory_text:
                errors.append(f"generated/inventory.md is missing send mode `{send_mode_id}`")
        for block_id in exact_block_ids:
            if block_id not in inventory_text:
                errors.append(f"generated/inventory.md is missing exact block `{block_id}`")
        for artifact in generated_artifacts:
            artifact_id = artifact.get("id")
            if isinstance(artifact_id, str) and artifact_id not in inventory_text:
                errors.append(
                    "generated/inventory.md is missing generated artifact "
                    f"`{artifact_id}`"
                )
        for example_id in generated_example_ids:
            if example_id not in inventory_text:
                errors.append(f"generated/inventory.md is missing generated example `{example_id}`")

    rendered_examples_text = EXAMPLES_PATH.read_text(encoding="utf-8")
    for example in generated_example_records:
        heading = example["rendered_heading"]
        family = example["family"]
        send_mode = example["send_mode"]
        if heading and heading in rendered_examples_text:
            continue
        if family and family not in rendered_examples_text:
            errors.append(f"generated/rendered-examples.md is missing prompt family `{family}`")
            continue
        if send_mode and send_mode not in rendered_examples_text:
            errors.append(f"generated/rendered-examples.md is missing send mode `{send_mode}`")

    _validate_live_prompt_surface_paths(errors, skip_inventory=skip_inventory_checks)
    _validate_current_assignment_examples(errors)
    _validate_same_session_examples(data, errors)

    return errors


def _render_inventory_md(data: dict[str, Any]) -> str:
    send_mode_ids = [send_mode["id"] for send_mode in data["send_modes"]]
    lines = [
        "# Generated Prompt Inventory",
        "",
        "Status: Generated reference",
        "",
        "This page inventories the current generated prompt contract surfaces.",
        "",
        "## Canonical Section Order",
        "",
    ]
    for index, section in enumerate(data["section_order"], start=1):
        lines.append(f"{index}. `{section}`")
    lines.extend(["", "## Static Continuation Sections", ""])
    for section in data["static_sections"]:
        lines.append(f"- `{section}`")
    lines.extend(["", "## Canonical Prompt Families", ""])
    for family in data["prompt_families"]:
        lines.append(f"- `{family['id']}`")
    lines.extend(["", "## Canonical Send Modes", ""])
    for send_mode_id in send_mode_ids:
        lines.append(f"- `{send_mode_id}`")
    lines.extend(["", "## Exact Block Registry", ""])
    for block in data["exact_blocks"]:
        lines.append(f"- `{block['id']}`")
        lines.append(f"  - owner: `{block['owner_file']}`")
        lines.append(f"  - role: `{block['role']}`")
    lines.extend(["", "## Generated Artifact Registry", ""])
    for artifact in data["generated_artifacts"]:
        lines.append(f"- `{artifact['id']}`")
        lines.append(f"  - file: `{artifact['path']}`")
    lines.extend(["", "## Generated Example Registry", ""])
    for example in data["generated_examples"]:
        lines.append(f"- `{example['id']}`")
        lines.append(f"  - rendered heading: `{example['rendered_heading']}`")
        lines.append(f"  - family: `{example['family']}`")
        lines.append(f"  - send mode: `{example['send_mode']}`")
    return "\n".join(lines).rstrip() + "\n"


def _render_inventory_debug(data: dict[str, Any]) -> str:
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
    for section in data.get("static_sections", []):
        lines.append(f"  - {section}")
    lines.append(f"- send modes: {', '.join(send_mode_ids)}")
    lines.append(f"- exact blocks: {len(data.get('exact_blocks', []))}")
    for block in data.get("exact_blocks", []):
        if isinstance(block, dict):
            lines.append(
                f"  - {block.get('id')} | owner={block.get('owner_file')} | "
                f"role={block.get('role')}"
            )
    lines.append(f"- prompt families: {len(data.get('prompt_families', []))}")
    for family in data.get("prompt_families", []):
        if isinstance(family, dict):
            lines.append(
                "  - "
                f"{family.get('id')} | "
                f"send_modes={','.join(family.get('allowed_send_modes', []))} | "
                f"required_sections={','.join(family.get('required_sections', []))}"
            )
    lines.append(f"- generated artifacts: {len(data.get('generated_artifacts', []))}")
    lines.append(f"- generated examples: {len(data.get('generated_examples', []))}")
    lines.append(f"- validation references: {len(data.get('validation_references', []))}")
    return "\n".join(lines).rstrip() + "\n"


def generate() -> None:
    data = load_catalog()
    errors = _validate_catalog(data, skip_inventory_checks=True)
    if errors:
        raise SystemExit("\n".join(f"ERROR: {error}" for error in errors))
    INVENTORY_PATH.write_text(_render_inventory_md(data), encoding="utf-8")


def validate() -> int:
    data = load_catalog()
    errors = _validate_catalog(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Prompt catalog validation passed.")
    return 0


def inventory() -> int:
    data = load_catalog()
    print(_render_inventory_debug(data), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["generate", "validate", "inventory"])
    args = parser.parse_args(argv)
    if args.command == "generate":
        generate()
        return 0
    if args.command == "inventory":
        return inventory()
    return validate()


if __name__ == "__main__":
    raise SystemExit(main())
