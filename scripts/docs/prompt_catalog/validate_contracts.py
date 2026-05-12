from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GeneratedExampleRecord:
    id: str
    family: str
    send_mode: str
    rendered_heading: str


@dataclass(frozen=True)
class CatalogValidationState:
    family_ids: tuple[str, ...]
    send_mode_ids: tuple[str, ...]
    exact_block_ids: tuple[str, ...]
    generated_artifacts: tuple[dict[str, Any], ...]
    generated_example_ids: tuple[str, ...]
    generated_example_records: tuple[GeneratedExampleRecord, ...]
