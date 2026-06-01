from __future__ import annotations

import ast
import importlib
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def _style_audit_namespace() -> SimpleNamespace:
    repo_root = Path(__file__).resolve().parents[4]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    return SimpleNamespace(
        cli=importlib.import_module("scripts.docs.style_audit.cli"),
        config=importlib.import_module("scripts.docs.style_audit.config"),
        layout_scan=importlib.import_module("scripts.docs.style_audit.layout_scan"),
        models=importlib.import_module("scripts.docs.style_audit.models"),
        module_loader=importlib.import_module("scripts.docs.style_audit.module_loader"),
        private_helpers=importlib.import_module("scripts.docs.style_audit.private_helpers"),
        report=importlib.import_module("scripts.docs.style_audit.report"),
        scan=importlib.import_module("scripts.docs.style_audit.scan"),
        test_structure_scan=importlib.import_module("scripts.docs.style_audit.test_structure_scan"),
        threshold_scan=importlib.import_module("scripts.docs.style_audit.threshold_scan"),
    )


def _audit_settings(
    tmp_path: Path,
    *,
    scan_roots: tuple[Path, ...] | None = None,
    excluded_paths: frozenset[Path] | None = None,
) -> Any:
    audit = _style_audit_namespace()
    apps_api_root = tmp_path / "apps" / "api"
    apps_api_root.mkdir(parents=True, exist_ok=True)
    if scan_roots is None:
        scan_root = tmp_path / "scan"
        scan_root.mkdir(parents=True, exist_ok=True)
        scan_roots = (scan_root,)
    for root in scan_roots:
        root.mkdir(parents=True, exist_ok=True)
    return audit.models.AuditSettings(
        root=tmp_path,
        apps_api_root=apps_api_root,
        scan_roots=scan_roots,
        excluded_paths=excluded_paths or frozenset(),
        file_split_review_threshold=600,
        file_no_growth_threshold=600,
        function_size_threshold=80,
        sibling_prefix_threshold=3,
        approved_wrapper_modules=frozenset(),
        disallowed_generic_module_names=frozenset({"helpers"}),
        inexact_package_names=frozenset({"runtime"}),
    )


def _write_module(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _empty_results(models: Any, root: Path) -> Any:
    module = models.ModuleRecord(
        path=root / "dummy.py",
        module_name="dummy",
        tree=ast.parse("pass\n"),
        lines=("pass",),
    )
    return models.AuditResults(
        modules=(module,),
        sibling_prefix_findings=(),
        import_wrapper_modules=(),
        star_import_collectors=(),
        phase_named_test_directory_findings=(),
        cross_lane_test_import_findings=(),
        import_placement_findings=(),
        wildcard_import_findings=(),
        todo_comment_findings=(),
        relative_import_depth_findings=(),
        cross_module_private_access_findings=(),
        gitkeep_placeholders=(),
        generic_module_name_findings=(),
        cross_module_findings=(),
        zero_reference_helpers=(),
        file_line_violations=(),
        function_size_violations=(),
    )


def test_style_audit_flags_top_level_import_placement(tmp_path: Path) -> None:
    settings = _audit_settings(tmp_path)
    module_path = settings.scan_roots[0] / "late_import.py"
    module_path.write_text(
        '"""module docstring"""\n'
        "from __future__ import annotations\n"
        '__all__ = ["value"]\n'
        "value = 1\n"
        "import math\n",
        encoding="utf-8",
    )

    audit = _style_audit_namespace()
    results = audit.scan.run_style_audit(settings)

    assert len(results.import_placement_findings) == 1
    finding = results.import_placement_findings[0]
    assert finding.path == module_path
    assert finding.line == 5
    assert finding.statement == "import math"


def test_style_audit_ignores_wildcard_imports_in_package_exports(tmp_path: Path) -> None:
    settings = _audit_settings(tmp_path)
    package_dir = settings.scan_roots[0] / "pkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text(
        "from .helpers import *\n",
        encoding="utf-8",
    )
    (package_dir / "helpers.py").write_text("VALUE = 1\n", encoding="utf-8")

    audit = _style_audit_namespace()
    results = audit.scan.run_style_audit(settings)

    assert results.wildcard_import_findings == ()


def test_style_audit_flags_wildcard_imports_outside_export_surfaces(tmp_path: Path) -> None:
    settings = _audit_settings(tmp_path)
    module_path = settings.scan_roots[0] / "consumer.py"
    module_path.write_text(
        "from helpers import *\n",
        encoding="utf-8",
    )
    (settings.scan_roots[0] / "helpers.py").write_text("VALUE = 1\n", encoding="utf-8")

    audit = _style_audit_namespace()
    results = audit.scan.run_style_audit(settings)

    assert len(results.wildcard_import_findings) == 1
    finding = results.wildcard_import_findings[0]
    assert finding.path == module_path
    assert finding.line == 1
    assert finding.source == "helpers"


def test_style_audit_flags_todo_without_owner_or_removal_detail(tmp_path: Path) -> None:
    settings = _audit_settings(tmp_path)
    module_path = settings.scan_roots[0] / "todo_example.py"
    module_path.write_text(
        "# TODO tighten this later\nvalue = 1\n",
        encoding="utf-8",
    )

    audit = _style_audit_namespace()
    results = audit.scan.run_style_audit(settings)

    assert len(results.todo_comment_findings) == 1
    finding = results.todo_comment_findings[0]
    assert finding.path == module_path
    assert finding.line == 1
    assert finding.text == "# TODO tighten this later"


def test_style_audit_accepts_todo_with_phase_detail(tmp_path: Path) -> None:
    settings = _audit_settings(tmp_path)
    (settings.scan_roots[0] / "todo_ok.py").write_text(
        "# TODO phase 5b: remove after packaging cutover\nvalue = 1\n",
        encoding="utf-8",
    )

    audit = _style_audit_namespace()
    results = audit.scan.run_style_audit(settings)

    assert results.todo_comment_findings == ()


def test_module_loader_skips_pycache_and_resolves_module_names(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    included_path = scan_root / "included.py"
    excluded_path = scan_root / "excluded.py"
    pycache_path = scan_root / "__pycache__" / "ignored.py"
    _write_module(included_path, "value = 1\n")
    _write_module(excluded_path, "value = 2\n")
    _write_module(pycache_path, "value = 3\n")

    settings = _audit_settings(
        tmp_path,
        scan_roots=(scan_root,),
        excluded_paths=frozenset({excluded_path}),
    )
    audit = _style_audit_namespace()

    assert audit.module_loader.iter_python_files(settings) == [included_path]

    app_module_path = tmp_path / "apps" / "api" / "app" / "runtime" / "sample.py"
    docs_module_path = tmp_path / "scripts" / "docs" / "tooling" / "example.py"
    _write_module(app_module_path, "value = 1\n")
    _write_module(docs_module_path, "value = 1\n")

    assert (
        audit.module_loader.module_name_for_path(app_module_path, settings) == "app.runtime.sample"
    )
    assert audit.module_loader.module_name_for_path(docs_module_path, settings) == "tooling.example"
    assert audit.module_loader.dotted_module_name(Path("pkg/__init__.py")) == "pkg"
    assert (
        audit.module_loader.resolve_module_name("pkg.sub.consumer", "source", 1) == "pkg.sub.source"
    )
    assert audit.module_loader.resolve_module_name("pkg.consumer", None, 1) == "pkg"
    assert audit.module_loader.resolve_module_name("pkg", "source", 2) is None
    assert audit.module_loader.count_non_comment_lines(("", "# x", "value = 1"), 1, 3) == 1


def test_build_audit_settings_scans_real_backend_and_tests() -> None:
    audit = _style_audit_namespace()
    settings = audit.config.build_audit_settings()

    expected_roots = {
        Path("scripts/docs"),
        Path("apps/api/app"),
        Path("apps/api/autoclaw"),
        Path("apps/api/tests/e2e"),
        Path("apps/api/tests/integration"),
        Path("apps/api/tests/unit"),
    }
    assert {path.relative_to(settings.root) for path in settings.scan_roots} == expected_roots
    assert settings.excluded_paths == frozenset()
    approved_wrappers = {
        path.relative_to(settings.root) for path in settings.approved_wrapper_modules
    }
    assert Path("apps/api/autoclaw/cli.py") in approved_wrappers
    assert Path("apps/api/autoclaw/main.py") in approved_wrappers
    assert Path("apps/api/autoclaw/openclaw/node_server.py") in approved_wrappers
    assert Path("apps/api/autoclaw/openclaw/operator_server.py") in approved_wrappers


def test_layout_scan_collects_structural_findings(tmp_path: Path) -> None:
    tests_root = tmp_path / "apps" / "api" / "tests" / "unit"
    runtime_root = tmp_path / "apps" / "api" / "app" / "runtime"
    routes_root = tmp_path / "apps" / "api" / "app" / "api" / "routes"
    settings = _audit_settings(
        tmp_path,
        scan_roots=(tests_root, runtime_root, routes_root),
    )
    audit = _style_audit_namespace()

    _write_module(tests_root / "test_alpha_one.py", "value = 1\n")
    _write_module(tests_root / "test_alpha_two.py", "value = 2\n")
    _write_module(tests_root / "test_alpha_three.py", "value = 3\n")
    _write_module(tests_root / "test_star.py", "from app.runtime.source import *\n")
    _write_module(runtime_root / "wrapper.py", '"""wrapper"""\nimport math\n')
    _write_module(runtime_root / "helpers.py", "value = 1\n")
    _write_module(routes_root / "allowed.py", "import math\n")
    (runtime_root / ".gitkeep").write_text("", encoding="utf-8")

    modules = audit.module_loader.load_modules(settings)
    findings = audit.layout_scan.collect_structural_findings(modules, settings)

    assert len(findings.sibling_prefix_findings) == 1
    assert findings.sibling_prefix_findings[0].prefix == "alpha"
    assert findings.import_wrapper_modules == (runtime_root / "wrapper.py",)
    assert len(findings.star_import_collectors) == 1
    assert findings.star_import_collectors[0].path == tests_root / "test_star.py"
    assert findings.gitkeep_placeholders == (runtime_root / ".gitkeep",)
    assert len(findings.generic_module_name_findings) == 1
    assert findings.generic_module_name_findings[0].path == runtime_root / "helpers.py"


def test_test_structure_scan_flags_phase_directories_and_cross_lane_imports(
    tmp_path: Path,
) -> None:
    tests_root = tmp_path / "apps" / "api" / "tests"
    settings = _audit_settings(
        tmp_path,
        scan_roots=(
            tests_root / "unit",
            tests_root / "integration",
            tests_root / "e2e",
        ),
    )
    audit = _style_audit_namespace()

    _write_module(
        tests_root / "unit" / "test_cli.py",
        "from tests.integration.phase5a.support import build_payload\n",
    )
    _write_module(
        tests_root / "integration" / "phase5a" / "support.py",
        "value = 1\n",
    )
    _write_module(
        tests_root / "e2e" / "phase4" / "test_lane.py",
        "value = 1\n",
    )

    modules = audit.module_loader.load_modules(settings)
    phase_directory_findings = (
        audit.test_structure_scan.collect_phase_named_test_directory_findings(
            modules,
            tests_root,
        )
    )
    cross_lane_findings = audit.test_structure_scan.collect_cross_lane_test_import_findings(
        modules,
        tests_root,
    )

    assert [finding.phase_directory_name for finding in phase_directory_findings] == [
        "phase4",
        "phase5a",
    ]
    assert len(cross_lane_findings) == 1
    assert cross_lane_findings[0].consumer_lane == "unit"
    assert cross_lane_findings[0].imported_lane == "integration"


def test_private_helper_scan_detects_direct_and_attribute_imports(tmp_path: Path) -> None:
    runtime_root = tmp_path / "apps" / "api" / "app" / "runtime"
    settings = _audit_settings(tmp_path, scan_roots=(runtime_root,))
    audit = _style_audit_namespace()

    _write_module(
        runtime_root / "source.py",
        "def _helper() -> int:\n    return 1\n\n\ndef _unused() -> int:\n    return 2\n",
    )
    _write_module(
        runtime_root / "consumer_direct.py",
        "from app.runtime.source import _helper\n\nvalue = _helper()\n",
    )
    _write_module(
        runtime_root / "consumer_attr.py",
        "import app.runtime.source as source\n\nvalue = source._helper()\n",
    )

    modules = audit.module_loader.load_modules(settings)
    module_name_to_path = {
        module.module_name: module.path for module in modules if module.module_name is not None
    }
    helpers, helpers_by_path = audit.private_helpers.collect_private_helpers(modules)
    references = audit.private_helpers.collect_same_module_references(
        helpers,
        helpers_by_path,
        modules,
    )
    findings = audit.private_helpers.collect_cross_module_references(
        helpers_by_path,
        module_name_to_path,
        modules,
        references,
    )
    access_findings = audit.private_helpers.collect_cross_module_private_access_findings(
        helpers_by_path,
        module_name_to_path,
        modules,
    )
    zero_reference = audit.private_helpers.zero_reference_helpers(helpers, references)

    assert [location.kind for _, location in findings] == ["module-attribute", "direct-import"]
    assert [finding.kind for finding in access_findings] == ["module-attribute", "direct-import"]
    assert [helper.name for helper in zero_reference] == ["_unused"]


def test_convention_scan_flags_deep_relative_imports_outside_tests(tmp_path: Path) -> None:
    app_root = tmp_path / "apps" / "api" / "app" / "runtime"
    test_root = tmp_path / "apps" / "api" / "tests" / "unit"
    settings = _audit_settings(tmp_path, scan_roots=(app_root, test_root))
    audit = _style_audit_namespace()

    _write_module(app_root / "deep_relative.py", "from ...helpers import thing\n")
    _write_module(test_root / "test_relative.py", "from ...helpers import thing\n")

    findings = audit.scan.run_style_audit(settings).relative_import_depth_findings

    assert len(findings) == 1
    assert findings[0].path == app_root / "deep_relative.py"
    assert findings[0].statement == "from ...helpers import thing"


def test_threshold_scan_reports_file_and_function_violations(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    settings = _audit_settings(tmp_path, scan_roots=(scan_root,))
    audit = _style_audit_namespace()

    _write_module(scan_root / "huge.py", "".join("value = 1\n" for _ in range(601)))
    long_body = "\n".join(f"    value_{index} = {index}" for index in range(81))
    _write_module(scan_root / "long_function.py", f"def long_function() -> None:\n{long_body}\n")

    modules = audit.module_loader.load_modules(settings)
    file_violations = audit.threshold_scan.collect_file_line_violations(modules, settings)
    function_violations = audit.threshold_scan.collect_function_size_violations(
        modules,
        settings.function_size_threshold,
    )

    assert file_violations == ((scan_root / "huge.py", 601),)
    assert len(function_violations) == 1
    assert function_violations[0].name == "long_function"
    assert function_violations[0].non_comment_lines == 82


def _results_with_findings(models: Any, tmp_path: Path) -> Any:
    helper = models.HelperDefinition(
        path=tmp_path / "helper.py",
        name="_helper",
        line=3,
        end_line=5,
        non_comment_lines=3,
    )
    reference = models.ReferenceLocation(
        path=tmp_path / "consumer.py",
        line=9,
        kind="direct-import",
    )
    base = _empty_results(models, tmp_path)
    return replace(
        base,
        sibling_prefix_findings=(
            models.SiblingPrefixFinding(
                directory=tmp_path / "pkg",
                prefix="alpha",
                members=(tmp_path / "pkg" / "alpha_one.py", tmp_path / "pkg" / "alpha_two.py"),
            ),
        ),
        import_wrapper_modules=(tmp_path / "wrapper.py",),
        star_import_collectors=(
            models.StarImportCollectorFinding(
                path=tmp_path / "test_star.py",
                imports=(models.StarImportLocation(line=4, source="app.runtime.source"),),
            ),
        ),
        phase_named_test_directory_findings=(
            models.PhaseNamedTestDirectoryFinding(
                directory=tmp_path / "tests" / "integration" / "phase5a",
                lane="integration",
                phase_directory_name="phase5a",
            ),
        ),
        cross_lane_test_import_findings=(
            models.CrossLaneTestImportFinding(
                path=tmp_path / "tests" / "unit" / "test_cli.py",
                line=12,
                statement="from tests.integration.phase5a.support import helper",
                consumer_lane="unit",
                imported_lane="integration",
            ),
        ),
        import_placement_findings=(
            models.ImportPlacementFinding(
                path=tmp_path / "late_import.py", line=6, statement="import math"
            ),
        ),
        wildcard_import_findings=(
            models.WildcardImportFinding(path=tmp_path / "wildcard.py", line=2, source="helpers"),
        ),
        todo_comment_findings=(
            models.TodoCommentFinding(path=tmp_path / "todo.py", line=1, text="# TODO fix this"),
        ),
        relative_import_depth_findings=(
            models.ImportPlacementFinding(
                path=tmp_path / "deep_relative.py",
                line=3,
                statement="from ...helpers import thing",
            ),
        ),
        cross_module_private_access_findings=(
            models.CrossModulePrivateAccessFinding(
                helper="_helper",
                helper_path=tmp_path / "helper.py",
                helper_line=3,
                consumer_path=tmp_path / "consumer.py",
                consumer_line=9,
                kind="direct-import",
            ),
        ),
        gitkeep_placeholders=(tmp_path / ".gitkeep",),
        generic_module_name_findings=(
            models.GenericModuleNameFinding(
                path=tmp_path / "helpers.py", package_name="runtime", module_name="helpers"
            ),
        ),
        cross_module_findings=((helper, reference),),
        zero_reference_helpers=(helper,),
        file_line_violations=((tmp_path / "big.py", 700),),
        function_size_violations=(
            models.FunctionSizeViolation(
                path=tmp_path / "big.py", name="too_big", line=10, non_comment_lines=99
            ),
        ),
    )


def test_render_audit_report_renders_all_sections(tmp_path: Path) -> None:
    audit = _style_audit_namespace()
    settings = _audit_settings(tmp_path)
    report = audit.report.render_audit_report(
        _results_with_findings(audit.models, tmp_path),
        settings,
    )

    assert "Execution STYLE audit" in report
    assert "Sibling-prefix layout families" in report
    assert "Phase-numbered test directories" in report
    assert "Cross-lane test imports" in report
    assert "Top-level import placement violations" in report
    assert "Wildcard imports outside deliberate export surfaces" in report
    assert "TODO comments missing owner or removal detail" in report
    assert "Cross-module private-helper imports" in report
    assert "Function-size threshold violations" in report


def test_render_audit_report_renders_no_findings_footer(tmp_path: Path) -> None:
    audit = _style_audit_namespace()
    report = audit.report.render_audit_report(
        _empty_results(audit.models, tmp_path),
        _audit_settings(tmp_path),
    )

    assert "No findings." in report
    assert "Rerun with `--fail-on-findings`" in report


def test_cli_main_respects_fail_on_findings(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    audit = _style_audit_namespace()
    settings = _audit_settings(tmp_path)
    results = audit.models.AuditResults(
        **{
            **_empty_results(audit.models, tmp_path).__dict__,
            "file_line_violations": ((tmp_path / "big.py", 700),),
        }
    )
    monkeypatch.setattr(audit.cli, "build_audit_settings", lambda: settings)
    monkeypatch.setattr(audit.cli, "run_style_audit", lambda _settings: results)
    monkeypatch.setattr(audit.cli, "render_audit_report", lambda *_args: "REPORT\n")

    assert audit.cli.main([]) == 0
    assert capsys.readouterr().out == "REPORT\n"
    assert audit.cli.main(["--fail-on-findings"]) == 1
    assert capsys.readouterr().out == "REPORT\n"
