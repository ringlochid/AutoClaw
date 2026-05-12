from __future__ import annotations

from scripts.docs.markdown_format import iter_maintained_markdown_files

from .paths import DOCS_ROOT, ROOT
from .validator_docs_checks import (
    validate_docs_rules,
    validate_inventory_hits,
    validate_lock_map_rules,
    validate_marker_rules,
    validate_prompt_catalog,
    validate_text_rules,
)
from .validator_inventory import build_inventory, print_inventory
from .validator_phase_checks import (
    validate_execution_record_headers,
    validate_phase_scoped_records,
)


def validate(debug_inventory: bool = False) -> int:
    errors: list[str] = []
    maintained_markdown_paths = iter_maintained_markdown_files(ROOT)
    redesign_and_execution_paths = list((DOCS_ROOT / "redesign").rglob("*.md")) + list(
        (DOCS_ROOT / "execution").rglob("*.md")
    )
    inventory = build_inventory()

    validate_text_rules(errors, maintained_markdown_paths)
    validate_marker_rules(errors)
    validate_execution_record_headers(errors)
    validate_phase_scoped_records(errors)
    validate_docs_rules(
        errors=errors,
        redesign_and_execution_paths=redesign_and_execution_paths,
        inventory=inventory,
    )
    validate_lock_map_rules(errors)
    validate_inventory_hits(errors=errors, inventory=inventory)
    validate_prompt_catalog(errors)

    if debug_inventory:
        print_inventory(inventory=inventory)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Docs freeze validation passed.")
    return 0

__all__ = ["print_inventory", "validate"]
