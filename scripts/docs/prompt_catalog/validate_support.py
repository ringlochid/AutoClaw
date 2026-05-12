from __future__ import annotations

from pathlib import Path
from typing import Any

from .load import PROMPT_LAYER_ROOT


def as_string_list(
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


def owner_doc_paths(owner_docs: list[str]) -> list[Path]:
    return [PROMPT_LAYER_ROOT / owner_doc for owner_doc in owner_docs]
