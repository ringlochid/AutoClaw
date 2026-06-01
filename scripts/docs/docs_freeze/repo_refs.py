from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from scripts.docs.markdown_format.files import iter_maintained_markdown_files

from .paths import ROOT

PSEUDO_REPO_ROOT = "autoclaw-main/"
REPO_REFERENCE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"(?P<value>"
    r"(?:autoclaw-main/)?"
    r"(?:AGENTS\.md|STYLE\.md|README\.md|pyproject\.toml|Makefile|"
    r"docs/[A-Za-z0-9_./*-]+|apps/[A-Za-z0-9_./*-]+|"
    r"scripts/[A-Za-z0-9_./*-]+|definitions/[A-Za-z0-9_./*-]+)"
    r"(?:::[A-Za-z0-9_./-]+)?"
    r")"
    r"(?![A-Za-z0-9_./-])"
)
TRAILING_REFERENCE_PUNCTUATION = "`.,);:]>"


@dataclass(frozen=True)
class RepoPathReferenceIssue:
    doc_path: Path
    line: int
    raw_reference: str
    normalized_reference: str
    reason: str


def repo_path_reference_issues() -> list[RepoPathReferenceIssue]:
    issues: list[RepoPathReferenceIssue] = []
    for doc_path in iter_maintained_markdown_files(ROOT):
        text = doc_path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            issues.extend(line_repo_path_reference_issues(doc_path, line_number, line))
    return sorted(
        issues,
        key=lambda issue: (
            issue.doc_path.relative_to(ROOT).as_posix(),
            issue.line,
            issue.raw_reference,
        ),
    )


def line_repo_path_reference_issues(
    doc_path: Path,
    line_number: int,
    line: str,
) -> list[RepoPathReferenceIssue]:
    issues: list[RepoPathReferenceIssue] = []
    seen_references: set[str] = set()
    for match in REPO_REFERENCE_PATTERN.finditer(line):
        raw_reference = clean_reference_token(match.group("value"))
        if not raw_reference or raw_reference in seen_references:
            continue
        seen_references.add(raw_reference)

        normalized_reference = normalized_repo_reference(raw_reference)
        if raw_reference.startswith(PSEUDO_REPO_ROOT):
            issues.append(
                RepoPathReferenceIssue(
                    doc_path=doc_path,
                    line=line_number,
                    raw_reference=raw_reference,
                    normalized_reference=normalized_reference,
                    reason="pseudo_repo_root",
                )
            )
            continue

        if "*" in normalized_reference:
            continue

        if not (ROOT / normalized_reference.rstrip("/")).exists():
            issues.append(
                RepoPathReferenceIssue(
                    doc_path=doc_path,
                    line=line_number,
                    raw_reference=raw_reference,
                    normalized_reference=normalized_reference,
                    reason="missing_path",
                )
            )
    return issues


def clean_reference_token(raw_reference: str) -> str:
    return raw_reference.rstrip(TRAILING_REFERENCE_PUNCTUATION)


def normalized_repo_reference(raw_reference: str) -> str:
    reference_without_symbol = raw_reference.split("::", 1)[0]
    if reference_without_symbol.startswith(PSEUDO_REPO_ROOT):
        return reference_without_symbol.removeprefix(PSEUDO_REPO_ROOT)
    return reference_without_symbol
