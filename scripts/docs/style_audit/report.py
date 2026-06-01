from __future__ import annotations

from .models import AuditResults, AuditSettings
from .report_sections import (
    render_cross_module_findings,
    render_cross_module_private_access_findings,
    render_file_line_violations,
    render_function_size_violations,
    render_generic_module_name_findings,
    render_gitkeep_placeholders,
    render_import_placement_findings,
    render_import_wrapper_modules,
    render_relative_import_depth_findings,
    render_sibling_prefix_findings,
    render_star_import_collectors,
    render_todo_comment_findings,
    render_wildcard_import_findings,
    render_zero_reference_helpers,
)


def render_audit_report(results: AuditResults, settings: AuditSettings) -> str:
    lines = _render_summary_lines(results)

    if results.sibling_prefix_findings:
        lines.extend(render_sibling_prefix_findings(results.sibling_prefix_findings, settings.root))
    if results.import_wrapper_modules:
        lines.extend(render_import_wrapper_modules(results.import_wrapper_modules, settings.root))
    if results.star_import_collectors:
        lines.extend(render_star_import_collectors(results.star_import_collectors, settings.root))
    if results.import_placement_findings:
        lines.extend(
            render_import_placement_findings(
                results.import_placement_findings,
                settings.root,
            )
        )
    if results.wildcard_import_findings:
        lines.extend(
            render_wildcard_import_findings(
                results.wildcard_import_findings,
                settings.root,
            )
        )
    if results.todo_comment_findings:
        lines.extend(render_todo_comment_findings(results.todo_comment_findings, settings.root))
    if results.relative_import_depth_findings:
        lines.extend(
            render_relative_import_depth_findings(
                results.relative_import_depth_findings,
                settings.root,
            )
        )
    if results.gitkeep_placeholders:
        lines.extend(render_gitkeep_placeholders(results.gitkeep_placeholders, settings.root))
    if results.generic_module_name_findings:
        lines.extend(
            render_generic_module_name_findings(
                results.generic_module_name_findings,
                settings.root,
            )
        )
    if results.cross_module_findings:
        lines.extend(render_cross_module_findings(results.cross_module_findings, settings.root))
    if results.cross_module_private_access_findings:
        lines.extend(
            render_cross_module_private_access_findings(
                results.cross_module_private_access_findings,
                settings.root,
            )
        )
    if results.zero_reference_helpers:
        lines.extend(render_zero_reference_helpers(results.zero_reference_helpers, settings.root))
    if results.file_line_violations:
        lines.extend(render_file_line_violations(results.file_line_violations, settings))
    if results.function_size_violations:
        lines.extend(
            render_function_size_violations(
                results.function_size_violations,
                settings.root,
            )
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


def _render_summary_lines(results: AuditResults) -> list[str]:
    return [
        "Execution STYLE audit",
        "",
        f"- scanned python files: {len(results.modules)}",
        f"- sibling-prefix layout families: {len(results.sibling_prefix_findings)}",
        f"- import-only wrapper modules: {len(results.import_wrapper_modules)}",
        f"- star-import test collectors: {len(results.star_import_collectors)}",
        f"- top-level import placement violations: {len(results.import_placement_findings)}",
        f"- wildcard imports outside export surfaces: {len(results.wildcard_import_findings)}",
        f"- TODO comments missing owner/removal detail: {len(results.todo_comment_findings)}",
        f"- deep relative imports outside tests: {len(results.relative_import_depth_findings)}",
        f"- tracked .gitkeep placeholders: {len(results.gitkeep_placeholders)}",
        f"- generic module filenames: {len(results.generic_module_name_findings)}",
        f"- cross-module private-helper imports: {len(results.cross_module_findings)}",
        "- cross-module private access findings: "
        f"{len(results.cross_module_private_access_findings)}",
        f"- zero-reference private module helpers: {len(results.zero_reference_helpers)}",
        f"- file-size threshold violations: {len(results.file_line_violations)}",
        f"- function-size threshold violations: {len(results.function_size_violations)}",
        "",
    ]
