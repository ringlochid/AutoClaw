from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.cli_support import coerce_path, command_env, print_json
from app.config import load_settings
from app.service_managers import (
    ManagedServiceStatus,
    ServiceInstallRequest,
    ServiceUninstallRequest,
    get_managed_service_manager,
)
from app.service_managers.systemd import render_systemd_service_unit
from app.terminal.theme import accent, heading, muted, rich_enabled, success, warn

DEFAULT_SERVICE_NAME = "autoclaw"
SERVICE_MANAGER = get_managed_service_manager()


def service_env_file_path(config_path: Path, explicit_env_file: str | None) -> Path:
    if explicit_env_file is not None:
        return coerce_path(explicit_env_file)
    return config_path.parent / "autoclaw.env"


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


def cmd_service_install(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()

    SERVICE_MANAGER.install(
        ServiceInstallRequest(
            config_path=config_path,
            data_dir=coerce_path(args.data_dir or settings.data_dir),
            env_file=service_env_file_path(config_path, args.env_file),
            service_name=args.name,
            unit_dir=coerce_path(args.unit_dir) if args.unit_dir is not None else None,
            force=args.force,
            no_start=args.no_start,
        )
    )
    return 0


def cmd_service_uninstall(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    SERVICE_MANAGER.uninstall(
        ServiceUninstallRequest(
            config_path=config_path,
            env_file=service_env_file_path(config_path, args.env_file),
            service_name=args.name,
            unit_dir=coerce_path(args.unit_dir) if args.unit_dir is not None else None,
            remove_env_file=args.remove_env_file,
        )
    )
    return 0


def _print_service_status(snapshot: ManagedServiceStatus, *, rich: bool) -> None:
    installed = "installed" if snapshot.installed else "not installed"
    running = "running" if snapshot.running else "stopped"
    running_label = success(running, rich=rich) if snapshot.running else warn(running, rich=rich)
    print(heading("AutoClaw service", rich=rich))
    print(f"status: {running_label} ({muted(installed, rich=rich)})")
    print(f"manager: {snapshot.manager}")
    print(f"unit: {accent(snapshot.service_name, rich=rich)}")
    print(f"enabled: {snapshot.enabled}")
    if snapshot.fragment_path:
        print(f"fragment: {accent(snapshot.fragment_path, rich=rich)}")
    if snapshot.active_state is not None:
        print(f"active state: {snapshot.active_state}")
    if snapshot.sub_state is not None:
        print(f"sub state: {snapshot.sub_state}")


def cmd_service_status(args: argparse.Namespace) -> int:
    snapshot = SERVICE_MANAGER.status(args.name)
    if args.json:
        print_json(snapshot.to_payload())
    else:
        _print_service_status(snapshot, rich=rich_enabled(args))
    return 0


def _systemd_lifecycle(args: argparse.Namespace, verb: str) -> int:
    action = getattr(SERVICE_MANAGER, verb)
    snapshot = action(args.name)
    if args.json:
        print_json(snapshot.to_payload())
    else:
        _print_service_status(snapshot, rich=rich_enabled(args))
    return 0


def cmd_service_start(args: argparse.Namespace) -> int:
    return _systemd_lifecycle(args, "start")


def cmd_service_stop(args: argparse.Namespace) -> int:
    return _systemd_lifecycle(args, "stop")


def cmd_service_restart(args: argparse.Namespace) -> int:
    return _systemd_lifecycle(args, "restart")


def collect_service_status(name: str = DEFAULT_SERVICE_NAME) -> ManagedServiceStatus | None:
    try:
        return SERVICE_MANAGER.status(name)
    except RuntimeError:
        return None


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
