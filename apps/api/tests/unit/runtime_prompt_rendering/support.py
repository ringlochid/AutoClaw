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
    return markdown.index(heading)


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def extract_section(markdown: str, heading: str, next_heading: str | None = None) -> str:
    section = markdown.split(heading, maxsplit=1)[1]
    if next_heading is not None:
        section = section.split(next_heading, maxsplit=1)[0]
    return section
