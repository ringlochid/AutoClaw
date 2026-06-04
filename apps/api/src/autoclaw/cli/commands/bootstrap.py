from __future__ import annotations

import argparse
import asyncio
import secrets

import uvicorn

from autoclaw.cli.commands.bootstrap_config import settings_to_config_text, update_config_sections
from autoclaw.cli.commands.bootstrap_database import (
    DatabaseRepairResult,
    ensure_database_ready,
    ensure_database_ready_with_legacy_sqlite_repair,
    ensure_sqlite_database,
    reset_sqlite_database,
    sqlite_database_path,
)
from autoclaw.cli.commands.openclaw.support import (
    collect_openclaw_preflight,
    emit_openclaw_preflight_failure,
)
from autoclaw.cli.support import coerce_path, command_env, print_json
from autoclaw.config import load_settings
from autoclaw.paths import default_data_dir, default_database_url, ensure_runtime_dirs


async def cmd_init(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    data_dir = coerce_path(args.data_dir or default_data_dir())
    database_url = args.database_url or default_database_url(data_dir)
    api_key = args.api_key or secrets.token_urlsafe(24)
    internal_api_key = args.internal_api_key or secrets.token_urlsafe(24)

    if config_path.exists() and not args.force:
        raise FileExistsError(
            f"Refusing to overwrite existing config without --force: {config_path}"
        )

    ensure_runtime_dirs(config_dir=config_path.parent, data_dir=data_dir)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        settings_to_config_text(
            data_dir=data_dir,
            database_url=database_url,
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            api_key=api_key,
            internal_api_key=internal_api_key,
        ),
        encoding="utf-8",
    )

    with command_env(
        config_path=config_path,
        data_dir=data_dir,
        database_url=database_url,
        api_host=args.host,
        api_port=args.port,
        log_level=args.log_level,
        api_key=api_key,
        internal_api_key=internal_api_key,
    ):
        if not args.skip_db_upgrade:
            await ensure_database_ready(database_url)

    payload = {
        "ok": True,
        "config_path": str(config_path),
        "data_dir": str(data_dir),
        "database_url": database_url,
    }
    if args.json:
        print_json(payload)
    else:
        print(f"Initialized config at {config_path}")
    return 0


def cmd_db_upgrade(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
        asyncio.run(ensure_database_ready(settings.database_url))
    return 0


async def cmd_db_reset(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
        await asyncio.to_thread(reset_sqlite_database, settings.database_url)
        await ensure_database_ready(settings.database_url)

    payload = {
        "ok": True,
        "database_url": settings.database_url,
    }
    if args.json:
        print_json(payload)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    preflight = collect_openclaw_preflight(config_path=config_path)
    if preflight.host_state.support_status != "supported":
        return emit_openclaw_preflight_failure(
            command_name="AutoClaw serve",
            args=args,
            openclaw_payload=preflight.payload,
            stopped_before="stopped before API startup",
        )
    with command_env(config_path=config_path):
        settings = load_settings()
        uvicorn.run(
            "app.main:app",
            host=settings.api_host,
            port=settings.api_port,
            log_level=settings.log_level.lower(),
            reload=False,
        )
    return 0


__all__ = [
    "DatabaseRepairResult",
    "cmd_db_reset",
    "cmd_db_upgrade",
    "cmd_init",
    "cmd_serve",
    "ensure_database_ready",
    "ensure_database_ready_with_legacy_sqlite_repair",
    "ensure_sqlite_database",
    "reset_sqlite_database",
    "settings_to_config_text",
    "sqlite_database_path",
    "update_config_sections",
]
