from __future__ import annotations

import argparse
from pathlib import Path

from .models import AuditSettings
from .report import render_audit_report
from .scan import run_style_audit

ROOT = Path(__file__).resolve().parents[3]
APPS_API_ROOT = ROOT / "apps" / "api"
SCAN_ROOTS = (
    ROOT / "scripts" / "docs",
    APPS_API_ROOT / "app" / "api",
    APPS_API_ROOT / "app" / "compiler",
    APPS_API_ROOT / "app" / "db",
    APPS_API_ROOT / "app" / "registry",
    APPS_API_ROOT / "app" / "runtime",
    APPS_API_ROOT / "app" / "schemas",
    APPS_API_ROOT / "tests" / "e2e",
    APPS_API_ROOT / "tests" / "integration",
    APPS_API_ROOT / "tests" / "unit",
)
EXCLUDED_PATHS = frozenset(
    {
        APPS_API_ROOT / "app" / "cli.py",
        APPS_API_ROOT / "tests" / "unit" / "test_cli.py",
    }
)
FILE_SPLIT_REVIEW_THRESHOLD = 400
FILE_NO_GROWTH_THRESHOLD = 600
FUNCTION_SIZE_THRESHOLD = 80
SIBLING_PREFIX_THRESHOLD = 3
APPROVED_WRAPPER_MODULES = frozenset(
    {
        APPS_API_ROOT / "app" / "runtime" / "contracts.py",
        APPS_API_ROOT / "app" / "runtime" / "ids.py",
    }
)
DISALLOWED_GENERIC_MODULE_NAMES = frozenset(
    {
        "helpers",
        "lookup",
        "misc",
        "models",
        "resources",
        "service",
        "shared",
        "support",
        "utils",
    }
)
INEXACT_PACKAGE_NAMES = frozenset(
    {
        "api",
        "compiler",
        "core",
        "db",
        "definitions",
        "models",
        "registry",
        "runtime",
        "schemas",
        "services",
        "tests",
    }
)


def build_audit_settings() -> AuditSettings:
    return AuditSettings(
        root=ROOT,
        apps_api_root=APPS_API_ROOT,
        scan_roots=SCAN_ROOTS,
        excluded_paths=EXCLUDED_PATHS,
        file_split_review_threshold=FILE_SPLIT_REVIEW_THRESHOLD,
        file_no_growth_threshold=FILE_NO_GROWTH_THRESHOLD,
        function_size_threshold=FUNCTION_SIZE_THRESHOLD,
        sibling_prefix_threshold=SIBLING_PREFIX_THRESHOLD,
        approved_wrapper_modules=APPROVED_WRAPPER_MODULES,
        disallowed_generic_module_names=DISALLOWED_GENERIC_MODULE_NAMES,
        inexact_package_names=INEXACT_PACKAGE_NAMES,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="exit non-zero when the audit reports findings",
    )
    args = parser.parse_args(argv)

    settings = build_audit_settings()
    results = run_style_audit(settings)
    print(render_audit_report(results, settings), end="")
    return 1 if args.fail_on_findings and results.has_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
