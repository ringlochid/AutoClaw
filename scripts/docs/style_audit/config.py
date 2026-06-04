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


def _python_module_paths(*roots: Path) -> frozenset[Path]:
    return frozenset(
        path
        for root in roots
        if root.exists()
        for path in root.rglob("*.py")
        if path.is_file()
    )


def _runtime_materialization_relative_paths() -> tuple[Path, ...]:
    return (
        Path("__init__.py"),
        Path("launch/__init__.py"),
        Path("launch/bootstrap/__init__.py"),
        Path("launch/bootstrap/context.py"),
        Path("launch/bootstrap/criteria.py"),
        Path("launch/bootstrap/manifest.py"),
        Path("launch/bootstrap/projection.py"),
        Path("launch/bootstrap/revisions.py"),
        Path("launch/bootstrap/rows.py"),
        Path("launch/bootstrap/workspace.py"),
        Path("launch/persistence/__init__.py"),
        Path("launch/persistence/attempts.py"),
        Path("launch/persistence/flows.py"),
        Path("launch/persistence/runtime.py"),
        Path("projection/__init__.py"),
        Path("projection/attempt_materialization.py"),
        Path("projection/dispatch/__init__.py"),
        Path("projection/dispatch/materialization.py"),
        Path("projection/dispatch/prompt.py"),
        Path("projection/manifest/__init__.py"),
        Path("projection/manifest/checkpoint_handoff.py"),
        Path("projection/manifest/context.py"),
        Path("projection/manifest/current_context_queries.py"),
        Path("projection/manifest/materialization.py"),
        Path("projection/manifest/projection.py"),
        Path("projection/manifest/structural_palette.py"),
        Path("projection/manifest/tree.py"),
        Path("projection/projection_mappers.py"),
        Path("projection/runtime_state.py"),
        Path("prompt/__init__.py"),
        Path("prompt/asset_catalog.py"),
        Path("prompt/assets/__init__.py"),
        Path("prompt/bundle.py"),
        Path("prompt/instructions.py"),
        Path("prompt/sections/__init__.py"),
        Path("prompt/sections/context.py"),
        Path("prompt/sections/primitives.py"),
        Path("prompt/sections/rendering.py"),
        Path("prompt/structural_edit_palette.py"),
        Path("task_root/__init__.py"),
        Path("task_root/localization.py"),
        Path("task_root/paths.py"),
        Path("task_root/reads.py"),
        Path("task_root/writes.py"),
    )


def _app_runtime_materialization_shell_modules() -> frozenset[Path]:
    return frozenset(
        APPS_API_APP_ROOT / "runtime" / relative
        for relative in _runtime_materialization_relative_paths()
    )


def _app_runtime_phase6_shell_modules() -> frozenset[Path]:
    return (
        frozenset({APPS_API_APP_ROOT / "runtime" / "ids.py"})
        | _python_module_paths(
            APPS_API_APP_ROOT / "runtime" / "control",
            APPS_API_APP_ROOT / "runtime" / "effects",
            APPS_API_APP_ROOT / "runtime" / "openclaw",
            APPS_API_APP_ROOT / "runtime" / "replan",
            APPS_API_APP_ROOT / "runtime" / "watchdog",
        )
    )


def _app_owner_shell_modules() -> frozenset[Path]:
    return frozenset(
        {
            APPS_API_APP_ROOT / "config.py",
            APPS_API_APP_ROOT / "paths.py",
            APPS_API_APP_ROOT / "file_entrypoints.py",
            APPS_API_APP_ROOT / "schemas" / "__init__.py",
            APPS_API_APP_ROOT / "schemas" / "operation_failure.py",
        }
    ) | _app_runtime_materialization_shell_modules() | _python_module_paths(
        APPS_API_APP_ROOT / "core",
        APPS_API_APP_ROOT / "compiler",
        APPS_API_APP_ROOT / "db",
        APPS_API_APP_ROOT / "registry",
        APPS_API_APP_ROOT / "schemas" / "definitions",
        APPS_API_APP_ROOT / "schemas" / "runtime",
        APPS_API_APP_ROOT / "platform" / "managed_services",
    )


def _app_wrapper_modules() -> frozenset[Path]:
    return frozenset(
        {
            APPS_API_APP_ROOT / "main.py",
            APPS_API_APP_ROOT / "cli" / "main.py",
            APPS_API_APP_ROOT / "cli" / "root.py",
            APPS_API_APP_ROOT / "cli" / "commands" / "service.py",
            APPS_API_APP_ROOT / "cli" / "commands" / "onboard.py",
            APPS_API_APP_ROOT / "cli" / "commands" / "openclaw" / "gateway_bootstrap.py",
            APPS_API_APP_ROOT / "runtime" / "contracts.py",
            APPS_API_APP_ROOT / "runtime" / "contract_models" / "launch.py",
            APPS_API_APP_ROOT / "runtime" / "contract_models" / "primitives.py",
            APPS_API_APP_ROOT / "runtime" / "contract_models" / "projection.py",
            APPS_API_APP_ROOT / "runtime" / "contract_models" / "prompt.py",
            APPS_API_APP_ROOT / "runtime" / "ids.py",
            APPS_API_APP_ROOT / "runtime" / "launch" / "bootstrap" / "__init__.py",
            APPS_API_APP_ROOT / "runtime" / "projection" / "manifest" / "__init__.py",
            APPS_API_APP_ROOT / "service_managers" / "base.py",
            APPS_API_APP_ROOT / "service_managers" / "factory.py",
            APPS_API_APP_ROOT / "service_managers" / "launchd.py",
            APPS_API_APP_ROOT / "service_managers" / "schtasks.py",
            APPS_API_APP_ROOT / "service_managers" / "systemd.py",
        }
    ) | _app_owner_shell_modules() | _app_runtime_phase6_shell_modules()


def _legacy_openclaw_wrapper_modules() -> frozenset[Path]:
    return frozenset(
        {
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "__init__.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "bindings.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "common.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "mcp_operation_failures.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_mcp" / "__init__.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_mcp" / "contracts.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_mcp" / "server.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_server.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "operator_mcp" / "__init__.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "operator_mcp" / "server.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "operator_server.py",
        }
    )


def _src_runtime_control_bridge_wrapper_modules() -> frozenset[Path]:
    return frozenset()


def _src_runtime_wrapper_modules() -> frozenset[Path]:
    return frozenset()


def _src_runtime_openclaw_gateway_shell_modules() -> frozenset[Path]:
    return _python_module_paths(AUTOCLAW_SRC_PACKAGE_ROOT / "runtime" / "openclaw")


def _src_owner_wrapper_modules() -> frozenset[Path]:
    return frozenset(
        {
            AUTOCLAW_SRC_PACKAGE_ROOT / "api" / "errors.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "api" / "router.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "integrations" / "openclaw" / "__init__.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "integrations" / "openclaw" / "node_mcp" / "__init__.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "integrations" / "openclaw" / "operator_mcp" / "__init__.py",
        }
    )


def _approved_wrapper_modules() -> frozenset[Path]:
    return (
        _app_wrapper_modules()
        | frozenset({AUTOCLAW_PACKAGE_ROOT / "cli.py", AUTOCLAW_PACKAGE_ROOT / "main.py"})
        | _legacy_openclaw_wrapper_modules()
        | _src_runtime_control_bridge_wrapper_modules()
        | _src_runtime_wrapper_modules()
        | _src_runtime_openclaw_gateway_shell_modules()
        | _src_owner_wrapper_modules()
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


def _legacy_openclaw_import_exceptions() -> frozenset[Path]:
    return frozenset(
        {
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "__init__.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "bindings.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "common.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "mcp_operation_failures.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_mcp" / "__init__.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_mcp" / "contracts.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_mcp" / "server.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "node_server.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "operator_mcp" / "__init__.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "operator_mcp" / "server.py",
            AUTOCLAW_PACKAGE_ROOT / "openclaw" / "operator_server.py",
        }
    )


def _src_runtime_import_exceptions() -> frozenset[Path]:
    return frozenset(
        {
            AUTOCLAW_SRC_PACKAGE_ROOT / "runtime" / "launch" / "__init__.py",
        }
    )


def _src_integration_openclaw_import_exceptions() -> frozenset[Path]:
    return frozenset(
        {
            AUTOCLAW_SRC_PACKAGE_ROOT / "integrations" / "openclaw" / "bindings.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "integrations" / "openclaw" / "common.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "integrations" / "openclaw" / "mcp_operation_failures.py",
            AUTOCLAW_SRC_PACKAGE_ROOT
            / "integrations"
            / "openclaw"
            / "operator_mcp"
            / "definition_tools.py",
        }
    )


def _src_owner_import_exceptions() -> frozenset[Path]:
    return frozenset(
        {
            AUTOCLAW_SRC_PACKAGE_ROOT / "api" / "errors.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "api" / "router.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "cli" / "__init__.py",
            AUTOCLAW_SRC_PACKAGE_ROOT / "main.py",
        }
    )


def _openclaw_gateway_public_naming_exceptions() -> frozenset[tuple[Path, str]]:
    return frozenset(
        {
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/adapter.py", "check_compatibility"),
            (
                ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/contracts.py",
                "retry_used_cached_device_token",
            ),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/contracts.py", "aborted"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/contracts.py", "yielded"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/contracts.py", "accepted"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/discovery.py", "binary_found"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/discovery.py", "config_exists"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/discovery.py", "loopback"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/discovery.py", "token_available"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/discovery.py", "password_available"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/fixtures.py", "aborted"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/fixtures.py", "yielded"),
            (
                ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/handshake.py",
                "use_cached_device_token",
            ),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/host_setup.py", "run_openclaw_cli"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/protocol.py", "ok"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/protocol.py", "aborted"),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/protocol.py", "yielded"),
            (
                ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/request_builders.py",
                "use_cached_device_token",
            ),
            (
                ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/request_builders.py",
                "retry_used_cached_device_token",
            ),
            (ROOT / "apps/api/src/autoclaw/integrations/openclaw/gateway/runtime_handle.py", "request_sent"),
        }
    )


def _runtime_assignment_public_naming_exceptions() -> frozenset[tuple[Path, str]]:
    return frozenset(
        {
            (ROOT / "apps/api/src/autoclaw/runtime/control/assignment/service.py", "read_after_commit"),
            (ROOT / "apps/api/src/autoclaw/runtime/control/boundary/service.py", "read_after_commit"),
        }
    )


def _runtime_dispatch_public_naming_exceptions() -> frozenset[tuple[Path, str]]:
    return frozenset(
        {
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/control.py",
                "stage_launch_projection_outputs",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/gateway/cleanup.py",
                "abort_requested",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/gateway/contracts.py",
                "abort_requested",
            ),
            (ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/gateway/contracts.py", "terminal"),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/gateway/contracts.py",
                "request_sent",
            ),
            (ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/gateway/session.py", "fenced"),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/gateway/session.py",
                "continuity_authority_exists",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/openclaw_runtime/event_ingest.py",
                "run_dispatch_ingest",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/openclaw_runtime/event_ingest.py",
                "advances_liveness",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/openclaw_runtime/lifecycle.py",
                "abort_remote",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/openclaw_runtime/lifecycle.py",
                "run_registered_dispatch_ingest",
            ),
            (ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/openclaw_runtime/models.py", "closed"),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/openclaw_runtime/models.py",
                "advances_liveness",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/openclaw_runtime/models.py",
                "saw_provider_progress",
            ),
            (ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/openclaw_runtime/models.py", "closing"),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/dispatch/opening.py",
                "stage_launch_projection_outputs",
            ),
            (ROOT / "apps/api/src/autoclaw/runtime/control/failures.py", "retryable"),
        }
    )


def _runtime_parent_tools_public_naming_exceptions() -> frozenset[tuple[Path, str]]:
    return frozenset(
        {
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/parent_tool_actions.py",
                "handle_structural_add",
            ),
            (ROOT / "apps/api/src/autoclaw/runtime/control/parent_tool_actions.py", "read_after_commit"),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/parent_tool_actions.py",
                "handle_structural_update",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/parent_tool_actions.py",
                "handle_structural_remove",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/parent_tool_actions.py",
                "handle_release_green",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/parent_tool_actions.py",
                "handle_release_blocked",
            ),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/parent_tool_actions.py",
                "handle_assign_child",
            ),
            (ROOT / "apps/api/src/autoclaw/runtime/control/parent_tools.py", "read_after_commit"),
        }
    )


def _runtime_release_public_naming_exceptions() -> frozenset[tuple[Path, str]]:
    return frozenset(
        {
            (ROOT / "apps/api/src/autoclaw/runtime/control/release/basis.py", "boundary_mode"),
            (
                ROOT / "apps/api/src/autoclaw/runtime/control/release/preconditions.py",
                "boundary_mode",
            ),
        }
    )


def _runtime_effects_public_naming_exceptions() -> frozenset[tuple[Path, str]]:
    return frozenset(
        {
            (ROOT / "apps/api/src/autoclaw/runtime/effects/queue.py", "apply_post_commit_actions"),
            (ROOT / "apps/api/src/autoclaw/runtime/effects/task_reconcile.py", "pending"),
            (ROOT / "apps/api/src/autoclaw/runtime/effects/task_reconcile.py", "changed"),
            (ROOT / "apps/api/src/autoclaw/runtime/effects/worker.py", "stop_requested"),
            (ROOT / "apps/api/src/autoclaw/runtime/effects/writes.py", "run_runtime_write"),
            (ROOT / "apps/api/src/autoclaw/runtime/replan/defaults.py", "apply_child_defaults"),
            (ROOT / "apps/api/src/autoclaw/runtime/watchdog/manager.py", "stop_requested"),
        }
    )


def _approved_public_naming_exceptions() -> frozenset[tuple[Path, str]]:
    return (
        _openclaw_gateway_public_naming_exceptions()
        | _runtime_assignment_public_naming_exceptions()
        | _runtime_dispatch_public_naming_exceptions()
        | _runtime_parent_tools_public_naming_exceptions()
        | _runtime_release_public_naming_exceptions()
        | _runtime_effects_public_naming_exceptions()
    )


def _approved_import_direction_exception_modules() -> frozenset[Path]:
    return (
        frozenset(
            {
                APPS_API_APP_ROOT / "main.py",
                APPS_API_APP_ROOT / "cli" / "__init__.py",
                APPS_API_APP_ROOT / "cli" / "main.py",
                AUTOCLAW_PACKAGE_ROOT / "cli.py",
                AUTOCLAW_PACKAGE_ROOT / "main.py",
            }
        )
        | _legacy_openclaw_import_exceptions()
        | _app_owner_shell_modules()
        | _app_runtime_phase6_shell_modules()
        | _src_runtime_import_exceptions()
        | _src_integration_openclaw_import_exceptions()
        | _src_owner_import_exceptions()
    )


def _public_naming_scan_roots() -> tuple[Path, ...]:
    return (
        AUTOCLAW_PACKAGE_ROOT,
        AUTOCLAW_SRC_PACKAGE_ROOT,
        APPS_API_APP_ROOT / "api",
        APPS_API_APP_ROOT / "cli",
        APPS_API_APP_ROOT / "cli_commands",
        APPS_API_APP_ROOT / "platform",
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
        approved_public_naming_exceptions=_approved_public_naming_exceptions(),
        disallowed_generic_module_names=DISALLOWED_GENERIC_MODULE_NAMES,
        inexact_package_names=INEXACT_PACKAGE_NAMES,
        public_naming_scan_roots=_public_naming_scan_roots(),
        public_naming_extra_modules=_public_naming_extra_modules(),
        module_shape_scan_roots=_module_shape_scan_roots(),
        module_shape_excluded_modules=frozenset({AUTOCLAW_SRC_PACKAGE_ROOT / "main.py"}),
    )
