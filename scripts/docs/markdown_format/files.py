from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path

from .formatting import format_markdown_text, format_yaml_text, normalize_text

ROOT = Path(__file__).resolve().parents[3]
DOCS_PUBLIC_ROOT = ROOT / "docs"
DOCS_INTERNAL_ROOT = ROOT / "docs-internal"
EXCLUDED_SOURCE_PACKS = DOCS_INTERNAL_ROOT / "archive" / "source-packs"

MAINTAINED_MD_ROOTS = (
    DOCS_PUBLIC_ROOT / "product",
    DOCS_PUBLIC_ROOT / "reference",
    DOCS_INTERNAL_ROOT / "design" / "v1",
    DOCS_INTERNAL_ROOT / "current" / "v1",
    DOCS_INTERNAL_ROOT / "execution" / "v1",
    DOCS_INTERNAL_ROOT / "adr",
    DOCS_INTERNAL_ROOT / "archive" / "execution",
    ROOT / ".agents" / "standards",
)
MAINTAINED_MD_FILES = (
    DOCS_PUBLIC_ROOT / "README.md",
    DOCS_INTERNAL_ROOT / "README.md",
    DOCS_INTERNAL_ROOT / "archive" / "README.md",
    DOCS_INTERNAL_ROOT / "archive" / "01-source-inputs-and-unsafe-material.md",
    DOCS_INTERNAL_ROOT / "archive" / "02-source-coverage-matrix.md",
    DOCS_INTERNAL_ROOT / "archive" / "03-old-version-docs-disposition.md",
    DOCS_INTERNAL_ROOT / "archive" / "design" / "findings.md",
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "STYLE.md",
)


@dataclass(frozen=True)
class FormatterViolation:
    path: Path
    line: int
    reason: str = "hard-wrapped prose or list item"


FORMAT_SUFFIXES = frozenset({".md", ".yaml", ".yml"})


def iter_maintained_markdown_files(root: Path = ROOT) -> list[Path]:
    docs_root = root / "docs"
    docs_internal_root = root / "docs-internal"
    excluded_source_packs = docs_internal_root / "archive" / "source-packs"
    maintained_roots = (
        docs_root / "product",
        docs_root / "reference",
        docs_internal_root / "design" / "v1",
        docs_internal_root / "current" / "v1",
        docs_internal_root / "execution" / "v1",
        docs_internal_root / "adr",
        docs_internal_root / "archive" / "execution",
        root / ".agents" / "standards",
    )
    maintained_files = (
        docs_root / "README.md",
        docs_internal_root / "README.md",
        docs_internal_root / "archive" / "README.md",
        docs_internal_root / "archive" / "01-source-inputs-and-unsafe-material.md",
        docs_internal_root / "archive" / "02-source-coverage-matrix.md",
        docs_internal_root / "archive" / "03-old-version-docs-disposition.md",
        docs_internal_root / "archive" / "design" / "findings.md",
        root / "README.md",
        root / "AGENTS.md",
        root / "STYLE.md",
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
        formatted = format_path_text(path, original)
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
        formatted = format_path_text(path, original)
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
        if path == DOCS_PUBLIC_ROOT or path == DOCS_INTERNAL_ROOT:
            resolved.extend(iter_maintained_markdown_files())
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.suffix not in FORMAT_SUFFIXES:
                    continue
                try:
                    child.relative_to(EXCLUDED_SOURCE_PACKS)
                    continue
                except ValueError:
                    pass
                resolved.append(child)
            continue
        resolved.append(path)
    return resolved


def format_path_text(path: Path, text: str) -> str:
    if path.suffix in {".yaml", ".yml"}:
        return format_yaml_text(text)
    return format_markdown_text(text)
