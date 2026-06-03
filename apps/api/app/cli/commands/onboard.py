from __future__ import annotations

import argparse
import asyncio
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.cli.commands.bootstrap import (
    cmd_init,
    ensure_database_ready_with_legacy_sqlite_repair,
    update_config_sections,
)
from app.cli.commands.openclaw.support import (
    collect_openclaw_preflight,
    emit_openclaw_preflight_failure,
)
from app.cli.commands.openclaw.wrapper import (
    reconcile_openclaw_setup,
)
from app.cli.commands.server_config import (
    build_server_bind_check_payload,
    emit_server_bind_check_failure,
    update_server_config_overrides,
)
from app.cli.commands.service import DEFAULT_SERVICE_NAME, cmd_service_install
from app.cli.terminal.note import note
from app.cli.terminal.prompts import PromptUnavailableError, confirm, text
from app.cli.terminal.theme import accent, heading, muted, rich_enabled, success, warn
from app.cli_support import coerce_path, command_env, print_json
from app.config import DEFAULT_API_PORT, load_settings
from app.paths import ensure_runtime_dirs
from app.runtime.openclaw.host_setup import host_base_url_from_config


async def cmd_onboard(args: argparse.Namespace) -> int:
    return await _cmd_onboard(args)


def _emit_prompt_unavailable_exit(command_name: str, exc: PromptUnavailableError) -> int:
    is_rich = rich_enabled()
    print(heading(command_name, is_rich=is_rich))
    print(warn(str(exc), is_rich=is_rich))
    print(muted("Rerun with --non-interactive when no TTY is available.", is_rich=is_rich))
    return 2


def _interactive_onboard_plan(args: argparse.Namespace) -> tuple[bool, bool]:
    is_rich = rich_enabled(args)
    note(
        (
            "This guided flow will initialize local AutoClaw state, reconcile the "
            "OpenClaw wrapper contract, and optionally install the managed service."
        ),
        "AutoClaw onboard",
        is_rich=is_rich,
    )
    if not confirm("Continue with guided onboarding?", is_default=True):
        return False, False
    install_daemon = False
    if not getattr(args, "skip_daemon", False):
        install_daemon = confirm("Install the managed service now?", is_default=True)
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
    is_rich = rich_enabled(args)
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
            default_value=str(default_api_port),
            hint=(
                "AutoClaw serves API and MCP on the same loopback port. "
                "Checks run after you choose it."
            ),
        )
    )
    gateway_port = int(
        text(
            "Choose OpenClaw gateway port",
            default_value=str(default_gateway_port),
            hint=(
                "AutoClaw connects to the local OpenClaw gateway on loopback. "
                "Compatibility checks run after you choose it."
            ),
        )
    )
    note(
        (f"Using AutoClaw on 127.0.0.1:{api_port} and OpenClaw on 127.0.0.1:{gateway_port}."),
        "Selected ports",
        is_rich=is_rich,
    )
    return api_port, gateway_port


def _persist_openclaw_port_override(
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


def _build_effective_openclaw_base_url(args: argparse.Namespace) -> str | None:
    gateway_port = getattr(args, "openclaw_gateway_port", None)
    if gateway_port is None:
        return None
    return f"http://127.0.0.1:{gateway_port}"


def _emit_onboard_preflight_failure(
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


def _collect_onboard_preflight(
    args: argparse.Namespace,
    *,
    config_path: Path,
    openclaw_base_url: str | None,
) -> Any:
    return collect_openclaw_preflight(
        config_path=config_path,
        data_dir=coerce_path(args.data_dir) if args.data_dir is not None else None,
        database_url=args.database_url,
        api_host=args.host,
        api_port=getattr(args, "port", None),
        log_level=args.log_level,
        api_key=args.api_key,
        internal_api_key=args.internal_api_key,
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )


def _prepare_interactive_onboard(args: argparse.Namespace) -> int | None:
    try:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise PromptUnavailableError("interactive prompting requires a TTY")
        proceed, install_daemon = _interactive_onboard_plan(args)
        needs_port_prompt = (
            getattr(args, "port", None) is None
            or getattr(args, "openclaw_gateway_port", None) is None
        )
        if needs_port_prompt:
            selected_api_port, selected_gateway_port = _interactive_onboard_ports(
                args,
                config_path=coerce_path(args.config),
            )
            if getattr(args, "port", None) is None:
                args.port = selected_api_port
            if getattr(args, "openclaw_gateway_port", None) is None:
                args.openclaw_gateway_port = selected_gateway_port
        if not proceed:
            is_rich = rich_enabled(args)
            print(heading("AutoClaw onboard", is_rich=is_rich))
            print(muted("cancelled before changes were applied", is_rich=is_rich))
            return 2
        args.install_daemon = install_daemon
        return None
    except PromptUnavailableError as exc:
        return _emit_prompt_unavailable_exit("AutoClaw onboard", exc)


async def _initialize_onboard_config(
    args: argparse.Namespace,
    *,
    config_path: Path,
) -> bool:
    if not args.force and await asyncio.to_thread(config_path.exists):
        return False
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
        raise RuntimeError(f"unexpected onboard init failure: {init_result}")
    return True


async def _repair_onboard_database(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.skip_db_upgrade:
        return None
    with command_env(config_path=args.config_path):
        settings = load_settings()
        repair_result = await ensure_database_ready_with_legacy_sqlite_repair(settings.database_url)
        if repair_result is None:
            return None
        return {
            "repaired": repair_result.is_repaired,
            "backup_path": str(repair_result.backup_path),
            "migrated_tables": list(repair_result.migrated_tables),
            "skipped_tables": list(repair_result.skipped_tables),
        }


def _apply_onboard_service_overrides(
    config_path: Path,
    *,
    requested_port: int | None,
    gateway_port: int | None,
) -> None:
    if requested_port is not None:
        update_server_config_overrides(config_path, port=requested_port)
    _persist_openclaw_port_override(
        config_path,
        gateway_port=gateway_port,
    )


def _load_onboard_server_payload(
    args: argparse.Namespace,
    *,
    config_path: Path,
    openclaw_base_url: str | None,
) -> dict[str, Any]:
    with command_env(
        config_path=config_path,
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    ):
        settings = load_settings()
    ensure_runtime_dirs(config_dir=config_path.parent, data_dir=settings.data_dir)
    return build_server_bind_check_payload(settings.api_host, settings.api_port)


async def _reconcile_onboard_openclaw(
    args: argparse.Namespace,
    *,
    config_path: Path,
    openclaw_base_url: str | None,
) -> tuple[Any, dict[str, Any]]:
    wrapper_result = await reconcile_openclaw_setup(
        config_path,
        is_non_interactive=bool(getattr(args, "non_interactive", False)),
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    preflight = collect_openclaw_preflight(
        config_path=config_path,
        openclaw_base_url=openclaw_base_url,
        openclaw_gateway_token=getattr(args, "openclaw_gateway_token", None),
    )
    return wrapper_result, preflight.payload


def _build_onboard_payload(
    *,
    created_local_config: bool,
    database_repair: dict[str, Any] | None,
    wrapper_result: Any,
    daemon_installed: bool,
    server_payload: dict[str, Any],
    openclaw_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": True,
        "created_local_config": created_local_config,
        "database_repair": database_repair,
        "wrapper_state_path": str(wrapper_result.path),
        "worker_agent_id": wrapper_result.worker_agent_id,
        "operator_agent_id": wrapper_result.operator_agent_id,
        "bootstrapped_worker": wrapper_result.is_worker_bootstrapped,
        "bootstrapped_operator": wrapper_result.is_operator_bootstrapped,
        "mcp_servers_written": list(wrapper_result.mcp_servers_written),
        "material_paths": {key: str(value) for key, value in wrapper_result.material_paths.items()},
        "daemon_installed": daemon_installed,
        "server": server_payload,
        "openclaw": openclaw_payload,
    }


def _install_onboard_daemon(
    args: argparse.Namespace,
    *,
    config_path: Path,
    requested_port: int | None,
) -> int:
    return cmd_service_install(
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


def _print_onboard_summary(
    *,
    is_rich: bool,
    server_payload: dict[str, Any],
    openclaw_payload: dict[str, Any],
    database_repair: dict[str, Any] | None,
    wrapper_result: Any,
    daemon_installed: bool,
) -> None:
    server_target = f"{server_payload['host']}:{server_payload['port']}"
    openclaw_mode = (
        f"loopback={openclaw_payload['loopback']}, "
        f"auth={openclaw_payload['effective_auth'] or 'unknown'}"
    )
    print(heading("AutoClaw onboard", is_rich=is_rich))
    print(success("local setup complete", is_rich=is_rich))
    server_label = (
        success("free to bind", is_rich=is_rich)
        if server_payload["ok"]
        else warn("busy", is_rich=is_rich)
    )
    print(f"service port: {accent(server_target, is_rich=is_rich)} ({server_label})")
    openclaw_label = (
        success(openclaw_payload["support_status"], is_rich=is_rich)
        if openclaw_payload["support_status"] == "supported"
        else warn(openclaw_payload["support_status"], is_rich=is_rich)
    )
    print(f"openclaw: {openclaw_label} {muted(openclaw_mode, is_rich=is_rich)}")
    print(f"openclaw base url: {accent(openclaw_payload['base_url'], is_rich=is_rich)}")
    print(f"openclaw config: {accent(openclaw_payload['config_path'], is_rich=is_rich)}")
    print(
        "openclaw binary: "
        f"{accent(str(openclaw_payload['binary_path'] or 'not found'), is_rich=is_rich)}"
    )
    print(f"worker agent: {accent(wrapper_result.worker_agent_id, is_rich=is_rich)}")
    print(f"operator agent: {accent(wrapper_result.operator_agent_id, is_rich=is_rich)}")
    print(f"wrapper state: {accent(str(wrapper_result.path), is_rich=is_rich)}")
    if database_repair is not None:
        print(
            "database repair: "
            f"{warn('legacy schema backed up and reconciled', is_rich=is_rich)}"
        )
        print(f"database backup: {accent(database_repair['backup_path'], is_rich=is_rich)}")
    if daemon_installed:
        print(f"managed service: {success('installed', is_rich=is_rich)}")


async def _cmd_onboard(args: argparse.Namespace) -> int:
    if not getattr(args, "non_interactive", False):
        interactive_result = _prepare_interactive_onboard(args)
        if interactive_result is not None:
            return interactive_result

    config_path = coerce_path(args.config)
    effective_base_url = _build_effective_openclaw_base_url(args)
    preflight = _collect_onboard_preflight(
        args,
        config_path=config_path,
        openclaw_base_url=effective_base_url,
    )
    if preflight.host_state.support_status != "supported":
        return _emit_onboard_preflight_failure(
            args=args,
            created_local_config=False,
            openclaw_payload=preflight.payload,
        )

    created_local_config = await _initialize_onboard_config(args, config_path=config_path)
    requested_port = getattr(args, "port", None)
    _apply_onboard_service_overrides(
        config_path,
        requested_port=requested_port,
        gateway_port=getattr(args, "openclaw_gateway_port", None),
    )
    args.config_path = config_path
    server_payload = _load_onboard_server_payload(
        args,
        config_path=config_path,
        openclaw_base_url=effective_base_url,
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

    database_repair = await _repair_onboard_database(args)
    wrapper_result, openclaw_payload = await _reconcile_onboard_openclaw(
        args,
        config_path=config_path,
        openclaw_base_url=effective_base_url,
    )

    daemon_installed = False
    if args.install_daemon:
        install_result = _install_onboard_daemon(
            args,
            config_path=config_path,
            requested_port=requested_port,
        )
        if install_result != 0:
            return install_result
        daemon_installed = True

    payload = _build_onboard_payload(
        created_local_config=created_local_config,
        database_repair=database_repair,
        wrapper_result=wrapper_result,
        daemon_installed=daemon_installed,
        server_payload=server_payload,
        openclaw_payload=openclaw_payload,
    )
    if args.json:
        print_json(payload)
        return 0

    _print_onboard_summary(
        is_rich=rich_enabled(args),
        server_payload=server_payload,
        openclaw_payload=openclaw_payload,
        database_repair=database_repair,
        wrapper_result=wrapper_result,
        daemon_installed=daemon_installed,
    )
    return 0


__all__ = ["cmd_onboard", "cmd_service_install"]
