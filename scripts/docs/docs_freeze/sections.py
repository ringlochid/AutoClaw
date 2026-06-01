from __future__ import annotations

import re
from pathlib import Path

from scripts.docs.markdown_format import (
    FormatterViolation,
    collect_violations,
    iter_maintained_markdown_files,
)

from .content.rules import (
    COMPATIBILITY_STATUS,
    DELETED_FILENAME_HISTORY_EXCLUDED_PATHS,
    DELETED_ROUTER_FILENAMES,
    LEGACY_HEADING,
)
from .paths import ARCHIVE_ROOT, DESIGN_ROOT, EXECUTION_ROOT, ROOT
from .record_rules import (
    MARKDOWN_LINK_PATTERN,
    PHASE_SCOPED_EVIDENCE_EXCLUDED_PATHS,
    PHASE_SCOPED_PLAN_EXCLUDED_PATHS,
    PHASE_SCOPED_REVIEW_EXCLUDED_PATHS,
)


def api_appendix_path() -> Path:
    return DESIGN_ROOT / "interfaces" / "api-schema-appendix.md"


def api_appendix_headings() -> list[str]:
    headings: list[str] = []
    for line in api_appendix_path().read_text(encoding="utf-8").splitlines():
        if line.startswith("### `") and line.endswith("`"):
            headings.append(line.strip())
    return headings


def matching_line_numbers(text: str, needle: str) -> list[int]:
    return [index for index, line in enumerate(text.splitlines(), start=1) if needle in line]


def section_slice(text: str, start_heading: str, end_heading: str) -> str:
    start = text.find(start_heading)
    if start == -1:
        return ""
    end = text.find(end_heading, start + len(start_heading))
    if end == -1:
        return text[start:]
    return text[start:end]


def section_body(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group("body") if match else ""


def execution_record_paths() -> list[Path]:
    excluded = (
        PHASE_SCOPED_PLAN_EXCLUDED_PATHS
        | PHASE_SCOPED_EVIDENCE_EXCLUDED_PATHS
        | PHASE_SCOPED_REVIEW_EXCLUDED_PATHS
    )
    live_paths = (
        sorted(EXECUTION_ROOT.glob("plans/*.md"))
        + sorted(EXECUTION_ROOT.glob("evidence/*.md"))
        + sorted(EXECUTION_ROOT.glob("reviews/*.md"))
    )
    archived_record_root = ARCHIVE_ROOT / "execution"
    archived_paths = (
        sorted(archived_record_root.glob("plans/*.md"))
        + sorted(archived_record_root.glob("evidence/*.md"))
        + sorted(archived_record_root.glob("reviews/*.md"))
    )
    return [path for path in live_paths + archived_paths if path not in excluded]


def missing_section_markers(
    text: str,
    *,
    start_heading: str,
    end_heading: str,
    markers: list[str],
) -> list[str]:
    section = section_slice(text, start_heading, end_heading)
    return [marker for marker in markers if marker not in section]


def legacy_heading_hits() -> dict[Path, list[int]]:
    hits: dict[Path, list[int]] = {}
    for path in DESIGN_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        line_numbers = matching_line_numbers(text, LEGACY_HEADING)
        if line_numbers:
            hits[path] = line_numbers
    return hits


def compatibility_status_hits() -> dict[Path, list[int]]:
    hits: dict[Path, list[int]] = {}
    for path in DESIGN_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        line_numbers = matching_line_numbers(text, COMPATIBILITY_STATUS)
        if line_numbers:
            hits[path] = line_numbers
    return hits


def deleted_filename_hits() -> dict[str, list[tuple[Path, list[int]]]]:
    hits: dict[str, list[tuple[Path, list[int]]]] = {}
    for path in iter_maintained_markdown_files(ROOT):
        if path in DELETED_FILENAME_HISTORY_EXCLUDED_PATHS:
            continue
        text = path.read_text(encoding="utf-8")
        for deleted_name in DELETED_ROUTER_FILENAMES:
            line_numbers = matching_line_numbers(text, deleted_name)
            if line_numbers:
                hits.setdefault(deleted_name, []).append((path, line_numbers))
    return hits


def markdown_formatter_violations() -> list[FormatterViolation]:
    return collect_violations(iter_maintained_markdown_files(ROOT))


def execution_markdown_sources() -> list[Path]:
    return [ROOT / "AGENTS.md", *iter_maintained_markdown_files(ROOT)]


def linked_design_paths_from_execution() -> set[Path]:
    linked: set[Path] = set()
    for path in execution_markdown_sources():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_PATTERN.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = (path.parent / target).resolve()
            try:
                rel = resolved.relative_to(ROOT)
            except ValueError:
                continue
            if rel.parts[:3] == ("docs-internal", "design", "v1") and resolved.is_file():
                linked.add(resolved)
    return linked


def unreferenced_design_paths() -> list[Path]:
    design_files = sorted(
        path
        for path in DESIGN_ROOT.rglob("*")
        if path.is_file() and path.suffix in {".md", ".yaml"} and path.name != "INDEX.md"
    )
    linked = linked_design_paths_from_execution()
    return [path for path in design_files if path not in linked]
