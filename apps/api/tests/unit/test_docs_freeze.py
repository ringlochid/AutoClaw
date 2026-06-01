from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_root_on_path() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    return repo_root


def test_iter_maintained_markdown_files_includes_product_and_root_docs() -> None:
    repo_root = _ensure_repo_root_on_path()

    from scripts.docs.markdown_format.files import iter_maintained_markdown_files

    maintained_paths = {
        path.relative_to(repo_root) for path in iter_maintained_markdown_files(repo_root)
    }

    assert Path("README.md") in maintained_paths
    assert Path("docs/README.md") in maintained_paths
    assert Path("docs/product/README.md") in maintained_paths


def test_repo_path_reference_issues_scan_root_readme() -> None:
    _ensure_repo_root_on_path()

    from scripts.docs.docs_freeze.repo_refs import line_repo_path_reference_issues

    issues = line_repo_path_reference_issues(
        doc_path=Path("README.md"),
        line_number=1,
        line="Run `scripts/docs/does_not_exist.py` after edits.",
    )

    assert len(issues) == 1
    assert issues[0].reason == "missing_path"
    assert issues[0].normalized_reference == "scripts/docs/does_not_exist.py"
