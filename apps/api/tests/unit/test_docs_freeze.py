from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace


def _ensure_repo_root_on_path() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    return repo_root


def _docs_freeze_namespace() -> SimpleNamespace:
    _ensure_repo_root_on_path()
    return SimpleNamespace(
        markdown_files=importlib.import_module("scripts.docs.markdown_format.files"),
        repo_refs=importlib.import_module("scripts.docs.docs_freeze.repo_refs"),
        inventory=importlib.import_module("scripts.docs.docs_freeze.validation.inventory"),
        record_rules=importlib.import_module("scripts.docs.docs_freeze.record_rules"),
    )


def test_iter_maintained_markdown_files_includes_product_and_root_docs() -> None:
    repo_root = _ensure_repo_root_on_path()
    docs_freeze = _docs_freeze_namespace()

    maintained_paths = {
        path.relative_to(repo_root)
        for path in docs_freeze.markdown_files.iter_maintained_markdown_files(repo_root)
    }

    assert Path("README.md") in maintained_paths
    assert Path("docs/README.md") in maintained_paths
    assert Path("docs/product/README.md") in maintained_paths
    assert Path("docs/reference/README.md") in maintained_paths
    assert Path("docs-internal/README.md") in maintained_paths
    assert Path("docs-internal/archive/03-old-version-docs-disposition.md") in maintained_paths


def test_repo_path_reference_issues_scan_root_readme() -> None:
    docs_freeze = _docs_freeze_namespace()

    issues = docs_freeze.repo_refs.line_repo_path_reference_issues(
        doc_path=Path("README.md"),
        line_number=1,
        line="Run `scripts/docs/does_not_exist.py` after edits.",
    )

    assert len(issues) == 1
    assert issues[0].reason == "missing_path"
    assert issues[0].normalized_reference == "scripts/docs/does_not_exist.py"


def test_repo_path_reference_issues_scan_relative_markdown_links() -> None:
    docs_freeze = _docs_freeze_namespace()

    issues = docs_freeze.repo_refs.line_repo_path_reference_issues(
        doc_path=Path("docs/reference/cli/example.md"),
        line_number=1,
        line="[Broken](../operator/does-not-exist.md)",
    )

    assert len(issues) == 1
    assert issues[0].reason == "missing_path"
    assert issues[0].normalized_reference == "docs/reference/operator/does-not-exist.md"


def test_repo_path_reference_issues_scan_backticked_relative_links() -> None:
    docs_freeze = _docs_freeze_namespace()

    issues = docs_freeze.repo_refs.line_repo_path_reference_issues(
        doc_path=Path("docs-internal/adr/example.md"),
        line_number=1,
        line="See `../design/v1/architecture/does-not-exist.md`.",
    )

    assert len(issues) == 1
    assert issues[0].reason == "missing_path"
    assert issues[0].normalized_reference == (
        "docs-internal/design/v1/architecture/does-not-exist.md"
    )


def test_repo_path_reference_issues_scan_backticked_relative_directories() -> None:
    docs_freeze = _docs_freeze_namespace()

    issues = docs_freeze.repo_refs.line_repo_path_reference_issues(
        doc_path=Path("docs/product/example.md"),
        line_number=1,
        line="See `../does-not-exist` for more detail.",
    )

    assert len(issues) == 1
    assert issues[0].reason == "missing_path"
    assert issues[0].normalized_reference == "docs/does-not-exist"


def test_public_reference_inventory_finds_target_status_and_contrast_markers() -> None:
    docs_freeze = _docs_freeze_namespace()

    reference_root = Path("/home/ubuntu/leo/projects/autoclaw/docs/reference")
    target_file = reference_root / "tmp-target.md"
    contrast_file = reference_root / "tmp-contrast.md"
    legacy_design_file = reference_root / "tmp-legacy-design.md"
    target_file.write_text("# x\n\nStatus: Target\n", encoding="utf-8")
    contrast_file.write_text(
        "# x\n\nStatus: Reference\n\n## Related current docs\n",
        encoding="utf-8",
    )
    legacy_design_file.write_text(
        "# x\n\nStatus: Reference\n\nThis page still says target redesign.\n",
        encoding="utf-8",
    )
    try:
        assert target_file in docs_freeze.inventory.public_reference_status_issues()
        assert (
            contrast_file,
            "## Related current docs/pages",
        ) in docs_freeze.inventory.public_reference_contrast_issues()
        assert (
            legacy_design_file,
            "legacy target-design wording",
        ) in docs_freeze.inventory.public_reference_contrast_issues()
    finally:
        target_file.unlink(missing_ok=True)
        contrast_file.unlink(missing_ok=True)
        legacy_design_file.unlink(missing_ok=True)


def test_doc_status_issues_find_invalid_execution_status() -> None:
    docs_freeze = _docs_freeze_namespace()

    execution_root = Path("/home/ubuntu/leo/projects/autoclaw/docs-internal/execution/v1")
    invalid_file = execution_root / "tmp-invalid-status.md"
    invalid_file.write_text("# x\n\nStatus: Target\n", encoding="utf-8")
    try:
        issues = [
            issue
            for issue in docs_freeze.inventory.doc_status_issues()
            if issue.path == invalid_file
        ]
        assert len(issues) == 1
        assert issues[0].found_status == "Target"
        assert issues[0].allowed_statuses == ("Reference",)
    finally:
        invalid_file.unlink(missing_ok=True)


def test_record_rules_include_phase55_phase6_and_phase7_pages() -> None:
    docs_freeze = _docs_freeze_namespace()

    assert docs_freeze.record_rules.PHASE_PAGE_BY_NAME["Phase 5.5"].as_posix().endswith(
        "phase-5.5-repo-hygiene-and-active-surface-freeze.md"
    )
    assert docs_freeze.record_rules.PHASE_PAGE_BY_NAME["Phase 6"].as_posix().endswith(
        "phase-6-source-structure-boundaries-and-naming-convergence.md"
    )
    assert docs_freeze.record_rules.PHASE_PAGE_BY_NAME["Phase 7"].as_posix().endswith(
        "phase-7-test-structure-and-proof-convergence.md"
    )
