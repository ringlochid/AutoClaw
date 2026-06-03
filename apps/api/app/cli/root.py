from __future__ import annotations

from typing import Any

import click

from app.cli.commands.bootstrap import cmd_db_reset, cmd_db_upgrade, cmd_init, cmd_serve
from app.cli.commands.config_view import cmd_config_path, cmd_config_show
from app.cli.commands.configure import cmd_configure
from app.cli.commands.definitions import cmd_definitions_import
from app.cli.commands.doctor import cmd_doctor
from app.cli.commands.onboard import cmd_onboard
from app.cli.commands.openclaw.wrapper import (
    cmd_openclaw_check,
    cmd_openclaw_doctor,
    cmd_openclaw_setup,
)
from app.cli.commands.service import (
    DEFAULT_SERVICE_NAME,
    cmd_service_install,
    cmd_service_render,
    cmd_service_restart,
    cmd_service_start,
    cmd_service_status,
    cmd_service_stop,
    cmd_service_uninstall,
)
from app.cli.commands.task_compose import cmd_task_compose_start
from app.config import DEFAULT_API_PORT, DEFAULT_LOG_LEVEL

from .context import CliContext
from .help import ROOT_HELP_EPILOG
from .root_support import (
    build_argument_namespace,
    config_option,
    invoke_handler_result,
    output_options,
    package_version,
)


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog=ROOT_HELP_EPILOG,
    help="AutoClaw local-first workflow control plane.",
)
@click.option(
    "--debug",
    "is_debug",
    is_flag=True,
    help="Include a traceback when a command fails.",
)
@click.version_option(package_version(), "--version", "-V")
@click.pass_context
def cli(ctx: click.Context, is_debug: bool) -> None:
    runtime = ctx.obj if isinstance(ctx.obj, CliContext) else CliContext()
    ctx.obj = runtime.overlay(is_debug=runtime.is_debug or is_debug)


@cli.command("init")
@config_option
@click.option("--data-dir")
@click.option("--database-url")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=DEFAULT_API_PORT, type=int, show_default=True)
@click.option("--log-level", default=DEFAULT_LOG_LEVEL, show_default=True)
@click.option("--api-key")
@click.option("--internal-api-key")
@click.option("--force", is_flag=True)
@click.option("--skip-db-upgrade", is_flag=True)
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def init_command(**kwargs: Any) -> int:
    return invoke_handler_result(
        cmd_init(build_argument_namespace(**kwargs, json=kwargs["is_json_output"]))
    )


@cli.command("serve")
@config_option
def serve_command(config: str) -> int:
    return invoke_handler_result(cmd_serve(build_argument_namespace(config=config)))


@cli.command("onboard")
@config_option
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
@output_options
def onboard_command(**kwargs: Any) -> int:
    return invoke_handler_result(
        cmd_onboard(build_argument_namespace(**kwargs, json=kwargs["json_output"]))
    )


@cli.command("configure")
@config_option
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
@output_options
def configure_command(**kwargs: Any) -> int:
    return invoke_handler_result(
        cmd_configure(build_argument_namespace(**kwargs, json=kwargs["json_output"]))
    )


@cli.command("doctor")
@config_option
@click.option("--fix", is_flag=True)
@output_options
def doctor_command(**kwargs: Any) -> int:
    return invoke_handler_result(
        cmd_doctor(build_argument_namespace(**kwargs, json=kwargs["json_output"]))
    )


@cli.group("config")
def config_group() -> None:
    return None


@config_group.command("path")
@config_option
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def config_path_command(config: str, is_json_output: bool) -> int:
    return invoke_handler_result(
        cmd_config_path(build_argument_namespace(config=config, json=is_json_output))
    )


@config_group.command("show")
@config_option
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def config_show_command(config: str, is_json_output: bool) -> int:
    return invoke_handler_result(
        cmd_config_show(build_argument_namespace(config=config, json=is_json_output))
    )


@cli.group("db")
def db_group() -> None:
    return None


@db_group.command("upgrade")
@config_option
@click.option("--revision", default="head", show_default=True)
def db_upgrade_command(config: str, revision: str) -> int:
    return invoke_handler_result(
        cmd_db_upgrade(build_argument_namespace(config=config, revision=revision))
    )


@db_group.command("reset")
@config_option
@click.option("--revision", default="head", show_default=True)
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def db_reset_command(config: str, revision: str, is_json_output: bool) -> int:
    return invoke_handler_result(
        cmd_db_reset(
            build_argument_namespace(config=config, revision=revision, json=is_json_output)
        )
    )


@cli.group("definitions")
def definitions_group() -> None:
    return None


@definitions_group.command("import")
@config_option
@click.option("--file", "file_path")
@click.option(
    "--overwrite",
    type=click.Choice(["reject", "allow_new_revision"]),
    default="reject",
    show_default=True,
)
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def definitions_import_command(
    config: str,
    file_path: str | None,
    overwrite: str,
    is_json_output: bool,
) -> int:
    return invoke_handler_result(
        cmd_definitions_import(
            build_argument_namespace(
                config=config,
                file=file_path,
                overwrite=overwrite,
                json=is_json_output,
            )
        )
    )


@cli.group("task-compose")
def task_compose_group() -> None:
    return None


@task_compose_group.command("start")
@config_option
@click.option("--file", "file_path", required=True)
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def task_compose_start_command(config: str, file_path: str, is_json_output: bool) -> int:
    return invoke_handler_result(
        cmd_task_compose_start(
            build_argument_namespace(config=config, file=file_path, json=is_json_output)
        )
    )


@cli.group("openclaw")
def openclaw_group() -> None:
    return None


@openclaw_group.command("check")
@config_option
@output_options
def openclaw_check_command(**kwargs: Any) -> int:
    return invoke_handler_result(
        cmd_openclaw_check(build_argument_namespace(**kwargs, json=kwargs["json_output"]))
    )


@openclaw_group.command("setup")
@config_option
@click.option("--non-interactive", is_flag=True)
@click.option("--openclaw-gateway-token")
@click.option("--openclaw-gateway-port", type=int)
@output_options
def openclaw_setup_command(**kwargs: Any) -> int:
    return invoke_handler_result(
        cmd_openclaw_setup(build_argument_namespace(**kwargs, json=kwargs["json_output"]))
    )


@openclaw_group.command("doctor")
@config_option
@click.option("--fix", is_flag=True)
@click.option("--openclaw-gateway-token")
@click.option("--openclaw-gateway-port", type=int)
@output_options
def openclaw_doctor_command(**kwargs: Any) -> int:
    return invoke_handler_result(
        cmd_openclaw_doctor(build_argument_namespace(**kwargs, json=kwargs["json_output"]))
    )


@cli.group("service")
def service_group() -> None:
    return None


@service_group.command("render")
@config_option
@click.option("--data-dir")
@click.option("--env-file")
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
def service_render_command(**kwargs: Any) -> int:
    return invoke_handler_result(cmd_service_render(build_argument_namespace(**kwargs)))


@service_group.command("install")
@config_option
@click.option("--data-dir")
@click.option("--env-file")
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--unit-dir")
@click.option("--port", type=int)
@click.option("--force", is_flag=True)
@click.option("--no-start", is_flag=True)
def service_install_command(**kwargs: Any) -> int:
    return invoke_handler_result(cmd_service_install(build_argument_namespace(**kwargs)))


@service_group.command("uninstall")
@config_option
@click.option("--env-file")
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--unit-dir")
@click.option("--remove-env-file", is_flag=True)
def service_uninstall_command(**kwargs: Any) -> int:
    return invoke_handler_result(cmd_service_uninstall(build_argument_namespace(**kwargs)))


@service_group.command("start")
@config_option
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def service_start_command(config: str, name: str, is_json_output: bool) -> int:
    return invoke_handler_result(
        cmd_service_start(build_argument_namespace(config=config, name=name, json=is_json_output))
    )


@service_group.command("stop")
@config_option
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def service_stop_command(config: str, name: str, is_json_output: bool) -> int:
    return invoke_handler_result(
        cmd_service_stop(build_argument_namespace(config=config, name=name, json=is_json_output))
    )


@service_group.command("restart")
@config_option
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def service_restart_command(config: str, name: str, is_json_output: bool) -> int:
    return invoke_handler_result(
        cmd_service_restart(build_argument_namespace(config=config, name=name, json=is_json_output))
    )


@service_group.command("status")
@config_option
@click.option("--name", default=DEFAULT_SERVICE_NAME, show_default=True)
@click.option("--json", "is_json_output", is_flag=True, help="Emit JSON output only.")
def service_status_command(config: str, name: str, is_json_output: bool) -> int:
    return invoke_handler_result(
        cmd_service_status(build_argument_namespace(config=config, name=name, json=is_json_output))
    )
