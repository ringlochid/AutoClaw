from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from scripts.docs.markdown_format.files import iter_maintained_markdown_files

from ..content.rules import (
    CURRENT_DOC_CLOSEOUT_HEADINGS,
    EXECUTION_PROGRAM_WORDING_ROOTS,
    FORBIDDEN_EXECUTION_PROGRAM_PATTERNS,
    PUBLIC_DOC_FORBIDDEN_REVIEW_HEADINGS,
    REQUIRED_MARKERS,
)
from ..paths import CURRENT_ROOT, DOCS_PUBLIC_ROOT, ROOT
from ..repo_refs import (
    NavigationLinkLabelIssue,
    RepoPathReferenceIssue,
    navigation_link_label_issues,
    repo_path_reference_issues,
)
from ..sections import (
    FormatterViolation,
    api_appendix_headings,
    compatibility_status_hits,
    deleted_filename_hits,
    legacy_heading_hits,
    markdown_formatter_violations,
    unreferenced_design_paths,
)


@dataclass(frozen=True)
class DocsFreezeInventory:
    legacy_hits: dict[Path, list[int]]
    compatibility_hits: dict[Path, list[int]]
    deleted_hits: dict[str, list[tuple[Path, list[int]]]]
    execution_program_wording_issues: list[LinePatternIssue]
    public_doc_review_heading_issues: list[LinePatternIssue]
    current_doc_closeout_heading_issues: list[Path]
    repo_path_issues: list[RepoPathReferenceIssue]
    navigation_link_label_issues: list[NavigationLinkLabelIssue]
    status_issues: list[DocStatusIssue]
    formatter_violations: list[FormatterViolation]
    unreferenced_paths: list[Path]
    public_reference_status_issues: list[Path]
    public_reference_contrast_issues: list[tuple[Path, str]]


def build_inventory() -> DocsFreezeInventory:
    return DocsFreezeInventory(
        legacy_hits=legacy_heading_hits(),
        compatibility_hits=compatibility_status_hits(),
        deleted_hits=deleted_filename_hits(),
        execution_program_wording_issues=execution_program_wording_issues(),
        public_doc_review_heading_issues=public_doc_review_heading_issues(),
        current_doc_closeout_heading_issues=current_doc_closeout_heading_issues(),
        repo_path_issues=repo_path_reference_issues(),
        navigation_link_label_issues=navigation_link_label_issues(),
        status_issues=doc_status_issues(),
        formatter_violations=markdown_formatter_violations(),
        unreferenced_paths=unreferenced_design_paths(),
        public_reference_status_issues=public_reference_status_issues(),
        public_reference_contrast_issues=public_reference_contrast_issues(),
    )


def print_inventory(*, inventory: DocsFreezeInventory | None = None) -> None:
    inventory = build_inventory() if inventory is None else inventory

    print("API appendix headings:")
    for heading in api_appendix_headings():
        print(f"- {heading}")

    print("")
    print_required_marker_coverage()
    print("")
    print_execution_linked_design_coverage(inventory.unreferenced_paths)
    print("")
    print_path_hits("Legacy filename headings in live design docs:", inventory.legacy_hits)
    print("")
    print_path_hits("Compatibility statuses in live design docs:", inventory.compatibility_hits)
    print("")
    print_deleted_router_hits(inventory.deleted_hits)
    print("")
    print_line_pattern_issues(
        "Execution-program wording outside execution/archive:",
        inventory.execution_program_wording_issues,
    )
    print("")
    print_line_pattern_issues(
        "Public-doc internal review headings:",
        inventory.public_doc_review_heading_issues,
    )
    print("")
    print_current_doc_closeout_heading_issues(inventory.current_doc_closeout_heading_issues)
    print("")
    print_repo_path_issues(inventory.repo_path_issues)
    print("")
    print_navigation_link_label_issues(inventory.navigation_link_label_issues)
    print("")
    print_status_issues(inventory.status_issues)
    print("")
    print_public_reference_issues(inventory)
    print("")
    print_formatter_violations(inventory.formatter_violations)


def print_required_marker_coverage() -> None:
    print("Required marker coverage:")
    for path, markers in REQUIRED_MARKERS.items():
        rel = path.relative_to(ROOT)
        if not path.exists():
            print(f"- {rel}: missing file")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            print(f"- {rel}: missing {len(missing)} marker(s)")
            for marker in missing:
                print(f"  - {marker}")
        else:
            print(f"- {rel}: ok ({len(markers)} marker(s))")


def print_execution_linked_design_coverage(unreferenced_paths: list[Path]) -> None:
    print("Maintained-doc linked design coverage:")
    if not unreferenced_paths:
        print(
            "- all design markdown/yaml files are linked from AGENTS.md or maintained markdown docs"
        )
        return
    for path in unreferenced_paths:
        print(f"- missing maintained-doc link: {path.relative_to(ROOT)}")


def print_path_hits(title: str, hits: dict[Path, list[int]]) -> None:
    print(title)
    if not hits:
        print("- none")
        return
    for path, line_numbers in sorted(hits.items()):
        joined = ", ".join(str(n) for n in line_numbers)
        print(f"- {path.relative_to(ROOT)}: lines {joined}")


def print_deleted_router_hits(deleted_hits: dict[str, list[tuple[Path, list[int]]]]) -> None:
    print("Deleted router filename references in maintained docs:")
    if not deleted_hits:
        print("- none")
        return
    for deleted_name in sorted(deleted_hits):
        print(f"- {deleted_name}")
        for path, line_numbers in deleted_hits[deleted_name]:
            joined = ", ".join(str(n) for n in line_numbers)
            print(f"  - {path.relative_to(ROOT)}: lines {joined}")


@dataclass(frozen=True)
class LinePatternIssue:
    path: Path
    line: int
    label: str


def print_line_pattern_issues(title: str, issues: list[LinePatternIssue]) -> None:
    print(title)
    if not issues:
        print("- none")
        return
    for issue in issues:
        print(f"- {issue.path.relative_to(ROOT)}:{issue.line}: {issue.label}")


def print_repo_path_issues(repo_path_issues: list[RepoPathReferenceIssue]) -> None:
    print("Missing or pseudo repo-path references in maintained docs:")
    if not repo_path_issues:
        print("- none")
        return
    for issue in repo_path_issues:
        suffix = ""
        if issue.reason == "pseudo_repo_root":
            suffix = f" -> rewrite to `{issue.normalized_reference}`"
        print(f"- {issue.doc_path.relative_to(ROOT)}:{issue.line}: `{issue.raw_reference}`{suffix}")


def print_navigation_link_label_issues(issues: list[NavigationLinkLabelIssue]) -> None:
    print("Filename-style markdown link labels:")
    if not issues:
        print("- none")
        return
    for issue in issues:
        print(
            f"- {issue.doc_path.relative_to(ROOT)}:{issue.line}: "
            f"`{issue.label}` -> `{issue.raw_target}`"
        )


@dataclass(frozen=True)
class DocStatusIssue:
    path: Path
    found_status: str | None
    allowed_statuses: tuple[str, ...]


def doc_status_issues() -> list[DocStatusIssue]:
    issues: list[DocStatusIssue] = []
    for path in iter_maintained_markdown_files(ROOT):
        allowed_statuses = allowed_statuses_for_path(path)
        if not allowed_statuses:
            continue
        found_status = doc_status_value(path)
        if found_status not in allowed_statuses:
            issues.append(
                DocStatusIssue(
                    path=path,
                    found_status=found_status,
                    allowed_statuses=allowed_statuses,
                )
            )
    return sorted(issues, key=lambda issue: issue.path.relative_to(ROOT).as_posix())


def allowed_statuses_for_path(path: Path) -> tuple[str, ...] | None:
    relative_path = path.relative_to(ROOT)
    parts = relative_path.parts
    if path.name == "INDEX.md":
        return ("Reference",)
    if relative_path in {
        Path("AGENTS.md"),
        Path("STYLE.md"),
        Path("README.md"),
        Path("docs/README.md"),
        Path("docs-internal/README.md"),
    }:
        return ("Reference",)
    if parts[0] == ".agents":
        return ("Reference",)
    if parts[0] == "docs":
        return ("Reference",)
    if parts[:2] == ("docs-internal", "adr"):
        return ("Reference", "Accepted")
    if parts[:2] == ("docs-internal", "archive"):
        return ("Reference",)
    if parts[:3] == ("docs-internal", "design", "v1"):
        return ("Target", "Reference")
    if parts[:3] == ("docs-internal", "current", "v1"):
        return ("Current", "Reference")
    if parts[:3] == ("docs-internal", "execution", "v1"):
        if path.name in {
            "phase-plan-template.md",
            "phase-evidence-template.md",
            "phase-review-template.md",
        }:
            return ("Template",)
        return ("Reference",)
    return None


def doc_status_value(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("Status: "):
            return line.removeprefix("Status: ").strip()
    return None


def print_formatter_violations(formatter_violations: list[FormatterViolation]) -> None:
    print("Maintained-doc markdown unwrap formatter violations:")
    if not formatter_violations:
        print("- none")
        return
    for violation in formatter_violations:
        print(f"- {violation.path.relative_to(ROOT)}:{violation.line}: {violation.reason}")


def print_status_issues(status_issues: list[DocStatusIssue]) -> None:
    print("Maintained-doc status contract issues:")
    if not status_issues:
        print("- none")
        return
    for issue in status_issues:
        found_status = issue.found_status if issue.found_status is not None else "<missing>"
        allowed = ", ".join(f"`{status}`" for status in issue.allowed_statuses)
        print(
            f"- {issue.path.relative_to(ROOT)}: found `Status: {found_status}`; "
            f"allowed here: {allowed}"
        )


def print_current_doc_closeout_heading_issues(paths: list[Path]) -> None:
    print("Current-doc closeout heading issues:")
    if not paths:
        print("- none")
        return
    for path in paths:
        print(f"- {path.relative_to(ROOT)}: missing exact `## Evidence` or `## Verification`")


def execution_program_wording_issues() -> list[LinePatternIssue]:
    issues: list[LinePatternIssue] = []
    for root in EXECUTION_PROGRAM_WORDING_ROOTS:
        for path in sorted(root.rglob("*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for line_number, line in enumerate(lines, start=1):
                for label, pattern in FORBIDDEN_EXECUTION_PROGRAM_PATTERNS:
                    if pattern.search(line):
                        issues.append(LinePatternIssue(path=path, line=line_number, label=label))
    return issues


def public_doc_review_heading_issues() -> list[LinePatternIssue]:
    issues: list[LinePatternIssue] = []
    for path in sorted(DOCS_PUBLIC_ROOT.rglob("*.md")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            for heading in PUBLIC_DOC_FORBIDDEN_REVIEW_HEADINGS:
                if stripped == heading:
                    issues.append(LinePatternIssue(path=path, line=line_number, label=heading))
    return issues


def current_doc_closeout_heading_issues() -> list[Path]:
    issues: list[Path] = []
    for path in sorted(CURRENT_ROOT.rglob("*.md")):
        if path.name == "README.md":
            continue
        headings = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
        if any(heading in headings for heading in CURRENT_DOC_CLOSEOUT_HEADINGS):
            continue
        issues.append(path)
    return issues


def public_reference_status_issues() -> list[Path]:
    reference_root = ROOT / "docs" / "reference"
    issues: list[Path] = []
    for path in sorted(reference_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        status_line = next(
            (line.strip() for line in text.splitlines() if line.startswith("Status: ")),
            None,
        )
        if status_line != "Status: Reference":
            issues.append(path)
    return issues


def public_reference_contrast_issues() -> list[tuple[Path, str]]:
    reference_root = ROOT / "docs" / "reference"
    banned_patterns = (
        (
            "legacy target-design pointer heading",
            re.compile(r"^##\s+redesign\s+pointer\b", re.IGNORECASE | re.MULTILINE),
        ),
        ("Target contrast:", re.compile(r"\btarget contrast:\b", re.IGNORECASE)),
        ("legacy target-design wording", re.compile(r"\btarget redesign\b", re.IGNORECASE)),
        ("design owner surface", re.compile(r"\b(?:re)?design owner surface\b", re.IGNORECASE)),
        (
            "Current shipped contrast:",
            re.compile(r"\bcurrent shipped contrast:\b", re.IGNORECASE),
        ),
        (
            "internal current-canon note",
            re.compile(r"\binternal current-canon note\b", re.IGNORECASE),
        ),
        (
            "Current mounted-node facts:",
            re.compile(r"\bcurrent mounted-node facts:\b", re.IGNORECASE),
        ),
        (
            "## Related current docs/pages",
            re.compile(r"^##\s+related\s+current\s+(?:docs|pages)\b", re.IGNORECASE | re.MULTILINE),
        ),
    )
    issues: list[tuple[Path, str]] = []
    for path in sorted(reference_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for display_marker, pattern in banned_patterns:
            if pattern.search(text):
                issues.append((path, display_marker))
    return issues


def print_public_reference_issues(inventory: DocsFreezeInventory) -> None:
    print("Public reference contract issues:")
    if (
        not inventory.public_reference_status_issues
        and not inventory.public_reference_contrast_issues
    ):
        print("- none")
        return
    for path in inventory.public_reference_status_issues:
        print(f"- {path.relative_to(ROOT)}: public reference page must use `Status: Reference`")
    for path, marker in inventory.public_reference_contrast_issues:
        print(f"- {path.relative_to(ROOT)}: contains `{marker}`")
