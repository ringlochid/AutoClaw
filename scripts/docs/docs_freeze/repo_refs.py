from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from scripts.docs.markdown_format.files import iter_maintained_markdown_files

from .paths import ROOT

PSEUDO_REPO_ROOT = "autoclaw-main/"
REPO_REFERENCE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"(?P<value>"
    r"(?:autoclaw-main/)?"
    r"(?:AGENTS\.md|STYLE\.md|README\.md|pyproject\.toml|Makefile|"
    r"docs/[A-Za-z0-9_./*-]+|docs-internal/[A-Za-z0-9_./*-]+|"
    r"apps/[A-Za-z0-9_./*-]+|scripts/[A-Za-z0-9_./*-]+|"
    r"definitions/[A-Za-z0-9_./*-]+)"
    r"(?:::[A-Za-z0-9_./-]+)?"
    r")"
    r"(?![A-Za-z0-9_./-])"
)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)#]+)")
MARKDOWN_LINK_WITH_LABEL_PATTERN = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<target>[^)]+)\)")
BACKTICKED_RELATIVE_REFERENCE_PATTERN = re.compile(r"`(?P<value>(?:\.\./)+[A-Za-z0-9_./-]+/?)`")
TRAILING_REFERENCE_PUNCTUATION = "`.,);:]>"


@dataclass(frozen=True)
class RepoPathReferenceIssue:
    doc_path: Path
    line: int
    raw_reference: str
    normalized_reference: str
    reason: str


@dataclass(frozen=True)
class NavigationLinkLabelIssue:
    doc_path: Path
    line: int
    label: str
    raw_target: str
    normalized_reference: str


def repo_path_reference_issues() -> list[RepoPathReferenceIssue]:
    issues: list[RepoPathReferenceIssue] = []
    for doc_path in iter_maintained_markdown_files(ROOT):
        text = doc_path.read_text(encoding="utf-8")
        if not should_validate_repo_paths(doc_path, text):
            continue
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


def navigation_link_label_issues() -> list[NavigationLinkLabelIssue]:
    issues: list[NavigationLinkLabelIssue] = []
    for doc_path in iter_maintained_markdown_files(ROOT):
        if not should_validate_navigation_link_labels(doc_path):
            continue
        in_code_block = False
        lines = doc_path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            issues.extend(line_navigation_link_label_issues(doc_path, line_number, line))
    return sorted(
        issues,
        key=lambda issue: (
            issue.doc_path.relative_to(ROOT).as_posix(),
            issue.line,
            issue.label,
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
    for raw_target in MARKDOWN_LINK_PATTERN.findall(line):
        if should_validate_relative_reference(doc_path):
            issues.extend(
                markdown_link_reference_issues(
                    doc_path=doc_path,
                    line_number=line_number,
                    raw_target=raw_target,
                )
            )
    for match in BACKTICKED_RELATIVE_REFERENCE_PATTERN.finditer(line):
        if should_validate_relative_reference(doc_path):
            issues.extend(
                relative_reference_issues(
                    doc_path=doc_path,
                    line_number=line_number,
                    raw_reference=match.group("value"),
                )
            )
    return issues


def line_navigation_link_label_issues(
    doc_path: Path,
    line_number: int,
    line: str,
) -> list[NavigationLinkLabelIssue]:
    issues: list[NavigationLinkLabelIssue] = []
    for match in MARKDOWN_LINK_WITH_LABEL_PATTERN.finditer(line):
        label = match.group("label").strip()
        normalized_label = label.replace("`", "").strip()
        if ".md" not in normalized_label.lower():
            continue
        raw_target = match.group("target").strip()
        normalized_reference = normalized_markdown_target(doc_path, raw_target)
        if normalized_reference is None or not normalized_reference.endswith(".md"):
            continue
        issues.append(
            NavigationLinkLabelIssue(
                doc_path=doc_path,
                line=line_number,
                label=label,
                raw_target=raw_target,
                normalized_reference=normalized_reference,
            )
        )
    return issues


def should_validate_relative_reference(doc_path: Path) -> bool:
    resolved_path = doc_path.resolve() if doc_path.is_absolute() else (ROOT / doc_path).resolve()
    try:
        relative_public_parts = resolved_path.relative_to(ROOT / "docs").parts
        return bool(relative_public_parts and relative_public_parts[0] in {"product", "reference"})
    except ValueError:
        pass

    try:
        relative_internal_parts = resolved_path.relative_to(ROOT / "docs-internal").parts
    except ValueError:
        return False

    if not relative_internal_parts:
        return False
    if relative_internal_parts[:2] == ("execution", "v1") and len(relative_internal_parts) >= 3:
        if relative_internal_parts[2] in {"plans", "evidence", "reviews"}:
            return False
    if relative_internal_parts[0] in {"design", "current", "execution", "adr"}:
        return True
    if relative_internal_parts[0] == "archive":
        return False
    return False


def should_validate_navigation_link_labels(doc_path: Path) -> bool:
    resolved_path = doc_path.resolve() if doc_path.is_absolute() else (ROOT / doc_path).resolve()
    try:
        relative_root_path = resolved_path.relative_to(ROOT)
    except ValueError:
        return False

    if relative_root_path in {Path("README.md"), Path("AGENTS.md"), Path("STYLE.md")}:
        return True

    try:
        resolved_path.relative_to(ROOT / ".agents" / "standards")
        return True
    except ValueError:
        pass

    try:
        resolved_path.relative_to(ROOT / "docs")
        return True
    except ValueError:
        pass

    try:
        relative_internal_parts = resolved_path.relative_to(ROOT / "docs-internal").parts
    except ValueError:
        return False

    return bool(
        relative_internal_parts and relative_internal_parts[0] in {"design", "current", "execution"}
    )


def should_validate_repo_paths(doc_path: Path, text: str) -> bool:
    resolved_path = doc_path.resolve() if doc_path.is_absolute() else (ROOT / doc_path).resolve()
    try:
        relative_internal_parts = resolved_path.relative_to(ROOT / "docs-internal").parts
    except ValueError:
        return True

    if not relative_internal_parts:
        return True
    if relative_internal_parts[:2] == ("execution", "v1") and len(relative_internal_parts) >= 3:
        if relative_internal_parts[2] in {"plans", "evidence", "reviews"}:
            return False
    if relative_internal_parts[0] == "archive":
        return False
    if relative_internal_parts[:2] == ("execution", "v1") and "summary-only: yes" in text:
        return False
    return True


def markdown_link_reference_issues(
    *,
    doc_path: Path,
    line_number: int,
    raw_target: str,
) -> list[RepoPathReferenceIssue]:
    parsed = urlparse(raw_target)
    if parsed.scheme or parsed.netloc or raw_target.startswith(("mailto:", "#")):
        return []

    resolved_path = (doc_path.parent / raw_target).resolve()
    try:
        normalized_reference = resolved_path.relative_to(ROOT).as_posix()
    except ValueError:
        return []

    if resolved_path.exists():
        return []

    return [
        RepoPathReferenceIssue(
            doc_path=doc_path,
            line=line_number,
            raw_reference=raw_target,
            normalized_reference=normalized_reference,
            reason="missing_path",
        )
    ]


def normalized_markdown_target(doc_path: Path, raw_target: str) -> str | None:
    parsed = urlparse(raw_target)
    if parsed.scheme or parsed.netloc or raw_target.startswith(("mailto:", "#")):
        return None

    target_path = raw_target.split("#", 1)[0].strip()
    if not target_path:
        return None

    resolved_path = (doc_path.parent / target_path).resolve()
    try:
        return resolved_path.relative_to(ROOT).as_posix()
    except ValueError:
        return None


def relative_reference_issues(
    *,
    doc_path: Path,
    line_number: int,
    raw_reference: str,
) -> list[RepoPathReferenceIssue]:
    resolved_path = (doc_path.parent / raw_reference).resolve()
    try:
        normalized_reference = resolved_path.relative_to(ROOT).as_posix()
    except ValueError:
        return []

    if resolved_path.exists():
        return []

    return [
        RepoPathReferenceIssue(
            doc_path=doc_path,
            line=line_number,
            raw_reference=raw_reference,
            normalized_reference=normalized_reference,
            reason="missing_path",
        )
    ]


def clean_reference_token(raw_reference: str) -> str:
    return raw_reference.rstrip(TRAILING_REFERENCE_PUNCTUATION)


def normalized_repo_reference(raw_reference: str) -> str:
    reference_without_symbol = raw_reference.split("::", 1)[0]
    if reference_without_symbol.startswith(PSEUDO_REPO_ROOT):
        return reference_without_symbol.removeprefix(PSEUDO_REPO_ROOT)
    return reference_without_symbol
