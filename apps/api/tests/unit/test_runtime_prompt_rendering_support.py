from __future__ import annotations

from tests.unit.test_runtime_prompt_rendering_samples import (
    parent_request,
    sample_assignment,
    sample_checkpoint,
    sample_manifest,
    worker_request,
)

__all__ = [
    "extract_section",
    "normalize_whitespace",
    "parent_request",
    "sample_assignment",
    "sample_checkpoint",
    "sample_manifest",
    "section_index",
    "worker_request",
]


def section_index(markdown: str, heading: str) -> int:
    return markdown.index(heading)


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def extract_section(markdown: str, heading: str, next_heading: str | None = None) -> str:
    section = markdown.split(heading, maxsplit=1)[1]
    if next_heading is not None:
        section = section.split(next_heading, maxsplit=1)[0]
    return section
