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
        import_direction_scan=importlib.import_module(
            "scripts.docs.style_audit.import_direction_scan"
        ),
        layout_scan=importlib.import_module("scripts.docs.style_audit.layout_scan"),
        models=importlib.import_module("scripts.docs.style_audit.models"),
        module_shape_scan=importlib.import_module("scripts.docs.style_audit.module_shape_scan"),
        module_loader=importlib.import_module("scripts.docs.style_audit.module_loader"),
        private_helpers=importlib.import_module("scripts.docs.style_audit.private_helpers"),
        public_naming_scan=importlib.import_module("scripts.docs.style_audit.public_naming_scan"),
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
        approved_wrapper_directories=frozenset({apps_api_root / "app" / "api" / "routes"}),
        approved_import_direction_exception_modules=frozenset(),
        disallowed_generic_module_names=frozenset({"helpers"}),
        inexact_package_names=frozenset({"runtime"}),
        public_naming_scan_roots=scan_roots,
        public_naming_extra_modules=frozenset(),
        module_shape_scan_roots=scan_roots,
        module_shape_excluded_modules=frozenset(),
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
        import_direction_findings=(),
        import_placement_findings=(),
        wildcard_import_findings=(),
        todo_comment_findings=(),
        relative_import_depth_findings=(),
        cross_module_private_access_findings=(),
        gitkeep_placeholders=(),
        generic_module_name_findings=(),
        duplicate_module_name_findings=(),
        public_naming_findings=(),
        module_shape_findings=(),
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
    assert (
        audit.module_loader.resolve_module_name(
            "pkg.sub.consumer",
            "source",
            1,
            current_path=Path("pkg/sub/consumer.py"),
        )
        == "pkg.sub.source"
    )
    assert (
        audit.module_loader.resolve_module_name(
            "pkg.sub",
            "source",
            1,
            current_path=Path("pkg/sub/__init__.py"),
        )
        == "pkg.sub.source"
    )
    assert audit.module_loader.resolve_module_name("pkg.consumer", None, 1) == "pkg"
    assert audit.module_loader.resolve_module_name("pkg", "source", 2) is None
    assert audit.module_loader.count_non_comment_lines(("", "# x", "value = 1"), 1, 3) == 1


def test_module_loader_dedupes_overlapping_scan_roots(tmp_path: Path) -> None:
    runtime_root = tmp_path / "apps" / "api" / "app" / "runtime"
    child_root = runtime_root / "nested"
    module_path = child_root / "sample.py"
    _write_module(module_path, "value = 1\n")
    settings = _audit_settings(tmp_path, scan_roots=(runtime_root, child_root))
    audit = _style_audit_namespace()

    assert audit.module_loader.iter_python_files(settings) == [module_path]


def test_build_audit_settings_exposes_phase6_wrapper_and_direction_scopes() -> None:
    audit = _style_audit_namespace()
    settings = audit.config.build_audit_settings()

    expected_roots = {
        Path("scripts/docs"),
        Path("apps/api/app"),
        Path("apps/api/autoclaw"),
        Path("apps/api/src/autoclaw"),
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
    approved_wrapper_directories = {
        path.relative_to(settings.root) for path in settings.approved_wrapper_directories
    }
    assert Path("apps/api/app/api/routes") in approved_wrapper_directories
    direction_exceptions = {
        path.relative_to(settings.root)
        for path in settings.approved_import_direction_exception_modules
    }
    assert Path("apps/api/app/main.py") in direction_exceptions
    assert Path("apps/api/autoclaw/cli.py") in direction_exceptions
    public_naming_roots = {
        path.relative_to(settings.root) for path in settings.public_naming_scan_roots
    }
    assert Path("apps/api/autoclaw") in public_naming_roots
    assert Path("apps/api/src/autoclaw") in public_naming_roots
    module_shape_roots = {
        path.relative_to(settings.root) for path in settings.module_shape_scan_roots
    }
    assert Path("apps/api/app") in module_shape_roots
    assert Path("apps/api/autoclaw") in module_shape_roots


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


def test_layout_scan_respects_configured_wrapper_directories_without_allowlisting_new_wrappers(
    tmp_path: Path,
) -> None:
    routes_root = tmp_path / "apps" / "api" / "app" / "api" / "routes"
    runtime_root = tmp_path / "apps" / "api" / "app" / "runtime"
    settings = replace(
        _audit_settings(
            tmp_path,
            scan_roots=(routes_root, runtime_root),
        ),
        approved_wrapper_directories=frozenset({routes_root}),
    )
    audit = _style_audit_namespace()

    _write_module(routes_root / "allowed.py", "import math\n")
    _write_module(runtime_root / "blocked.py", "import math\n")

    modules = audit.module_loader.load_modules(settings)
    findings = audit.layout_scan.collect_structural_findings(modules, settings)

    assert findings.import_wrapper_modules == (runtime_root / "blocked.py",)


def test_layout_scan_flags_duplicate_module_name_ownership_across_legacy_and_src_autoclaw(
    tmp_path: Path,
) -> None:
    legacy_root = tmp_path / "apps" / "api" / "autoclaw"
    src_root = tmp_path / "apps" / "api" / "src" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(legacy_root, src_root))
    audit = _style_audit_namespace()

    _write_module(legacy_root / "common.py", "VALUE = 1\n")
    _write_module(src_root / "common.py", "VALUE = 2\n")

    modules = audit.module_loader.load_modules(settings)
    findings = audit.layout_scan.collect_structural_findings(modules, settings)

    assert len(findings.duplicate_module_name_findings) == 1
    finding = findings.duplicate_module_name_findings[0]
    assert finding.module_name == "autoclaw.common"
    assert finding.paths == (legacy_root / "common.py", src_root / "common.py")


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


def test_style_audit_flags_autoclaw_modules_that_import_app_outside_approved_shims(
    tmp_path: Path,
) -> None:
    autoclaw_root = tmp_path / "apps" / "api" / "autoclaw"
    app_root = tmp_path / "apps" / "api" / "app"
    settings = _audit_settings(tmp_path, scan_roots=(autoclaw_root, app_root))
    audit = _style_audit_namespace()

    _write_module(app_root / "runtime" / "owner.py", "VALUE = 1\n")
    _write_module(
        autoclaw_root / "consumer.py",
        "from app.runtime.owner import VALUE\n",
    )

    findings = audit.scan.run_style_audit(settings).import_direction_findings

    assert len(findings) == 1
    assert findings[0].path == autoclaw_root / "consumer.py"
    assert findings[0].owner_family == "autoclaw"
    assert findings[0].violated_rule == "autoclaw-consumer-imports-app-owner"


def test_style_audit_allows_phase6_approved_shim_import_direction_exceptions(
    tmp_path: Path,
) -> None:
    autoclaw_root = tmp_path / "apps" / "api" / "autoclaw"
    app_root = tmp_path / "apps" / "api" / "app"
    consumer_path = autoclaw_root / "cli.py"
    settings = replace(
        _audit_settings(tmp_path, scan_roots=(autoclaw_root, app_root)),
        approved_import_direction_exception_modules=frozenset({consumer_path}),
    )
    audit = _style_audit_namespace()

    _write_module(app_root / "runtime" / "owner.py", "VALUE = 1\n")
    _write_module(consumer_path, "from app.runtime.owner import VALUE\n")

    findings = audit.scan.run_style_audit(settings).import_direction_findings

    assert findings == ()


def test_style_audit_flags_src_autoclaw_modules_that_import_legacy_autoclaw_owner(
    tmp_path: Path,
) -> None:
    src_root = tmp_path / "apps" / "api" / "src" / "autoclaw"
    legacy_root = tmp_path / "apps" / "api" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(src_root, legacy_root))
    audit = _style_audit_namespace()

    _write_module(legacy_root / "legacy_only.py", "VALUE = 1\n")
    _write_module(
        src_root / "consumer.py",
        "from autoclaw.legacy_only import VALUE\n",
    )

    findings = audit.scan.run_style_audit(settings).import_direction_findings

    assert len(findings) == 1
    assert findings[0].path == src_root / "consumer.py"
    assert findings[0].violated_rule == "src-autoclaw-consumer-imports-legacy-owner"


def test_style_audit_flags_src_autoclaw_modules_that_import_legacy_owner_outside_scan_root(
    tmp_path: Path,
) -> None:
    src_root = tmp_path / "apps" / "api" / "src" / "autoclaw"
    legacy_root = tmp_path / "apps" / "api" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(src_root,))
    audit = _style_audit_namespace()

    _write_module(legacy_root / "legacy_only.py", "VALUE = 1\n")
    _write_module(
        src_root / "consumer.py",
        "from autoclaw.legacy_only import VALUE\n",
    )

    findings = audit.scan.run_style_audit(settings).import_direction_findings

    assert len(findings) == 1
    assert findings[0].path == src_root / "consumer.py"
    assert findings[0].violated_rule == "src-autoclaw-consumer-imports-legacy-owner"


def test_style_audit_allows_src_autoclaw_modules_that_import_same_tree_owner_with_duplicate_name(
    tmp_path: Path,
) -> None:
    src_root = tmp_path / "apps" / "api" / "src" / "autoclaw"
    legacy_root = tmp_path / "apps" / "api" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(src_root,))
    audit = _style_audit_namespace()

    _write_module(src_root / "common.py", "VALUE = 1\n")
    _write_module(legacy_root / "common.py", "VALUE = 2\n")
    _write_module(src_root / "consumer.py", "from autoclaw.common import VALUE\n")

    findings = audit.scan.run_style_audit(settings).import_direction_findings

    assert findings == ()


def test_style_audit_flags_weak_public_function_verbs(tmp_path: Path) -> None:
    autoclaw_root = tmp_path / "apps" / "api" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(autoclaw_root,))
    audit = _style_audit_namespace()

    _write_module(
        autoclaw_root / "naming.py",
        "def handle_dispatch() -> None:\n    return None\n",
    )

    findings = audit.scan.run_style_audit(settings).public_naming_findings

    assert len(findings) == 1
    assert findings[0].name == "handle_dispatch"
    assert findings[0].reason == "weak_public_verb"


def test_style_audit_does_not_flag_names_with_weak_verb_prefix_collisions(
    tmp_path: Path,
) -> None:
    autoclaw_root = tmp_path / "apps" / "api" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(autoclaw_root,))
    audit = _style_audit_namespace()

    _write_module(
        autoclaw_root / "naming.py",
        "def runtime_exception_failure() -> None:\n    return None\n"
        "def checkpoint_id() -> str:\n    return 'x'\n",
    )

    findings = audit.scan.run_style_audit(settings).public_naming_findings

    assert findings == ()


def test_style_audit_flags_non_fact_shaped_public_booleans(tmp_path: Path) -> None:
    autoclaw_root = tmp_path / "apps" / "api" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(autoclaw_root,))
    audit = _style_audit_namespace()

    _write_module(
        autoclaw_root / "naming.py",
        "ready_flag = True\n",
    )

    findings = audit.scan.run_style_audit(settings).public_naming_findings

    assert len(findings) == 1
    assert findings[0].name == "ready_flag"
    assert findings[0].reason == "public_boolean_not_fact_shaped"


def test_style_audit_flags_non_fact_shaped_public_optional_booleans(tmp_path: Path) -> None:
    autoclaw_root = tmp_path / "apps" / "api" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(autoclaw_root,))
    audit = _style_audit_namespace()

    _write_module(
        autoclaw_root / "naming.py",
        "ready_flag: bool | None = None\n",
    )

    findings = audit.scan.run_style_audit(settings).public_naming_findings

    assert len(findings) == 1
    assert findings[0].name == "ready_flag"
    assert findings[0].reason == "public_boolean_not_fact_shaped"


def test_style_audit_flags_non_fact_shaped_public_boolean_parameters(tmp_path: Path) -> None:
    autoclaw_root = tmp_path / "apps" / "api" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(autoclaw_root,))
    audit = _style_audit_namespace()

    _write_module(
        autoclaw_root / "naming.py",
        "def build_runtime(ready_flag: bool, is_safe: bool = True) -> None:\n"
        "    return None\n",
    )

    findings = audit.scan.run_style_audit(settings).public_naming_findings

    assert len(findings) == 1
    assert findings[0].name == "ready_flag"
    assert findings[0].kind == "function-parameter"


def test_style_audit_flags_non_fact_shaped_public_boolean_fields_and_methods(
    tmp_path: Path,
) -> None:
    autoclaw_root = tmp_path / "apps" / "api" / "autoclaw"
    settings = _audit_settings(tmp_path, scan_roots=(autoclaw_root,))
    audit = _style_audit_namespace()

    _write_module(
        autoclaw_root / "naming.py",
        "class RuntimeState:\n"
        "    ready_flag: bool = False\n\n"
        "    def __init__(self, should_sync: bool, enabled_flag: bool = False) -> None:\n"
        "        self.enabled_flag = enabled_flag\n\n"
        "    def handle_runtime(self, allow_retry: bool) -> None:\n"
        "        return None\n",
    )

    findings = audit.scan.run_style_audit(settings).public_naming_findings

    assert [(finding.name, finding.kind, finding.reason) for finding in findings] == [
        ("ready_flag", "field", "public_boolean_not_fact_shaped"),
        ("enabled_flag", "constructor-parameter", "public_boolean_not_fact_shaped"),
        ("allow_retry", "method-parameter", "public_boolean_not_fact_shaped"),
        ("handle_runtime", "method", "weak_public_verb"),
    ]


def test_style_audit_flags_private_helper_before_public_entrypoint(tmp_path: Path) -> None:
    app_root = tmp_path / "apps" / "api" / "app"
    settings = _audit_settings(tmp_path, scan_roots=(app_root,))
    audit = _style_audit_namespace()

    _write_module(
        app_root / "runtime" / "ordering.py",
        "def _helper() -> None:\n    return None\n\n"
        "def public_entrypoint() -> None:\n    return None\n",
    )

    findings = audit.scan.run_style_audit(settings).module_shape_findings

    assert len(findings) == 1
    assert findings[0].reason == "public_after_private_helper"
    assert findings[0].name == "public_entrypoint"


def test_style_audit_flags_constant_after_function_block(tmp_path: Path) -> None:
    app_root = tmp_path / "apps" / "api" / "app"
    settings = _audit_settings(tmp_path, scan_roots=(app_root,))
    audit = _style_audit_namespace()

    _write_module(
        app_root / "runtime" / "ordering.py",
        "def public_entrypoint() -> None:\n    return None\n\n"
        "VALUE = 1\n",
    )

    findings = audit.scan.run_style_audit(settings).module_shape_findings

    assert len(findings) == 1
    assert findings[0].reason == "declaration_after_function_block"
    assert findings[0].name == "VALUE"


def test_style_audit_flags_public_entrypoint_after_shared_helper_value_reference(
    tmp_path: Path,
) -> None:
    app_root = tmp_path / "apps" / "api" / "app"
    settings = _audit_settings(tmp_path, scan_roots=(app_root,))
    audit = _style_audit_namespace()

    _write_module(
        app_root / "main.py",
        "def lifespan() -> object:\n    return object()\n\n"
        "def build_app() -> object:\n    return {\"lifespan\": lifespan}\n",
    )

    findings = audit.scan.run_style_audit(settings).module_shape_findings

    assert len(findings) == 1
    assert findings[0].reason == "public_after_shared_helper"
    assert findings[0].name == "build_app"


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
    helper, reference = _cross_module_sample_records(models, tmp_path)
    base = _empty_results(models, tmp_path)
    return replace(
        base,
        **_results_with_findings_payload(models, tmp_path, helper, reference),
    )


def _cross_module_sample_records(models: Any, tmp_path: Path) -> tuple[Any, Any]:
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
    return helper, reference


def _results_with_findings_payload(
    models: Any,
    tmp_path: Path,
    helper: Any,
    reference: Any,
) -> dict[str, Any]:
    return {
        **_results_import_findings_payload(models, tmp_path),
        **_results_structure_findings_payload(models, tmp_path, helper, reference),
        **_results_threshold_payload(models, tmp_path, helper),
    }


def _results_import_findings_payload(models: Any, tmp_path: Path) -> dict[str, Any]:
    return {
        "import_direction_findings": (
            models.ImportDirectionFinding(
                path=tmp_path / "autoclaw" / "consumer.py",
                line=5,
                statement="from app.runtime.owner import VALUE",
                owner_family="autoclaw",
                violated_rule="autoclaw-consumer-imports-app-owner",
            ),
        ),
        "import_placement_findings": (
            models.ImportPlacementFinding(
                path=tmp_path / "late_import.py", line=6, statement="import math"
            ),
        ),
        "wildcard_import_findings": (
            models.WildcardImportFinding(path=tmp_path / "wildcard.py", line=2, source="helpers"),
        ),
        "todo_comment_findings": (
            models.TodoCommentFinding(path=tmp_path / "todo.py", line=1, text="# TODO fix this"),
        ),
        "relative_import_depth_findings": (
            models.ImportPlacementFinding(
                path=tmp_path / "deep_relative.py",
                line=3,
                statement="from ...helpers import thing",
            ),
        ),
    }


def _results_structure_findings_payload(
    models: Any,
    tmp_path: Path,
    helper: Any,
    reference: Any,
) -> dict[str, Any]:
    return {
        "sibling_prefix_findings": (
            models.SiblingPrefixFinding(
                directory=tmp_path / "pkg",
                prefix="alpha",
                members=(tmp_path / "pkg" / "alpha_one.py", tmp_path / "pkg" / "alpha_two.py"),
            ),
        ),
        "import_wrapper_modules": (tmp_path / "wrapper.py",),
        "star_import_collectors": (
            models.StarImportCollectorFinding(
                path=tmp_path / "test_star.py",
                imports=(models.StarImportLocation(line=4, source="app.runtime.source"),),
            ),
        ),
        "phase_named_test_directory_findings": (
            models.PhaseNamedTestDirectoryFinding(
                directory=tmp_path / "tests" / "integration" / "phase5a",
                lane="integration",
                phase_directory_name="phase5a",
            ),
        ),
        "cross_lane_test_import_findings": (
            models.CrossLaneTestImportFinding(
                path=tmp_path / "tests" / "unit" / "test_cli.py",
                line=12,
                statement="from tests.integration.phase5a.support import helper",
                consumer_lane="unit",
                imported_lane="integration",
            ),
        ),
        "gitkeep_placeholders": (tmp_path / ".gitkeep",),
        "generic_module_name_findings": (
            models.GenericModuleNameFinding(
                path=tmp_path / "helpers.py", package_name="runtime", module_name="helpers"
            ),
        ),
        "duplicate_module_name_findings": (
            models.DuplicateModuleNameFinding(
                module_name="autoclaw.common",
                paths=(
                    tmp_path / "apps" / "api" / "autoclaw" / "common.py",
                    tmp_path / "apps" / "api" / "src" / "autoclaw" / "common.py",
                ),
            ),
        ),
        "public_naming_findings": (
            models.PublicNamingFinding(
                path=tmp_path / "naming.py",
                line=3,
                name="handle_dispatch",
                kind="function",
                reason="weak_public_verb",
            ),
        ),
        "module_shape_findings": (
            models.ModuleShapeFinding(
                path=tmp_path / "ordering.py",
                line=7,
                name="public_entrypoint",
                reason="public_after_private_helper",
            ),
        ),
        **_results_shared_surface_findings_payload(models, tmp_path, helper, reference),
    }


def _results_shared_surface_findings_payload(
    models: Any,
    tmp_path: Path,
    helper: Any,
    reference: Any,
) -> dict[str, Any]:
    return {
        "cross_module_private_access_findings": (
            models.CrossModulePrivateAccessFinding(
                helper="_helper",
                helper_path=tmp_path / "helper.py",
                helper_line=3,
                consumer_path=tmp_path / "consumer.py",
                consumer_line=9,
                kind="direct-import",
            ),
        ),
        "cross_module_findings": ((helper, reference),),
    }


def _results_threshold_payload(models: Any, tmp_path: Path, helper: Any) -> dict[str, Any]:
    return {
        "zero_reference_helpers": (helper,),
        "file_line_violations": ((tmp_path / "big.py", 700),),
        "function_size_violations": (
            models.FunctionSizeViolation(
                path=tmp_path / "big.py", name="too_big", line=10, non_comment_lines=99
            ),
        ),
    }


def test_render_audit_report_includes_phase6_sections(tmp_path: Path) -> None:
    audit = _style_audit_namespace()
    settings = _audit_settings(tmp_path)
    report = audit.report.render_audit_report(
        _results_with_findings(audit.models, tmp_path),
        settings,
    )

    assert "Execution STYLE audit" in report
    assert "Import-direction findings" in report
    assert "Module-shape findings" in report
    assert "Public naming findings" in report
    assert "Duplicate module-name ownership findings" in report
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


def test_cli_main_passes_explicit_scan_roots(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    audit = _style_audit_namespace()
    scan_root = tmp_path / "apps" / "api" / "app"
    settings = _audit_settings(tmp_path, scan_roots=(scan_root,))
    captured_scan_roots: dict[str, tuple[Path, ...]] = {}

    def _build_settings(*, scan_roots: tuple[Path, ...] | None = None) -> Any:
        captured_scan_roots["value"] = scan_roots or ()
        return settings

    monkeypatch.setattr(audit.cli, "_validated_scan_roots", lambda *_args: (scan_root,))
    monkeypatch.setattr(audit.cli, "build_audit_settings", _build_settings)
    monkeypatch.setattr(
        audit.cli,
        "run_style_audit",
        lambda _settings: _empty_results(audit.models, tmp_path),
    )
    monkeypatch.setattr(audit.cli, "render_audit_report", lambda *_args: "REPORT\n")
    _write_module(scan_root / "sample.py", "value = 1\n")

    assert audit.cli.main(["--scan-root", "apps/api/app"]) == 0
    assert captured_scan_roots["value"] == (scan_root,)
    assert capsys.readouterr().out == "REPORT\n"
