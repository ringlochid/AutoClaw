from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stdout
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.cli_commands.bootstrap import (
    cmd_init,
    ensure_database_ready_with_legacy_sqlite_repair,
    update_config_sections,
)
from app.cli_commands.openclaw_support import (
    collect_openclaw_preflight,
    emit_openclaw_preflight_failure,
)
from app.cli_commands.openclaw_wrapper import (
    WrapperStateResult,
    bootstrap_openclaw_gateway_access,
    inspect_openclaw_integration,
    reconcile_openclaw_setup,
)
from app.cli_commands.server_config import (
    apply_server_config_overrides,
    build_server_bind_check_payload,
    emit_server_bind_check_failure,
)
from app.cli_commands.service import (
    DEFAULT_SERVICE_NAME,
    cmd_service_install,
    collect_service_status,
)
from app.cli_support import coerce_path, command_env, print_json
from app.config import DEFAULT_API_PORT, load_settings
from app.db.session import ping_database, verify_database_schema
from app.paths import ensure_runtime_dirs
from app.runtime.openclaw.host_setup import host_base_url_from_config
from app.terminal.note import note
from app.terminal.prompts import PromptUnavailableError, SelectOption, confirm, select, text
from app.terminal.theme import accent, heading, muted, rich_enabled, success, warn

REDACTED_VALUE = "__AUTOCLAW_REDACTED__"

DEFAULT_WEB_CONSOLE_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
)


def _prompt_unavailable(command_name: str, exc: PromptUnavailableError) -> int:
    rich = rich_enabled()
    print(heading(command_name, rich=rich))
    print(warn(str(exc), rich=rich))
    print(muted("Rerun with --non-interactive when no TTY is available.", rich=rich))
    return 2


def _interactive_onboard_plan(args: argparse.Namespace) -> tuple[bool, bool]:
    rich = rich_enabled(args)
    note(
        (
            "This guided flow will initialize local AutoClaw state, reconcile the "
            "OpenClaw wrapper contract, and optionally install the managed service."
        ),
        "AutoClaw onboard",
        rich=rich,
    )
    if not confirm("Continue with guided onboarding?", default=True):
        return False, False
    install_daemon = False
    if not getattr(args, "skip_daemon", False):
        install_daemon = confirm("Install the managed service now?", default=True)
    return True, install_daemon


def _resolve_gateway_port_from_url(base_url: str | None) -> int | None:
    if not base_url:
        return None
    try:
        return urlparse(base_url).port
    except ValueError:
        return None


def _interactive_onboard_ports(
    args: argparse.Namespace,
    *,
    config_path: Path,
) -> tuple[int, int]:
    rich = rich_enabled(args)
    preflight = collect_openclaw_preflight(
        config_path=config_path,
        data_dir=coerce_path(args.data_dir) if args.data_dir is not None else None,
        database_url=args.database_url,
        api_host=args.host,
        api_port=getattr(args, "port", None),
        log_level=args.log_level,
        api_key=args.api_key,
        internal_api_key=args.internal_api_key,
    )
    default_api_port = getattr(args, "port", None) or preflight.settings.api_port
    default_gateway_port = (
        getattr(args, "openclaw_gateway_port", None)
        or _resolve_gateway_port_from_url(preflight.settings.openclaw.base_url)
        or _resolve_gateway_port_from_url(host_base_url_from_config(preflight.host_state))
        or 18789
    )
    api_port = int(
        text(
            "Choose AutoClaw service / MCP port",
            default=str(default_api_port),
            hint=(
                "AutoClaw serves API and MCP on the same loopback port. "
                "Checks run after you choose it."
            ),
        )
    )
    gateway_port = int(
        text(
            "Choose OpenClaw gateway port",
            default=str(default_gateway_port),
            hint=(
                "AutoClaw connects to the local OpenClaw gateway on loopback. "
                "Compatibility checks run after you choose it."
            ),
        )
    )
    note(
        (
            f"Using AutoClaw on 127.0.0.1:{api_port} and OpenClaw on "
            f"127.0.0.1:{gateway_port}."
        ),
        "Selected ports",
        rich=rich,
    )
    return api_port, gateway_port


def _apply_openclaw_port_override(
    config_path: Path,
    *,
    gateway_port: int | None,
) -> None:
    if gateway_port is None:
        return
    update_config_sections(
        config_path,
        section_updates={
            "openclaw": {
                "base_url": f"http://127.0.0.1:{gateway_port}",
            }
        },
    )


def _interactive_configure_section(args: argparse.Namespace) -> str:
    rich = rich_enabled(args)
    note(
        "Choose which owned slice AutoClaw should reconcile in this run.",
        "AutoClaw configure",
        rich=rich,
    )
    section = getattr(args, "section", "all")
    if not isinstance(section, str):
        section = str(section)
    if section != "all":
        return section
    return select(
        "Select a configuration section",
        options=[
            SelectOption("openclaw", "OpenClaw wrapper", "Reconcile wrapper-owned material"),
            SelectOption("service", "Managed service", "Install or refresh the service unit"),
            SelectOption("local", "Local state", "Refresh local config and database state"),
            SelectOption("runtime", "Runtime", "Refresh local runtime prerequisites"),
            SelectOption(
                "definitions",
                "Definitions",
                "Re-seed packaged definition registry defaults.",
            ),
            SelectOption("web", "Web", "Refresh the local web console origin allowlist."),
            SelectOption("all", "All", "Reconcile every owned slice"),
        ],
        default_index=0,
        title="AutoClaw configure",
    )


def _redact_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    security = redacted.get("security")
    if isinstance(security, dict):
        security = dict(security)
        for key in ("api_key", "internal_api_key"):
            if security.get(key):
                security[key] = REDACTED_VALUE
        redacted["security"] = security
    openclaw = redacted.get("openclaw")
    if isinstance(openclaw, dict):
        openclaw = dict(openclaw)
        for key in ("gateway_token", "gateway_password"):
            if openclaw.get(key):
                openclaw[key] = REDACTED_VALUE
        redacted["openclaw"] = openclaw
    return redacted


def _settings_payload(settings: Any, config_path: Path) -> dict[str, Any]:
    payload = {
        "config_path": str(config_path),
        "paths": {
            "data_dir": str(settings.data_dir),
        },
        "database": {
            "url": settings.database_url,
            "echo": settings.database_echo,
        },
        "server": {
            "host": settings.api_host,
            "port": settings.api_port,
            "console_origins": settings.console_origins,
        },
        "logging": {
            "level": settings.log_level,
        },
        "security": {
            "api_key": settings.api_key,
            "internal_api_key": settings.internal_api_key,
        },
        "openclaw": settings.openclaw.model_dump(mode="json"),
        "runtime": settings.runtime.model_dump(mode="json"),
    }
    return _redact_config_payload(payload)


def _emit_onboard_openclaw_preflight_failure(
    *,
    args: argparse.Namespace,
    created_local_config: bool,
    openclaw_payload: dict[str, Any],
) -> int:
    return emit_openclaw_preflight_failure(
        command_name="AutoClaw onboard",
        args=args,
        openclaw_payload=openclaw_payload,
        stopped_before="stopped before database, OpenClaw integration, and service setup",
        payload_extra={"created_local_config": created_local_config},
    )


def cmd_config_path(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    payload = {"ok": True, "config_path": str(config_path)}
    if args.json:
        print_json(payload)
    else:
        print(accent(str(config_path), rich=rich_enabled(args)))
    return 0


def cmd_config_show(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
    payload = _settings_payload(settings, config_path)
    if args.json:
        print_json(payload)
    else:
        print_json(payload)
    return 0


async def cmd_doctor(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    findings: list[dict[str, Any]] = []
    if not config_path.is_file():
        payload = {
            "ok": False,
            "findings": [
                {
                    "name": "config_path",
                    "status": "error",
                    "detail": f"missing config file: {config_path}",
                }
            ],
        }
        if args.json:
            print_json(payload)
        else:
            rich = rich_enabled(args)
            print(heading("AutoClaw doctor", rich=rich))
            print(warn(f"missing config file: {config_path}", rich=rich))
        return 1

    preflight = collect_openclaw_preflight(config_path=config_path)
    if args.fix and preflight.host_state.support_status != "supported":
        return emit_openclaw_preflight_failure(
            command_name="AutoClaw doctor",
            args=args,
            openclaw_payload=preflight.payload,
            stopped_before="stopped before local and OpenClaw repair",
        )

    openclaw_payload = await inspect_openclaw_integration(config_path)
    findings.append(
        {
            "name": "openclaw_integration",
            "status": "ok" if openclaw_payload["ok"] else "warn",
            "detail": openclaw_payload,
        }
    )

    with command_env(config_path=config_path):
        settings = load_settings()
        ensure_runtime_dirs(config_dir=config_path.parent, data_dir=settings.data_dir)
        findings.append(
            {
                "name": "runtime_dirs",
                "status": "ok",
                "detail": str(settings.data_dir),
            }
        )
        if args.fix:
            database_repair_result = await ensure_database_ready_with_legacy_sqlite_repair(
                settings.database_url
            )
            repair_detail: dict[str, Any] = {"status": "applied db upgrade/seed repair"}
            if database_repair_result is not None:
                repair_detail.update(
                    {
                        "backup_path": str(database_repair_result.backup_path),
                        "migrated_tables": list(database_repair_result.migrated_tables),
                        "skipped_tables": list(database_repair_result.skipped_tables),
                    }
                )
            findings.append(
                {
                    "name": "database_fix",
                    "status": "ok",
                    "detail": repair_detail,
                }
            )
        else:
            await ping_database()
            await verify_database_schema()
            findings.append(
                {
                    "name": "database",
                    "status": "ok",
                    "detail": settings.database_url,
                }
            )
        definitions_root = resources.files("app.resources").joinpath("definitions")
        findings.append(
            {
                "name": "packaged_resources",
                "status": "ok" if definitions_root.is_dir() else "error",
                "detail": str(definitions_root),
            }
        )
        service_status = collect_service_status(DEFAULT_SERVICE_NAME)
        if service_status is None:
            findings.append(
                {
                    "name": "service_manager",
                    "status": "warn",
                    "detail": "managed service checks are unavailable on this platform",
                }
            )
        else:
            findings.append(
                {
                    "name": "service_manager",
                    "status": "ok" if service_status.installed else "warn",
                    "detail": service_status.to_payload(),
                }
            )
        if args.fix:
            wrapper_repair_result: WrapperStateResult = await reconcile_openclaw_setup(
                config_path,
                non_interactive=True,
            )
            findings.append(
                {
                    "name": "openclaw_integration_fix",
                    "status": "ok",
                    "detail": {
                        "worker_agent_id": wrapper_repair_result.worker_agent_id,
                        "operator_agent_id": wrapper_repair_result.operator_agent_id,
                        "mcp_servers_written": list(wrapper_repair_result.mcp_servers_written),
                        "bootstrapped_worker": wrapper_repair_result.bootstrapped_worker,
                        "bootstrapped_operator": wrapper_repair_result.bootstrapped_operator,
                    },
                }
            )

    ok = not any(item["status"] == "error" for item in findings)
    payload = {"ok": ok, "findings": findings}
    if args.json:
        print_json(payload)
    else:
        rich = rich_enabled(args)
        label = success("ok", rich=rich) if ok else warn("attention needed", rich=rich)
        print(heading("AutoClaw doctor", rich=rich))
        print(f"status: {label}")
        for finding in findings:
            print(f"{finding['name']}: {muted(str(finding['status']), rich=rich)}")
    return 0 if ok else 1


def _effective_openclaw_base_url(
    args: argparse.Namespace,
    *,
    gateway_port: int | None,
) -> str | None:
    if gateway_port is not None:
        return f"http://127.0.0.1:{gateway_port}"
    return None


async def cmd_onboard(args: argparse.Namespace) -> int:
    if not getattr(args, "non_interactive", False):
        try:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise PromptUnavailableError("interactive prompting requires a TTY")
        except PromptUnavailableError as exc:
            return _prompt_unavailable("AutoClaw onboard", exc)

    config_path = coerce_path(args.config)
    if not getattr(args, "non_interactive", False):
        try:
            proceed, install_daemon = _interactive_onboard_plan(args)
            needs_port_prompt = (
                getattr(args, "port", None) is None
                or getattr(args, "openclaw_gateway_port", None) is None
            )
            if needs_port_prompt:
                selected_api_port, selected_gateway_port = _interactive_onboard_ports(
                    args,
                    config_path=config_path,
                )
                if getattr(args, "port", None) is None:
                    args.port = selected_api_port
                if getattr(args, "openclaw_gateway_port", None) is None:
                    args.openclaw_gateway_port = selected_gateway_port
        except PromptUnavailableError as exc:
            return _prompt_unavailable("AutoClaw onboard", exc)
        if not proceed:
            rich = rich_enabled(args)
            print(heading("AutoClaw onboard", rich=rich))
            print(muted("cancelled before changes were applied", rich=rich))
            return 2
        args.install_daemon = install_daemon

    effective_base_url = _effective_openclaw_base_url(
        args,
        gateway_port=getattr(args, "openclaw_gateway_port", None),
    )
    preflight = collect_openclaw_preflight(
        config_path=config_path,
        data_dir=coerce_path(args.data_dir) if args.data_dir is not None else None,
        database_url=args.database_url,
        api_host=args.host,
        api_port=getattr(args, "port", None),
        log_level=args.log_level,
        api_key=args.api_key,
        internal_api_key=args.internal_api_key,
        openclaw_base_url=effective_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    if preflight.host_state.support_status != "supported":
        return _emit_onboard_openclaw_preflight_failure(
            args=args,
            created_local_config=False,
            openclaw_payload=preflight.payload,
        )

    created_local_config = False
    if args.force or not config_path.exists():
        with redirect_stdout(io.StringIO()):
            init_result = await cmd_init(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=args.data_dir,
                    database_url=args.database_url,
                    host=args.host,
                    port=args.port if args.port is not None else DEFAULT_API_PORT,
                    log_level=args.log_level,
                    api_key=args.api_key,
                    internal_api_key=args.internal_api_key,
                    force=True,
                    skip_db_upgrade=True,
                    json=False,
                )
            )
        if init_result != 0:
            return init_result
        created_local_config = True
    requested_port = getattr(args, "port", None)
    if requested_port is not None:
        apply_server_config_overrides(config_path, port=requested_port)
    _apply_openclaw_port_override(
        config_path,
        gateway_port=getattr(args, "openclaw_gateway_port", None),
    )
    with command_env(
        config_path=config_path,
        openclaw_base_url=effective_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    ):
        settings = load_settings()
    server_payload = build_server_bind_check_payload(
        settings.api_host,
        settings.api_port,
    )
    if not server_payload["ok"]:
        return emit_server_bind_check_failure(
            command_name="AutoClaw onboard",
            args=args,
            server_payload=server_payload,
            stopped_before="stopped before local runtime, OpenClaw integration, and service setup",
            payload_extra={
                "created_local_config": created_local_config,
                "openclaw": preflight.payload,
            },
        )

    database_repair: dict[str, Any] | None = None
    if not args.skip_db_upgrade:
        with command_env(config_path=config_path):
            settings = load_settings()
            repair_result = await ensure_database_ready_with_legacy_sqlite_repair(
                settings.database_url
            )
            if repair_result is not None:
                database_repair = {
                    "repaired": repair_result.repaired,
                    "backup_path": str(repair_result.backup_path),
                    "migrated_tables": list(repair_result.migrated_tables),
                    "skipped_tables": list(repair_result.skipped_tables),
                }

    wrapper_result = await reconcile_openclaw_setup(
        config_path,
        non_interactive=bool(getattr(args, "non_interactive", False)),
        openclaw_base_url=effective_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    preflight = collect_openclaw_preflight(
        config_path=config_path,
        openclaw_base_url=effective_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    openclaw_payload = preflight.payload
    daemon_installed = False
    if args.install_daemon:
        install_result = cmd_service_install(
            argparse.Namespace(
                config=str(config_path),
                data_dir=None,
                env_file=None,
                name=DEFAULT_SERVICE_NAME,
                unit_dir=None,
                port=requested_port,
                force=args.force,
                no_start=args.no_start,
                json=getattr(args, "json", False),
            )
        )
        if install_result != 0:
            return install_result
        daemon_installed = True

    payload = {
        "ok": True,
        "created_local_config": created_local_config,
        "database_repair": database_repair,
        "wrapper_state_path": str(wrapper_result.path),
        "worker_agent_id": wrapper_result.worker_agent_id,
        "operator_agent_id": wrapper_result.operator_agent_id,
        "bootstrapped_worker": wrapper_result.bootstrapped_worker,
        "bootstrapped_operator": wrapper_result.bootstrapped_operator,
        "mcp_servers_written": list(wrapper_result.mcp_servers_written),
        "material_paths": {key: str(value) for key, value in wrapper_result.material_paths.items()},
        "daemon_installed": daemon_installed,
        "server": server_payload,
        "openclaw": openclaw_payload,
    }
    if args.json:
        print_json(payload)
    else:
        rich = rich_enabled(args)
        server_target = f"{server_payload['host']}:{server_payload['port']}"
        openclaw_mode = (
            f"loopback={openclaw_payload['loopback']}, "
            f"auth={openclaw_payload['effective_auth'] or 'unknown'}"
        )
        print(heading("AutoClaw onboard", rich=rich))
        print(success("local setup complete", rich=rich))
        server_label = (
            success("free to bind", rich=rich)
            if server_payload["ok"]
            else warn(
                "busy",
                rich=rich,
            )
        )
        print(f"service port: {accent(server_target, rich=rich)} ({server_label})")
        openclaw_label = (
            success(openclaw_payload["support_status"], rich=rich)
            if openclaw_payload["support_status"] == "supported"
            else warn(openclaw_payload["support_status"], rich=rich)
        )
        print(f"openclaw: {openclaw_label} {muted(openclaw_mode, rich=rich)}")
        print(f"openclaw base url: {accent(openclaw_payload['base_url'], rich=rich)}")
        print(f"openclaw config: {accent(openclaw_payload['config_path'], rich=rich)}")
        print(
            "openclaw binary: "
            f"{accent(str(openclaw_payload['binary_path'] or 'not found'), rich=rich)}"
        )
        print(f"worker agent: {accent(wrapper_result.worker_agent_id, rich=rich)}")
        print(f"operator agent: {accent(wrapper_result.operator_agent_id, rich=rich)}")
        print(f"wrapper state: {accent(str(wrapper_result.path), rich=rich)}")
        if database_repair is not None:
            print(f"database repair: {warn('legacy schema backed up and reconciled', rich=rich)}")
            print(f"database backup: {accent(database_repair['backup_path'], rich=rich)}")
        if daemon_installed:
            print(f"managed service: {success('installed', rich=rich)}")
    return 0


async def cmd_configure(args: argparse.Namespace) -> int:
    if not getattr(args, "non_interactive", False):
        try:
            args.section = _interactive_configure_section(args)
        except PromptUnavailableError as exc:
            return _prompt_unavailable("AutoClaw configure", exc)
    config_path = coerce_path(args.config)
    section = args.section
    actions: list[str] = []
    if section in {"all", "openclaw", "service"}:
        if not getattr(args, "non_interactive", False) or getattr(
            args, "openclaw_gateway_token", None
        ):
            bootstrap_openclaw_gateway_access(
                config_path=config_path,
                non_interactive=bool(getattr(args, "non_interactive", False)),
                gateway_token=getattr(args, "openclaw_gateway_token", None),
                gateway_port=getattr(args, "openclaw_gateway_port", None),
            )
        preflight = collect_openclaw_preflight(config_path=config_path)
        if preflight.host_state.support_status != "supported":
            stopped_before = (
                "stopped before local runtime, OpenClaw integration, and service reconciliation"
                if section == "all"
                else "stopped before OpenClaw integration or service reconciliation"
            )
            return emit_openclaw_preflight_failure(
                command_name="AutoClaw configure",
                args=args,
                openclaw_payload=preflight.payload,
                stopped_before=stopped_before,
                payload_extra={"section": section, "actions": actions},
            )
    if section in {"all", "local", "runtime"}:
        with command_env(config_path=config_path):
            settings = load_settings()
            await ensure_database_ready_with_legacy_sqlite_repair(settings.database_url)
        actions.append("local_runtime")
    if section in {"all", "definitions"}:
        with command_env(config_path=config_path):
            settings = load_settings()
            await ensure_database_ready_with_legacy_sqlite_repair(settings.database_url)
        actions.append("definitions_registry")
    if section in {"all", "web"}:
        with command_env(config_path=config_path):
            load_settings()
        update_config_sections(
            config_path,
            section_updates={"server": {"console_origins": list(DEFAULT_WEB_CONSOLE_ORIGINS)}},
        )
        actions.append("web_console")
    if section in {"all", "openclaw"}:
        await reconcile_openclaw_setup(
            config_path,
            non_interactive=bool(getattr(args, "non_interactive", False)),
        )
        actions.append("openclaw_dual_surface")
    if section in {"all", "service"}:
        requested_port = getattr(args, "port", None)
        with command_env(config_path=config_path):
            settings = load_settings()
        server_payload = build_server_bind_check_payload(
            settings.api_host,
            requested_port if requested_port is not None else settings.api_port,
        )
        if not server_payload["ok"]:
            return emit_server_bind_check_failure(
                command_name="AutoClaw configure",
                args=args,
                server_payload=server_payload,
                stopped_before="stopped before managed service install",
                payload_extra={"section": section, "actions": actions},
            )
        service_install_result = cmd_service_install(
            argparse.Namespace(
                config=str(config_path),
                data_dir=None,
                env_file=None,
                name=DEFAULT_SERVICE_NAME,
                unit_dir=None,
                port=requested_port,
                force=args.force,
                no_start=args.no_start,
                json=getattr(args, "json", False),
            )
        )
        if service_install_result != 0:
            return service_install_result
        actions.append("service_manager")
    payload = {"ok": True, "section": section, "actions": actions}
    if args.json:
        print_json(payload)
    else:
        rich = rich_enabled(args)
        print(heading("AutoClaw configure", rich=rich))
        print(f"applied: {accent(', '.join(actions) or 'no changes', rich=rich)}")
    return 0


__all__ = [
    "cmd_config_path",
    "cmd_config_show",
    "cmd_configure",
    "cmd_doctor",
    "cmd_onboard",
]
