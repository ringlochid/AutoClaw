from __future__ import annotations

import argparse
import asyncio

from app.cli_commands.bootstrap import (
    cmd_db_reset,
    cmd_db_upgrade,
    cmd_init,
    cmd_serve,
    settings_to_config_text,
)
from app.cli_commands.definitions import cmd_definitions_import
from app.cli_commands.openclaw_wrapper import (
    cmd_openclaw_check,
    cmd_openclaw_doctor,
    cmd_openclaw_setup,
)
from app.cli_commands.operator import (
    cmd_config_path,
    cmd_config_show,
    cmd_configure,
    cmd_doctor,
    cmd_onboard,
)
from app.cli_commands.service import (
    DEFAULT_SERVICE_NAME,
    cmd_service_install,
    cmd_service_render,
    cmd_service_restart,
    cmd_service_start,
    cmd_service_status,
    cmd_service_stop,
    cmd_service_uninstall,
    render_service_unit,
)
from app.cli_commands.task_compose import cmd_task_compose_start
from app.cli_support import command_env, print_json
from app.config import DEFAULT_LOG_LEVEL
from app.paths import default_config_path


def _add_common_output_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--no-color", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoclaw")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--config", default=str(default_config_path()))
    init_parser.add_argument("--data-dir")
    init_parser.add_argument("--database-url")
    init_parser.add_argument("--host", default="127.0.0.1")
    init_parser.add_argument("--port", type=int, default=8123)
    init_parser.add_argument("--log-level", default=DEFAULT_LOG_LEVEL)
    init_parser.add_argument("--api-key")
    init_parser.add_argument("--internal-api-key")
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--skip-db-upgrade", action="store_true")
    init_parser.add_argument("--json", action="store_true")
    init_parser.set_defaults(handler=_cmd_init)

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--config", default=str(default_config_path()))
    serve_parser.set_defaults(handler=_cmd_serve)

    onboard_parser = subparsers.add_parser("onboard")
    onboard_parser.add_argument("--config", default=str(default_config_path()))
    onboard_parser.add_argument("--data-dir")
    onboard_parser.add_argument("--database-url")
    onboard_parser.add_argument("--host", default="127.0.0.1")
    onboard_parser.add_argument("--port", type=int, default=8123)
    onboard_parser.add_argument("--log-level", default=DEFAULT_LOG_LEVEL)
    onboard_parser.add_argument("--api-key")
    onboard_parser.add_argument("--internal-api-key")
    onboard_parser.add_argument("--force", action="store_true")
    onboard_parser.add_argument("--skip-db-upgrade", action="store_true")
    onboard_parser.add_argument("--install-daemon", action="store_true")
    onboard_parser.add_argument("--skip-daemon", action="store_true")
    onboard_parser.add_argument("--no-start", action="store_true")
    onboard_parser.add_argument("--non-interactive", action="store_true")
    onboard_parser.add_argument("--openclaw-gateway-token")
    onboard_parser.add_argument("--openclaw-gateway-port", type=int)
    _add_common_output_flags(onboard_parser)
    onboard_parser.set_defaults(handler=cmd_onboard)

    configure_parser = subparsers.add_parser("configure")
    configure_parser.add_argument("--config", default=str(default_config_path()))
    configure_parser.add_argument(
        "--section",
        choices=["all", "local", "openclaw", "service", "runtime", "definitions", "web"],
        default="all",
    )
    configure_parser.add_argument("--force", action="store_true")
    configure_parser.add_argument("--no-start", action="store_true")
    configure_parser.add_argument("--non-interactive", action="store_true")
    configure_parser.add_argument("--openclaw-gateway-token")
    configure_parser.add_argument("--openclaw-gateway-port", type=int)
    _add_common_output_flags(configure_parser)
    configure_parser.set_defaults(handler=cmd_configure)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--config", default=str(default_config_path()))
    doctor_parser.add_argument("--fix", action="store_true")
    _add_common_output_flags(doctor_parser)
    doctor_parser.set_defaults(handler=cmd_doctor)

    config_parser = subparsers.add_parser("config")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    config_path_parser = config_subparsers.add_parser("path")
    config_path_parser.add_argument("--config", default=str(default_config_path()))
    config_path_parser.add_argument("--json", action="store_true")
    config_path_parser.set_defaults(handler=cmd_config_path)
    config_show_parser = config_subparsers.add_parser("show")
    config_show_parser.add_argument("--config", default=str(default_config_path()))
    config_show_parser.add_argument("--json", action="store_true")
    config_show_parser.set_defaults(handler=cmd_config_show)

    db_parser = subparsers.add_parser("db")
    db_subparsers = db_parser.add_subparsers(dest="db_command", required=True)
    db_upgrade_parser = db_subparsers.add_parser("upgrade")
    db_upgrade_parser.add_argument("--config", default=str(default_config_path()))
    db_upgrade_parser.add_argument("--revision", default="head")
    db_upgrade_parser.set_defaults(handler=_cmd_db_upgrade)
    db_reset_parser = db_subparsers.add_parser("reset")
    db_reset_parser.add_argument("--config", default=str(default_config_path()))
    db_reset_parser.add_argument("--revision", default="head")
    db_reset_parser.add_argument("--json", action="store_true")
    db_reset_parser.set_defaults(handler=_cmd_db_reset)

    definitions_parser = subparsers.add_parser("definitions")
    definitions_subparsers = definitions_parser.add_subparsers(
        dest="definitions_command",
        required=True,
    )
    definitions_import_parser = definitions_subparsers.add_parser("import")
    definitions_import_parser.add_argument("--config", default=str(default_config_path()))
    definitions_import_parser.add_argument("--file")
    definitions_import_parser.add_argument(
        "--overwrite",
        choices=["reject", "allow_new_revision"],
        default="reject",
    )
    definitions_import_parser.add_argument("--json", action="store_true")
    definitions_import_parser.set_defaults(handler=cmd_definitions_import)

    task_compose_parser = subparsers.add_parser("task-compose")
    task_compose_subparsers = task_compose_parser.add_subparsers(
        dest="task_compose_command",
        required=True,
    )
    task_compose_start_parser = task_compose_subparsers.add_parser("start")
    task_compose_start_parser.add_argument("--config", default=str(default_config_path()))
    task_compose_start_parser.add_argument("--file", required=True)
    task_compose_start_parser.add_argument("--json", action="store_true")
    task_compose_start_parser.set_defaults(handler=cmd_task_compose_start)

    openclaw_parser = subparsers.add_parser("openclaw")
    openclaw_subparsers = openclaw_parser.add_subparsers(
        dest="openclaw_command",
        required=True,
    )
    openclaw_check_parser = openclaw_subparsers.add_parser("check")
    openclaw_check_parser.add_argument("--config", default=str(default_config_path()))
    _add_common_output_flags(openclaw_check_parser)
    openclaw_check_parser.set_defaults(handler=cmd_openclaw_check)
    openclaw_setup_parser = openclaw_subparsers.add_parser("setup")
    openclaw_setup_parser.add_argument("--config", default=str(default_config_path()))
    openclaw_setup_parser.add_argument("--non-interactive", action="store_true")
    openclaw_setup_parser.add_argument("--openclaw-gateway-token")
    openclaw_setup_parser.add_argument("--openclaw-gateway-port", type=int)
    _add_common_output_flags(openclaw_setup_parser)
    openclaw_setup_parser.set_defaults(handler=cmd_openclaw_setup)
    openclaw_doctor_parser = openclaw_subparsers.add_parser("doctor")
    openclaw_doctor_parser.add_argument("--config", default=str(default_config_path()))
    openclaw_doctor_parser.add_argument("--fix", action="store_true")
    openclaw_doctor_parser.add_argument("--openclaw-gateway-token")
    openclaw_doctor_parser.add_argument("--openclaw-gateway-port", type=int)
    _add_common_output_flags(openclaw_doctor_parser)
    openclaw_doctor_parser.set_defaults(handler=cmd_openclaw_doctor)

    service_parser = subparsers.add_parser("service")
    service_subparsers = service_parser.add_subparsers(dest="service_command", required=True)

    service_render_parser = service_subparsers.add_parser("render")
    service_render_parser.add_argument("--config", default=str(default_config_path()))
    service_render_parser.add_argument("--data-dir")
    service_render_parser.add_argument("--env-file")
    service_render_parser.add_argument("--name", default=DEFAULT_SERVICE_NAME)
    service_render_parser.set_defaults(handler=cmd_service_render)

    service_install_parser = service_subparsers.add_parser("install")
    service_install_parser.add_argument("--config", default=str(default_config_path()))
    service_install_parser.add_argument("--data-dir")
    service_install_parser.add_argument("--env-file")
    service_install_parser.add_argument("--name", default=DEFAULT_SERVICE_NAME)
    service_install_parser.add_argument("--unit-dir")
    service_install_parser.add_argument("--force", action="store_true")
    service_install_parser.add_argument("--no-start", action="store_true")
    service_install_parser.set_defaults(handler=cmd_service_install)

    service_uninstall_parser = service_subparsers.add_parser("uninstall")
    service_uninstall_parser.add_argument("--config", default=str(default_config_path()))
    service_uninstall_parser.add_argument("--env-file")
    service_uninstall_parser.add_argument("--name", default=DEFAULT_SERVICE_NAME)
    service_uninstall_parser.add_argument("--unit-dir")
    service_uninstall_parser.add_argument("--remove-env-file", action="store_true")
    service_uninstall_parser.set_defaults(handler=cmd_service_uninstall)

    service_start_parser = service_subparsers.add_parser("start")
    service_start_parser.add_argument("--config", default=str(default_config_path()))
    service_start_parser.add_argument("--name", default=DEFAULT_SERVICE_NAME)
    service_start_parser.add_argument("--json", action="store_true")
    service_start_parser.set_defaults(handler=cmd_service_start)

    service_stop_parser = service_subparsers.add_parser("stop")
    service_stop_parser.add_argument("--config", default=str(default_config_path()))
    service_stop_parser.add_argument("--name", default=DEFAULT_SERVICE_NAME)
    service_stop_parser.add_argument("--json", action="store_true")
    service_stop_parser.set_defaults(handler=cmd_service_stop)

    service_restart_parser = service_subparsers.add_parser("restart")
    service_restart_parser.add_argument("--config", default=str(default_config_path()))
    service_restart_parser.add_argument("--name", default=DEFAULT_SERVICE_NAME)
    service_restart_parser.add_argument("--json", action="store_true")
    service_restart_parser.set_defaults(handler=cmd_service_restart)

    service_status_parser = service_subparsers.add_parser("status")
    service_status_parser.add_argument("--config", default=str(default_config_path()))
    service_status_parser.add_argument("--name", default=DEFAULT_SERVICE_NAME)
    service_status_parser.add_argument("--json", action="store_true")
    service_status_parser.set_defaults(handler=cmd_service_status)

    return parser


_cmd_init = cmd_init
_cmd_serve = cmd_serve
_cmd_db_upgrade = cmd_db_upgrade
_cmd_db_reset = cmd_db_reset
_cmd_service_render = cmd_service_render
_cmd_service_install = cmd_service_install
_cmd_service_uninstall = cmd_service_uninstall
_cmd_service_start = cmd_service_start
_cmd_service_stop = cmd_service_stop
_cmd_service_restart = cmd_service_restart
_cmd_service_status = cmd_service_status
_render_service_unit = render_service_unit
_settings_to_config_text = settings_to_config_text
_command_env = command_env
_print_json = print_json


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.handler(args)
    if asyncio.iscoroutine(result):
        return int(asyncio.run(result))
    return int(result)
