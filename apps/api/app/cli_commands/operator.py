from __future__ import annotations

import argparse
import io
import socket
import sys
from contextlib import redirect_stdout
from importlib import resources
from pathlib import Path
from typing import Any

from app.cli_commands.bootstrap import cmd_init, ensure_database_ready
from app.cli_commands.openclaw_support import (
    collect_openclaw_preflight,
    emit_openclaw_preflight_failure,
)
from app.cli_commands.openclaw_wrapper import (
    inspect_openclaw_integration,
    reconcile_openclaw_setup,
)
from app.cli_commands.service import (
    DEFAULT_SERVICE_NAME,
    cmd_service_install,
    collect_service_status,
)
from app.cli_support import coerce_path, command_env, print_json
from app.config import load_settings
from app.db.session import ping_database, verify_database_schema
from app.paths import ensure_runtime_dirs
from app.terminal.note import note
from app.terminal.prompts import PromptUnavailableError, SelectOption, confirm, select
from app.terminal.theme import accent, heading, muted, rich_enabled, success, warn

REDACTED_VALUE = "__AUTOCLAW_REDACTED__"


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


def _server_bind_check_payload(host: str, port: int) -> dict[str, Any]:
    try:
        candidates = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        return {
            "ok": False,
            "host": host,
            "port": port,
            "reason": str(exc),
        }

    errors: list[str] = []
    for family, socktype, proto, _canonname, sockaddr in candidates:
        test_socket = socket.socket(family, socktype, proto)
        try:
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6 and hasattr(socket, "IPV6_V6ONLY"):
                test_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            test_socket.bind(sockaddr)
            return {
                "ok": True,
                "host": host,
                "port": port,
                "address": sockaddr[0],
            }
        except OSError as exc:
            errors.append(str(exc))
        finally:
            test_socket.close()

    return {
        "ok": False,
        "host": host,
        "port": port,
        "reason": errors[-1] if errors else "bind failed",
    }


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
        stopped_before="stopped before local config, database, and service setup",
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
            await ensure_database_ready(settings.database_url)
            findings.append(
                {
                    "name": "database_fix",
                    "status": "ok",
                    "detail": "applied db upgrade/seed repair",
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
            repair_result = await reconcile_openclaw_setup(config_path, non_interactive=True)
            findings.append(
                {
                    "name": "openclaw_integration_fix",
                    "status": "ok",
                    "detail": {
                        "worker_agent_id": repair_result.worker_agent_id,
                        "operator_agent_id": repair_result.operator_agent_id,
                        "mcp_servers_written": list(repair_result.mcp_servers_written),
                        "bootstrapped_worker": repair_result.bootstrapped_worker,
                        "bootstrapped_operator": repair_result.bootstrapped_operator,
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


async def cmd_onboard(args: argparse.Namespace) -> int:
    if not getattr(args, "non_interactive", False):
        try:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise PromptUnavailableError("interactive prompting requires a TTY")
        except PromptUnavailableError as exc:
            return _prompt_unavailable("AutoClaw onboard", exc)

    config_path = coerce_path(args.config)
    preflight = collect_openclaw_preflight(
        config_path=config_path,
        data_dir=coerce_path(args.data_dir) if args.data_dir is not None else None,
        database_url=args.database_url,
        api_host=args.host,
        api_port=args.port,
        log_level=args.log_level,
        api_key=args.api_key,
        internal_api_key=args.internal_api_key,
    )
    if preflight.host_state.support_status != "supported":
        return _emit_onboard_openclaw_preflight_failure(
            args=args,
            created_local_config=False,
            openclaw_payload=preflight.payload,
        )

    if not getattr(args, "non_interactive", False):
        try:
            proceed, install_daemon = _interactive_onboard_plan(args)
        except PromptUnavailableError as exc:
            return _prompt_unavailable("AutoClaw onboard", exc)
        if not proceed:
            rich = rich_enabled(args)
            print(heading("AutoClaw onboard", rich=rich))
            print(muted("cancelled before changes were applied", rich=rich))
            return 2
        args.install_daemon = install_daemon
    created_local_config = False
    if args.force or not config_path.exists():
        with redirect_stdout(io.StringIO()):
            init_result = await cmd_init(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=args.data_dir,
                    database_url=args.database_url,
                    host=args.host,
                    port=args.port,
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

    if not args.skip_db_upgrade:
        with command_env(config_path=config_path):
            settings = load_settings()
            await ensure_database_ready(settings.database_url)

    wrapper_result = await reconcile_openclaw_setup(
        config_path,
        non_interactive=bool(getattr(args, "non_interactive", False)),
    )
    preflight = collect_openclaw_preflight(config_path=config_path)
    onboard_settings = preflight.settings
    server_payload = _server_bind_check_payload(
        onboard_settings.api_host,
        onboard_settings.api_port,
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
                force=args.force,
                no_start=args.no_start,
            )
        )
        if install_result != 0:
            return install_result
        daemon_installed = True

    payload = {
        "ok": True,
        "created_local_config": created_local_config,
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
            await ensure_database_ready(settings.database_url)
        actions.append("local_runtime")
    if section in {"all", "openclaw"}:
        await reconcile_openclaw_setup(
            config_path,
            non_interactive=bool(getattr(args, "non_interactive", False)),
        )
        actions.append("openclaw_dual_surface")
    if section in {"all", "service"}:
        cmd_service_install(
            argparse.Namespace(
                config=str(config_path),
                data_dir=None,
                env_file=None,
                name=DEFAULT_SERVICE_NAME,
                unit_dir=None,
                force=args.force,
                no_start=args.no_start,
            )
        )
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
