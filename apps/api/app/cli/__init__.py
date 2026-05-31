from __future__ import annotations

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

from .main import build_parser, main

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

__all__ = [
    "DEFAULT_SERVICE_NAME",
    "_cmd_db_reset",
    "_cmd_db_upgrade",
    "_cmd_init",
    "_cmd_serve",
    "_cmd_service_install",
    "_cmd_service_render",
    "_cmd_service_restart",
    "_cmd_service_start",
    "_cmd_service_status",
    "_cmd_service_stop",
    "_cmd_service_uninstall",
    "_command_env",
    "_print_json",
    "_render_service_unit",
    "_settings_to_config_text",
    "build_parser",
    "cmd_config_path",
    "cmd_config_show",
    "cmd_configure",
    "cmd_definitions_import",
    "cmd_doctor",
    "cmd_onboard",
    "cmd_openclaw_check",
    "cmd_openclaw_doctor",
    "cmd_openclaw_setup",
    "cmd_task_compose_start",
    "main",
]
