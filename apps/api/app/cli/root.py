from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from typing import Any, ParamSpec, TypeVar

import click

from app.cli_commands.bootstrap import cmd_db_reset, cmd_db_upgrade, cmd_init, cmd_serve
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
)
from app.cli_commands.task_compose import cmd_task_compose_start
from app.config import DEFAULT_LOG_LEVEL
from app.paths import default_config_path

from .context import CliContext
from .help import ROOT_HELP_EPILOG

P = ParamSpec("P")
T = TypeVar("T")


def _package_version() -> str:
    try:
        return version("autoclaw")
    except PackageNotFoundError:
        return "0.1.1"


def _default_config_text() -> str:
    return str(default_config_path())


def _invoke_handler(result: int | Any) -> int:
    if asyncio.iscoroutine(result):
        return int(asyncio.run(result))
    return int(result)


def _namespace(**kwargs: Any) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def _output_options(function: Callable[P, T]) -> Callable[P, T]:
    function = click.option(
        "--no-color",
        is_flag=True,
        help="Disable ANSI color output.",
    )(function)
    function = click.option("--plain", is_flag=True, help="Disable rich styling.")(function)
    function = click.option(
        "--json",
        "json_output",
        is_flag=True,
        help="Emit JSON output only.",
    )(function)
    return function


def _config_option(function: Callable[P, T]) -> Callable[P, T]:
    return click.option("--config", default=_default_config_text, show_default=True)(function)


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog=ROOT_HELP_EPILOG,
    help="AutoClaw local-first workflow control plane.",
)
@click.option("--debug", is_flag=True, help="Include a traceback when a command fails.")
@click.version_option(_package_version(), "--version", "-V")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    runtime = ctx.obj if isinstance(ctx.obj, CliContext) else CliContext()
    ctx.obj = runtime.overlay(debug=runtime.debug or debug)


@cli.command("init")
@_config_option
@click.option("--data-dir")
@click.option("--database-url")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8123, type=int, show_default=True)
@click.option("--log-level", default=DEFAULT_LOG_LEVEL, show_default=True)
@click.option("--api-key")
@click.option("--internal-api-key")
@click.option("--force", is_flag=True)
@click.option("--skip-db-upgrade", is_flag=True)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def init_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_init(_namespace(**kwargs, json=kwargs["json_output"])))


@cli.command("serve")
@_config_option
def serve_command(config: str) -> int:
    return _invoke_handler(cmd_serve(_namespace(config=config)))


@cli.command("onboard")
@_config_option
@click.option("--data-dir")
@click.option("--database-url")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", type=int)
@click.option("--log-level", default=DEFAULT_LOG_LEVEL, show_default=True)
@click.option("--api-key")
@click.option("--internal-api-key")
@click.option("--force", is_flag=True)
@click.option("--skip-db-upgrade", is_flag=True)
@click.option("--install-daemon", is_flag=True)
@click.option("--skip-daemon", is_flag=True)
@click.option("--no-start", is_flag=True)
@click.option("--non-interactive", is_flag=True)
@click.option("--openclaw-gateway-token")
@click.option("--openclaw-gateway-port", type=int)
@_output_options
def onboard_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_onboard(_namespace(**kwargs, json=kwargs["json_output"])))


@cli.command("configure")
@_config_option
@click.option(
    "--section",
    type=click.Choice(["all", "local", "openclaw", "service", "runtime", "definitions", "web"]),
    default="all",
    show_default=True,
)
@click.option("--port", type=int)
@click.option("--force", is_flag=True)
@click.option("--no-start", is_flag=True)
@click.option("--non-interactive", is_flag=True)
@click.option("--openclaw-gateway-token")
@click.option("--openclaw-gateway-port", type=int)
@_output_options
def configure_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_configure(_namespace(**kwargs, json=kwargs["json_output"])))


@cli.command("doctor")
@_config_option
@click.option("--fix", is_flag=True)
@_output_options
def doctor_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_doctor(_namespace(**kwargs, json=kwargs["json_output"])))


@cli.group("config")
def config_group() -> None:
    return None


@config_group.command("path")
@_config_option
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def config_path_command(config: str, json_output: bool) -> int:
    return _invoke_handler(cmd_config_path(_namespace(config=config, json=json_output)))


@config_group.command("show")
@_config_option
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def config_show_command(config: str, json_output: bool) -> int:
    return _invoke_handler(cmd_config_show(_namespace(config=config, json=json_output)))


@cli.group("db")
def db_group() -> None:
    return None


@db_group.command("upgrade")
@_config_option
@click.option("--revision", default="head", show_default=True)
def db_upgrade_command(config: str, revision: str) -> int:
    return _invoke_handler(cmd_db_upgrade(_namespace(config=config, revision=revision)))


@db_group.command("reset")
@_config_option
@click.option("--revision", default="head", show_default=True)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def db_reset_command(config: str, revision: str, json_output: bool) -> int:
    return _invoke_handler(
        cmd_db_reset(_namespace(config=config, revision=revision, json=json_output))
    )


@cli.group("definitions")
def definitions_group() -> None:
    return None


@definitions_group.command("import")
@_config_option
@click.option("--file", "file_path")
@click.option(
    "--overwrite",
    type=click.Choice(["reject", "allow_new_revision"]),
    default="reject",
    show_default=True,
)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def definitions_import_command(
    config: str,
    file_path: str | None,
    overwrite: str,
    json_output: bool,
) -> int:
    return _invoke_handler(
        cmd_definitions_import(
            _namespace(
                config=config,
                file=file_path,
                overwrite=overwrite,
                json=json_output,
            )
        )
    )


@cli.group("task-compose")
def task_compose_group() -> None:
    return None


@task_compose_group.command("start")
@_config_option
@click.option("--file", "file_path", required=True)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def task_compose_start_command(config: str, file_path: str, json_output: bool) -> int:
    return _invoke_handler(
        cmd_task_compose_start(_namespace(config=config, file=file_path, json=json_output))
    )


@cli.group("openclaw")
def openclaw_group() -> None:
    return None


@openclaw_group.command("check")
@_config_option
@_output_options
def openclaw_check_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_openclaw_check(_namespace(**kwargs, json=kwargs["json_output"])))


@openclaw_group.command("setup")
@_config_option
@click.option("--non-interactive", is_flag=True)
@click.option("--openclaw-gateway-token")
@click.option("--openclaw-gateway-port", type=int)
@_output_options
def openclaw_setup_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_openclaw_setup(_namespace(**kwargs, json=kwargs["json_output"])))


@openclaw_group.command("doctor")
@_config_option
@click.option("--fix", is_flag=True)
@click.option("--openclaw-gateway-token")
@click.option("--openclaw-gateway-port", type=int)
@_output_options
def openclaw_doctor_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_openclaw_doctor(_namespace(**kwargs, json=kwargs["json_output"])))


@cli.group("service")
def service_group() -> None:
    return None


@service_group.command("render")
@_config_option
@click.option("--data-dir")
@click.option("--env-file")
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
def service_render_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_service_render(_namespace(**kwargs)))


@service_group.command("install")
@_config_option
@click.option("--data-dir")
@click.option("--env-file")
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--unit-dir")
@click.option("--port", type=int)
@click.option("--force", is_flag=True)
@click.option("--no-start", is_flag=True)
def service_install_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_service_install(_namespace(**kwargs)))


@service_group.command("uninstall")
@_config_option
@click.option("--env-file")
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--unit-dir")
@click.option("--remove-env-file", is_flag=True)
def service_uninstall_command(**kwargs: Any) -> int:
    return _invoke_handler(cmd_service_uninstall(_namespace(**kwargs)))


@service_group.command("start")
@_config_option
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def service_start_command(config: str, name: str, json_output: bool) -> int:
    return _invoke_handler(
        cmd_service_start(_namespace(config=config, name=name, json=json_output))
    )


@service_group.command("stop")
@_config_option
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def service_stop_command(config: str, name: str, json_output: bool) -> int:
    return _invoke_handler(cmd_service_stop(_namespace(config=config, name=name, json=json_output)))


@service_group.command("restart")
@_config_option
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def service_restart_command(config: str, name: str, json_output: bool) -> int:
    return _invoke_handler(
        cmd_service_restart(_namespace(config=config, name=name, json=json_output))
    )


@service_group.command("status")
@_config_option
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output only.")
def service_status_command(config: str, name: str, json_output: bool) -> int:
    return _invoke_handler(
        cmd_service_status(_namespace(config=config, name=name, json=json_output))
    )
