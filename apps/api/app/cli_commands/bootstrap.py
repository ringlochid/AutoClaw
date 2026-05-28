from __future__ import annotations

import argparse
import asyncio
import json
import secrets
from pathlib import Path
from typing import Any

import uvicorn
from sqlalchemy.engine import make_url

from app.cli_support import coerce_path, command_env, print_json
from app.config import OpenClawSettings, RuntimeSettings, load_settings
from app.db.session import (
    dispose_db_engine,
    ensure_database_schema,
    get_session_factory,
    ping_database,
)
from app.paths import default_data_dir, default_database_url, ensure_runtime_dirs
from app.registry import seed_definition_registry
from app.runtime.openclaw.host_setup import AUTOCLAW_OPERATOR_AGENT_ID, AUTOCLAW_WORKER_AGENT_ID


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Path):
        return json.dumps(str(value))
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value))


def _config_sections_to_text(payload: dict[str, dict[str, Any]]) -> str:
    section_order = (
        "paths",
        "database",
        "server",
        "logging",
        "security",
        "openclaw",
        "runtime",
    )
    ordered_sections = [
        section for section in section_order if isinstance(payload.get(section), dict)
    ]
    ordered_sections.extend(
        section
        for section in payload
        if section not in ordered_sections and isinstance(payload[section], dict)
    )

    lines: list[str] = []
    for section in ordered_sections:
        values = payload[section]
        rendered_values = [
            (key, value) for key, value in values.items() if value is not None and value != ""
        ]
        if not rendered_values:
            continue
        lines.append(f"[{section}]")
        for key, value in rendered_values:
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def settings_to_config_text(
    *,
    data_dir: Path,
    database_url: str,
    host: str,
    port: int,
    log_level: str,
    api_key: str,
    internal_api_key: str,
) -> str:
    payload: dict[str, dict[str, Any]] = {
        "paths": {
            "data_dir": data_dir,
        },
        "database": {
            "url": database_url,
            "echo": False,
        },
        "server": {
            "host": host,
            "port": port,
            "console_origins": [
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:4173",
                "http://localhost:4173",
            ],
        },
        "logging": {
            "level": log_level,
        },
        "security": {
            "api_key": api_key,
            "internal_api_key": internal_api_key,
        },
        "openclaw": {
            "base_url": OpenClawSettings().base_url,
            "agent_id": AUTOCLAW_WORKER_AGENT_ID,
            "operator_agent_id": AUTOCLAW_OPERATOR_AGENT_ID,
            "timeout_ms": OpenClawSettings().timeout_ms,
        },
        "runtime": RuntimeSettings().model_dump(mode="json"),
    }
    return _config_sections_to_text(payload)


def update_config_sections(
    config_path: Path,
    *,
    section_updates: dict[str, dict[str, Any]],
) -> None:
    import tomllib

    if config_path.is_file():
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    else:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    for section, values in section_updates.items():
        existing = payload.get(section)
        next_values = dict(existing) if isinstance(existing, dict) else {}
        for key, value in values.items():
            if value is None or value == "":
                next_values.pop(key, None)
            else:
                next_values[key] = value
        if next_values:
            payload[section] = next_values
        else:
            payload.pop(section, None)
    config_path.write_text(
        _config_sections_to_text(
            {key: value for key, value in payload.items() if isinstance(value, dict)}
        ),
        encoding="utf-8",
    )


def sqlite_database_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    return Path(url.database).expanduser().resolve()


def ensure_sqlite_database(database_url: str) -> Path | None:
    database_path = sqlite_database_path(database_url)
    if database_path is None:
        return None
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch(exist_ok=True)
    return database_path


def reset_sqlite_database(database_url: str) -> Path:
    database_path = sqlite_database_path(database_url)
    if database_path is None:
        raise ValueError("db reset only supports sqlite URLs during Phase 0.5")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    database_path.touch()
    return database_path


async def ensure_database_ready(database_url: str) -> None:
    ensure_sqlite_database(database_url)
    await ping_database()
    await ensure_database_schema()
    async with get_session_factory()() as session:
        await seed_definition_registry(session)
        await session.commit()
    await dispose_db_engine()


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
        await dispose_db_engine()
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
    "cmd_db_reset",
    "cmd_db_upgrade",
    "cmd_init",
    "cmd_serve",
    "ensure_database_ready",
    "ensure_sqlite_database",
    "reset_sqlite_database",
    "settings_to_config_text",
    "sqlite_database_path",
    "update_config_sections",
]
