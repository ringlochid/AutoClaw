from __future__ import annotations

from autoclaw.cli.commands.bootstrap import (
    cmd_db_reset,
    cmd_db_upgrade,
    cmd_init,
    cmd_serve,
    settings_to_config_text,
)
from autoclaw.cli.commands.config_view import (
    cmd_config_path,
    cmd_config_show,
)
from autoclaw.cli.commands.configure import cmd_configure
from autoclaw.cli.commands.definitions import cmd_definitions_import
from autoclaw.cli.commands.doctor import cmd_doctor
from autoclaw.cli.commands.onboard import cmd_onboard
from autoclaw.cli.commands.openclaw.wrapper import (
    cmd_openclaw_check,
    cmd_openclaw_doctor,
    cmd_openclaw_setup,
)
from autoclaw.cli.commands.service import (
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
from autoclaw.cli.commands.task_compose import cmd_task_compose_start
from autoclaw.cli.support import command_env, print_json

from .main import build_parser, main

__all__ = [
    "DEFAULT_SERVICE_NAME",
    "build_parser",
    "cmd_config_path",
    "cmd_config_show",
    "cmd_configure",
    "cmd_db_reset",
    "cmd_db_upgrade",
    "cmd_definitions_import",
    "cmd_doctor",
    "cmd_init",
    "cmd_onboard",
    "cmd_openclaw_check",
    "cmd_openclaw_doctor",
    "cmd_openclaw_setup",
    "cmd_serve",
    "cmd_service_install",
    "cmd_service_render",
    "cmd_service_restart",
    "cmd_service_start",
    "cmd_service_status",
    "cmd_service_stop",
    "cmd_service_uninstall",
    "cmd_task_compose_start",
    "command_env",
    "main",
    "print_json",
    "render_service_unit",
    "settings_to_config_text",
]
