from __future__ import annotations

import argparse
from pathlib import Path

from autoclaw.config import load_settings
from autoclaw.interfaces.cli.commands.bootstrap import (
    ensure_database_ready_with_legacy_sqlite_repair,
    update_config_sections,
)
from autoclaw.interfaces.cli.commands.openclaw.support import (
    collect_openclaw_preflight,
    emit_openclaw_preflight_failure,
)
from autoclaw.interfaces.cli.commands.openclaw.wrapper import (
    bootstrap_openclaw_gateway_access,
    reconcile_openclaw_setup,
)
from autoclaw.interfaces.cli.commands.server_config import (
    build_server_bind_check_payload,
    emit_server_bind_check_failure,
)
from autoclaw.interfaces.cli.commands.service import DEFAULT_SERVICE_NAME, cmd_service_install
from autoclaw.interfaces.cli.progress import CliProgress
from autoclaw.interfaces.cli.support import coerce_path, command_env, print_json
from autoclaw.interfaces.cli.terminal.note import note
from autoclaw.interfaces.cli.terminal.prompts import PromptUnavailableError, SelectOption, select
from autoclaw.interfaces.cli.terminal.theme import accent, heading, rich_enabled, warn

DEFAULT_WEB_CONSOLE_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
)


async def cmd_configure(args: argparse.Namespace) -> int:
    if not getattr(args, "non_interactive", False):
        try:
            args.section = _select_configure_section(args)
        except PromptUnavailableError as exc:
            return _emit_prompt_unavailable_exit("AutoClaw configure", exc)

    config_path = coerce_path(args.config)
    progress = CliProgress.from_args(args)
    section = args.section
    actions: list[str] = []

    if section in {"all", "openclaw", "service"}:
        validation_result = _validate_openclaw_configure_section(
            args,
            config_path=config_path,
            section=section,
            actions=actions,
            progress=progress,
        )
        if validation_result is not None:
            return validation_result

    if section in {"all", "local", "runtime", "definitions"}:
        await _repair_database_section(config_path, progress=progress)
    if section in {"all", "local", "runtime"}:
        actions.append("local_runtime")
    if section in {"all", "definitions"}:
        actions.append("definitions_registry")
    if section in {"all", "web"}:
        progress.step("config", "Refreshing web console origin allowlist")
        update_config_sections(
            config_path,
            section_updates={"server": {"console_origins": list(DEFAULT_WEB_CONSOLE_ORIGINS)}},
        )
        progress.done("config", "Web console origins refreshed")
        actions.append("web_console")
    if section in {"all", "openclaw"}:
        progress.step("openclaw", "Reconciling OpenClaw integration")
        await reconcile_openclaw_setup(
            config_path,
            is_non_interactive=bool(getattr(args, "non_interactive", False)),
            progress=progress,
        )
        actions.append("openclaw_dual_surface")
    if section in {"all", "service"}:
        requested_port = getattr(args, "port", None)
        with command_env(config_path=config_path):
            settings = load_settings()
        effective_port = requested_port if requested_port is not None else settings.api_port
        progress.step(
            "server",
            f"Checking local API bind target {settings.api_host}:{effective_port}",
        )
        server_payload = build_server_bind_check_payload(
            settings.api_host,
            effective_port,
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
            _service_install_args(args, config_path, requested_port),
            progress=progress,
        )
        if service_install_result != 0:
            return service_install_result
        actions.append("service_manager")

    payload = {"ok": True, "section": section, "actions": actions}
    if args.json:
        print_json(payload)
    else:
        is_rich = rich_enabled(args)
        print(heading("AutoClaw configure", is_rich=is_rich))
        print(f"applied: {accent(', '.join(actions) or 'no changes', is_rich=is_rich)}")
    return 0


def _emit_prompt_unavailable_exit(command_name: str, exc: PromptUnavailableError) -> int:
    is_rich = rich_enabled()
    print(heading(command_name, is_rich=is_rich))
    print(warn(str(exc), is_rich=is_rich))
    return 2


def _select_configure_section(args: argparse.Namespace) -> str:
    is_rich = rich_enabled(args)
    note(
        "Choose which owned slice AutoClaw should reconcile in this run.",
        "AutoClaw configure",
        is_rich=is_rich,
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


def _validate_openclaw_configure_section(
    args: argparse.Namespace,
    *,
    config_path: Path,
    section: str,
    actions: list[str],
    progress: CliProgress,
) -> int | None:
    if not getattr(args, "non_interactive", False) or getattr(args, "openclaw_gateway_token", None):
        progress.step("openclaw", "Reconciling OpenClaw gateway access")
        bootstrap_openclaw_gateway_access(
            config_path=config_path,
            is_non_interactive=bool(getattr(args, "non_interactive", False)),
            gateway_token=getattr(args, "openclaw_gateway_token", None),
            gateway_port=getattr(args, "openclaw_gateway_port", None),
            command_observer=progress.command,
            command_output_observer=progress.command_output,
        )
    progress.step("openclaw", "Checking OpenClaw support")
    preflight = collect_openclaw_preflight(config_path=config_path)
    if preflight.host_state.support_status == "supported":
        return None

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


async def _repair_database_section(
    config_path: Path,
    *,
    progress: CliProgress,
) -> None:
    with command_env(config_path=config_path):
        settings = load_settings()
        progress.step("database", "Running database upgrade")
        await ensure_database_ready_with_legacy_sqlite_repair(
            settings.database_url,
            progress=progress,
        )


def _service_install_args(
    args: argparse.Namespace,
    config_path: Path,
    requested_port: int | None,
) -> argparse.Namespace:
    return argparse.Namespace(
        config=str(config_path),
        data_dir=None,
        env_file=None,
        name=DEFAULT_SERVICE_NAME,
        unit_dir=None,
        port=requested_port,
        force=args.force,
        no_start=args.no_start,
        json=getattr(args, "json", False),
        plain=getattr(args, "plain", False),
        no_color=getattr(args, "no_color", False),
        verbose=getattr(args, "verbose", False),
    )


__all__ = ["cmd_configure"]
