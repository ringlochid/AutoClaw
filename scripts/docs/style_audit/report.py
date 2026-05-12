from __future__ import annotations

from pathlib import Path

from .models import (
    AuditResults,
    AuditSettings,
    FunctionSizeViolation,
    HelperDefinition,
    ReferenceLocation,
)


def render_audit_report(results: AuditResults, settings: AuditSettings) -> str:
    lines = [
        "Execution STYLE audit",
        "",
        f"- scanned python files: {len(results.modules)}",
        f"- cross-module private-helper imports: {len(results.cross_module_findings)}",
        f"- zero-reference private module helpers: {len(results.zero_reference_helpers)}",
        f"- file-size threshold violations: {len(results.file_line_violations)}",
        f"- function-size threshold violations: {len(results.function_size_violations)}",
        "",
    ]

    if results.cross_module_findings:
        lines.extend(_render_cross_module_findings(results.cross_module_findings, settings.root))
    if results.zero_reference_helpers:
        lines.extend(_render_zero_reference_helpers(results.zero_reference_helpers, settings.root))
    if results.file_line_violations:
        lines.extend(_render_file_line_violations(results.file_line_violations, settings))
    if results.function_size_violations:
        lines.extend(
            _render_function_size_violations(results.function_size_violations, settings.root)
        )
    if not results.has_findings:
        lines.extend(["No findings.", ""])

    lines.extend(
        [
            "This command is report-only by default.",
            "Rerun with `--fail-on-findings` to make findings exit non-zero.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_cross_module_findings(
    findings: tuple[tuple[HelperDefinition, ReferenceLocation], ...],
    root: Path,
) -> list[str]:
    grouped: dict[tuple[Path, str], list[ReferenceLocation]] = {}
    for helper, location in findings:
        grouped.setdefault((helper.path, helper.name), []).append(location)

    lines = ["Cross-module private-helper imports", ""]
    for helper_path, helper_name in sorted(grouped):
        helper = next(
            finding_helper
            for finding_helper, _ in findings
            if finding_helper.path == helper_path and finding_helper.name == helper_name
        )
        lines.append(f"- {_format_helper(helper, root)}")
        for location in sorted(grouped[(helper_path, helper_name)], key=_reference_sort_key):
            lines.append(
                f"  - {location.path.relative_to(root)}:{location.line} via {location.kind}"
            )
        lines.append("")
    return lines


def _render_zero_reference_helpers(
    helpers: tuple[HelperDefinition, ...],
    root: Path,
) -> list[str]:
    lines = ["Zero-reference private module helpers", ""]
    for helper in helpers:
        lines.append(
            f"- {_format_helper(helper, root)} ({helper.non_comment_lines} non-comment lines)"
        )
    lines.append("")
    return lines


def _render_file_line_violations(
    violations: tuple[tuple[Path, int], ...],
    settings: AuditSettings,
) -> list[str]:
    lines = ["File-size threshold violations", ""]
    for path, line_count in violations:
        threshold = (
            f">{settings.file_no_growth_threshold} no-growth"
            if line_count > settings.file_no_growth_threshold
            else f">{settings.file_split_review_threshold} split-review"
        )
        lines.append(f"- {path.relative_to(settings.root)}: {line_count} lines ({threshold})")
    lines.append("")
    return lines


def _render_function_size_violations(
    violations: tuple[FunctionSizeViolation, ...],
    root: Path,
) -> list[str]:
    lines = ["Function-size threshold violations", ""]
    for violation in violations:
        lines.append(
            f"- {violation.path.relative_to(root)}:{violation.line} `{violation.name}` "
            f"({violation.non_comment_lines} non-comment lines)"
        )
    lines.append("")
    return lines


def _format_helper(helper: HelperDefinition, root: Path) -> str:
    return f"{helper.path.relative_to(root)}:{helper.line} `{helper.name}`"


def _reference_sort_key(location: ReferenceLocation) -> tuple[str, int, str]:
    return (location.path.as_posix(), location.line, location.kind)
