from __future__ import annotations

from .manifest_samples import sample_manifest
from .planning_samples import (
    non_root_parent_request,
    parent_request,
)
from .samples import (
    sample_assignment,
    sample_checkpoint,
    worker_request,
)

__all__ = [
    "extract_section",
    "non_root_parent_request",
    "normalize_whitespace",
    "parent_request",
    "sample_assignment",
    "sample_checkpoint",
    "sample_manifest",
    "section_index",
    "worker_request",
]


def section_index(markdown: str, heading: str) -> int:
    offset = 0
    for line in markdown.splitlines(keepends=True):
        if line.strip() == heading:
            return offset
        offset += len(line)
    raise ValueError(f"missing markdown heading line: {heading}")


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def extract_section(markdown: str, heading: str, next_heading: str | None = None) -> str:
    start = section_index(markdown, heading) + len(heading)
    section = markdown[start:]
    if next_heading is not None:
        end = section_index(section, next_heading)
        section = section[:end]
    return section
