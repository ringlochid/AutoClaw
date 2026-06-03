from __future__ import annotations

from pathlib import Path

from .models import AuditSettings

ROOT = Path(__file__).resolve().parents[3]
APPS_API_ROOT = ROOT / "apps" / "api"
APPS_API_APP_ROOT = APPS_API_ROOT / "app"
APPS_API_TESTS_ROOT = APPS_API_ROOT / "tests"
AUTOCLAW_PACKAGE_ROOT = APPS_API_ROOT / "autoclaw"
AUTOCLAW_SRC_PACKAGE_ROOT = APPS_API_ROOT / "src" / "autoclaw"
SCRIPTS_DOCS_ROOT = ROOT / "scripts" / "docs"
FILE_SPLIT_REVIEW_THRESHOLD = 600
FILE_NO_GROWTH_THRESHOLD = 600
FUNCTION_SIZE_THRESHOLD = 80
SIBLING_PREFIX_THRESHOLD = 3
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


def _style_audit_scan_roots() -> tuple[Path, ...]:
    return (
        SCRIPTS_DOCS_ROOT,
        APPS_API_APP_ROOT,
        AUTOCLAW_PACKAGE_ROOT,
        AUTOCLAW_SRC_PACKAGE_ROOT,
        APPS_API_TESTS_ROOT / "e2e",
        APPS_API_TESTS_ROOT / "integration",
        APPS_API_TESTS_ROOT / "unit",
    )


def _approved_wrapper_modules() -> frozenset[Path]:
    return frozenset(
        {
            APPS_API_APP_ROOT / "runtime" / "contracts.py",
            APPS_API_APP_ROOT / "runtime" / "ids.py",
            AUTOCLAW_PACKAGE_ROOT / "cli.py",
            AUTOCLAW_PACKAGE_ROOT / "main.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_server.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "operator_server.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "api" / "errors.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "api" / "router.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "main.py",
        }
    )


def _approved_wrapper_directories() -> frozenset[Path]:
    return frozenset({APPS_API_APP_ROOT / "api" / "routes"})


def _approved_duplicate_module_name_paths() -> frozenset[Path]:
    return frozenset(
        {
            AUTOCLAW_PACKAGE_ROOT / "__init__.py",
            AUTOCLAW_PACKAGE_ROOT / "__main__.py",
            AUTOCLAW_PACKAGE_ROOT / "cli.py",
            AUTOCLAW_PACKAGE_ROOT / "main.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "__init__.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "__main__.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "cli" / "__init__.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "main.py",
        }
    )


def _approved_import_direction_exception_modules() -> frozenset[Path]:
    return frozenset(
        {
            AUTOCLAW_PACKAGE_ROOT / "cli.py",
            AUTOCLAW_PACKAGE_ROOT / "main.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_server.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "operator_server.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "api" / "errors.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "api" / "router.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "cli" / "__init__.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "main.py",
        }
    )


def _public_naming_scan_roots() -> tuple[Path, ...]:
    return (
        AUTOCLAW_PACKAGE_ROOT,
        AUTOCLAW_SRC_PACKAGE_ROOT,
        APPS_API_APP_ROOT / "api",
        APPS_API_APP_ROOT / "cli",
        APPS_API_APP_ROOT / "cli_commands",
        APPS_API_APP_ROOT / "schemas",
        APPS_API_APP_ROOT / "registry",
    )


def _public_naming_extra_modules() -> frozenset[Path]:
    return frozenset(
        {
            APPS_API_APP_ROOT / "runtime" / "contracts.py",
            APPS_API_APP_ROOT / "runtime" / "ids.py",
            APPS_API_APP_ROOT / "file_entrypoints.py",
            APPS_API_APP_ROOT / "cli_support.py",
            APPS_API_APP_ROOT / "main.py",
        }
    )


def _module_shape_scan_roots() -> tuple[Path, ...]:
    return (
        APPS_API_APP_ROOT,
        AUTOCLAW_PACKAGE_ROOT,
        AUTOCLAW_SRC_PACKAGE_ROOT,
    )


def build_audit_settings(
    *,
    scan_roots: tuple[Path, ...] | None = None,
    excluded_paths: frozenset[Path] | None = None,
) -> AuditSettings:
    return AuditSettings(
        root=ROOT,
        apps_api_root=APPS_API_ROOT,
        scan_roots=scan_roots or _style_audit_scan_roots(),
        excluded_paths=excluded_paths or frozenset(),
        file_split_review_threshold=FILE_SPLIT_REVIEW_THRESHOLD,
        file_no_growth_threshold=FILE_NO_GROWTH_THRESHOLD,
        function_size_threshold=FUNCTION_SIZE_THRESHOLD,
        sibling_prefix_threshold=SIBLING_PREFIX_THRESHOLD,
        approved_wrapper_modules=_approved_wrapper_modules(),
        approved_wrapper_directories=_approved_wrapper_directories(),
        approved_duplicate_module_name_paths=_approved_duplicate_module_name_paths(),
        approved_import_direction_exception_modules=(
            _approved_import_direction_exception_modules()
        ),
        disallowed_generic_module_names=DISALLOWED_GENERIC_MODULE_NAMES,
        inexact_package_names=INEXACT_PACKAGE_NAMES,
        public_naming_scan_roots=_public_naming_scan_roots(),
        public_naming_extra_modules=_public_naming_extra_modules(),
        module_shape_scan_roots=_module_shape_scan_roots(),
        module_shape_excluded_modules=frozenset({AUTOCLAW_SRC_PACKAGE_ROOT / "main.py"}),
    )
