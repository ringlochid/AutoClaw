from __future__ import annotations

import argparse
import sys
from pathlib import Path

from autoclaw.config import load_settings
from autoclaw.interfaces.cli.commands.server_config import (
    build_server_bind_check_payload,
    emit_server_bind_check_failure,
    update_server_config_overrides,
)
from autoclaw.interfaces.cli.progress import CliProgress
from autoclaw.interfaces.cli.support import coerce_path, command_env, print_json
from autoclaw.interfaces.cli.terminal.theme import (
    accent,
    heading,
    muted,
    rich_enabled,
    success,
    warn,
)
from autoclaw.platform.managed_services import (
    ManagedServiceStatus,
    ServiceInstallRequest,
    ServiceUninstallRequest,
    get_managed_service_manager,
)
from autoclaw.platform.managed_services.systemd import (
    build_service_unit_name,
    render_systemd_service_unit,
)

DEFAULT_SERVICE_NAME = "autoclaw"
SERVICE_MANAGER = get_managed_service_manager()


def cmd_service_render(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()

    data_dir = coerce_path(args.data_dir or settings.data_dir)
    env_file = service_env_file_path(config_path, args.env_file)
    print(
        render_service_unit(
            python_bin=Path(sys.executable),
            config_path=config_path,
            data_dir=data_dir,
            env_file=env_file,
        )
    )
    return 0


def cmd_service_install(
    args: argparse.Namespace,
    *,
    progress: CliProgress | None = None,
) -> int:
    active_progress = progress or CliProgress.from_args(args)
    config_path = coerce_path(args.config)
    requested_port = getattr(args, "port", None)
    with command_env(config_path=config_path):
        initial_settings = load_settings()
    effective_port = requested_port if requested_port is not None else initial_settings.api_port
    active_progress.step(
        "server",
        f"Checking local API bind target {initial_settings.api_host}:{effective_port}",
    )
    server_payload = build_server_bind_check_payload(
        initial_settings.api_host,
        effective_port,
    )
    if not server_payload["ok"]:
        return emit_server_bind_check_failure(
            command_name="AutoClaw service install",
            args=args,
            server_payload=server_payload,
            stopped_before="stopped before managed service install",
        )
    if requested_port is not None:
        active_progress.step("config", f"Persisting service port override {requested_port}")
        update_server_config_overrides(config_path, port=requested_port)

    active_progress.step("service", "Writing managed service unit")
    SERVICE_MANAGER.install(
        ServiceInstallRequest(
            config_path=config_path,
            data_dir=coerce_path(args.data_dir or initial_settings.data_dir),
            env_file=service_env_file_path(config_path, args.env_file),
            service_name=args.name,
            unit_dir=coerce_path(args.unit_dir) if args.unit_dir is not None else None,
            should_force=args.force,
            should_skip_start=args.no_start,
            command_observer=active_progress.command_args,
        )
    )
    active_progress.done("service", "Managed service installed")
    return 0


def cmd_service_uninstall(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    SERVICE_MANAGER.uninstall(
        ServiceUninstallRequest(
            config_path=config_path,
            env_file=service_env_file_path(config_path, args.env_file),
            service_name=args.name,
            unit_dir=coerce_path(args.unit_dir) if args.unit_dir is not None else None,
            should_remove_env_file=args.remove_env_file,
        )
    )
    return 0


def cmd_service_status(args: argparse.Namespace) -> int:
    snapshot = SERVICE_MANAGER.status(args.name)
    if args.json:
        print_json(snapshot.to_payload())
    else:
        _print_service_status(snapshot, is_rich=rich_enabled(args))
    return 0


def cmd_service_start(args: argparse.Namespace) -> int:
    progress = CliProgress.from_args(args)
    return execute_service_lifecycle(args, "start", progress=progress)


def cmd_service_stop(args: argparse.Namespace) -> int:
    return execute_service_lifecycle(args, "stop", progress=CliProgress.from_args(args))


def cmd_service_restart(args: argparse.Namespace) -> int:
    progress = CliProgress.from_args(args)
    return execute_service_lifecycle(args, "restart", progress=progress)


def execute_service_lifecycle(
    args: argparse.Namespace,
    verb: str,
    *,
    progress: CliProgress,
) -> int:
    action = getattr(SERVICE_MANAGER, verb)
    progress.command_args(("systemctl", "--user", verb, build_service_unit_name(args.name)))
    snapshot = action(args.name)
    progress.done("service", f"Managed service {verb} complete")
    if args.json:
        print_json(snapshot.to_payload())
    else:
        _print_service_status(snapshot, is_rich=rich_enabled(args))
    return 0


def collect_service_status(name: str = DEFAULT_SERVICE_NAME) -> ManagedServiceStatus | None:
    try:
        return SERVICE_MANAGER.status(name)
    except RuntimeError:
        return None


def render_service_unit(
    *,
    python_bin: Path,
    config_path: Path,
    data_dir: Path,
    env_file: Path,
) -> str:
    return render_systemd_service_unit(
        python_bin=python_bin,
        config_path=config_path,
        data_dir=data_dir,
        env_file=env_file,
    )


def service_env_file_path(config_path: Path, explicit_env_file: str | None) -> Path:
    if explicit_env_file is not None:
        return coerce_path(explicit_env_file)
    return config_path.parent / "autoclaw.env"


def _print_service_status(snapshot: ManagedServiceStatus, *, is_rich: bool) -> None:
    installed = "installed" if snapshot.is_installed else "not installed"
    running = "running" if snapshot.is_running else "stopped"
    running_label = (
        success(running, is_rich=is_rich) if snapshot.is_running else warn(running, is_rich=is_rich)
    )
    print(heading("AutoClaw service", is_rich=is_rich))
    print(f"status: {running_label} ({muted(installed, is_rich=is_rich)})")
    print(f"manager: {snapshot.manager}")
    print(f"unit: {accent(snapshot.service_name, is_rich=is_rich)}")
    print(f"enabled: {snapshot.is_enabled}")
    if snapshot.fragment_path:
        print(f"fragment: {accent(snapshot.fragment_path, is_rich=is_rich)}")
    if snapshot.active_state is not None:
        print(f"active state: {snapshot.active_state}")
    if snapshot.sub_state is not None:
        print(f"sub state: {snapshot.sub_state}")


__all__ = [
    "DEFAULT_SERVICE_NAME",
    "cmd_service_install",
    "cmd_service_render",
    "cmd_service_restart",
    "cmd_service_start",
    "cmd_service_status",
    "cmd_service_stop",
    "cmd_service_uninstall",
    "collect_service_status",
    "render_service_unit",
    "service_env_file_path",
]
