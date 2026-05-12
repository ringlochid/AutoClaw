from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path

from .formatting import format_markdown_text, normalize_text

ROOT = Path(__file__).resolve().parents[3]
DOCS_ROOT = ROOT / "docs"
EXCLUDED_SOURCE_PACKS = DOCS_ROOT / "archive" / "source-packs"

MAINTAINED_MD_ROOTS = (
    DOCS_ROOT / "redesign",
    DOCS_ROOT / "current",
    DOCS_ROOT / "execution",
)
MAINTAINED_MD_FILES = (
    DOCS_ROOT / "README.md",
    ROOT / "README.md",
)


@dataclass(frozen=True)
class FormatterViolation:
    path: Path
    line: int
    reason: str = "hard-wrapped prose or list item"


def iter_maintained_markdown_files(root: Path = ROOT) -> list[Path]:
    docs_root = root / "docs"
    excluded_source_packs = docs_root / "archive" / "source-packs"
    maintained_roots = (
        docs_root / "redesign",
        docs_root / "current",
        docs_root / "execution",
    )
    maintained_files = (
        docs_root / "README.md",
        root / "README.md",
    )

    paths: list[Path] = []
    for base in maintained_roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            try:
                path.relative_to(excluded_source_packs)
                continue
            except ValueError:
                pass
            paths.append(path)

    for path in maintained_files:
        if path.exists():
            paths.append(path)

    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(path)
    return deduped


def first_difference_line(original: str, formatted: str) -> int:
    original_lines = normalize_text(original).splitlines()
    formatted_lines = normalize_text(formatted).splitlines()
    for index, (left, right) in enumerate(
        zip_longest(original_lines, formatted_lines, fillvalue=None),
        start=1,
    ):
        if left != right:
            return index
    return 1


def collect_violations(paths: Iterable[Path]) -> list[FormatterViolation]:
    violations: list[FormatterViolation] = []
    for path in paths:
        original = path.read_text(encoding="utf-8")
        formatted = format_markdown_text(original)
        if original != formatted:
            violations.append(
                FormatterViolation(
                    path=path,
                    line=first_difference_line(original, formatted),
                )
            )
    return violations


def write_formatted_files(paths: Iterable[Path]) -> list[Path]:
    changed: list[Path] = []
    for path in paths:
        original = path.read_text(encoding="utf-8")
        formatted = format_markdown_text(original)
        if original == formatted:
            continue
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(formatted)
        changed.append(path)
    return changed


def resolve_paths(cli_paths: Sequence[str] | None) -> list[Path]:
    if not cli_paths:
        return iter_maintained_markdown_files()

    resolved: list[Path] = []
    for raw in cli_paths:
        path = (ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
        if path.is_dir():
            for child in sorted(path.rglob("*.md")):
                try:
                    child.relative_to(EXCLUDED_SOURCE_PACKS)
                    continue
                except ValueError:
                    pass
                resolved.append(child)
            continue
        resolved.append(path)
    return resolved
