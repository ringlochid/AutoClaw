from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Any

import uvicorn
from sqlalchemy.engine import make_url

from app.config import _CONFIG_ENV_VAR, get_settings, load_settings
from app.db.session import dispose_db_engine, ping_database
from app.paths import (
    default_config_path,
    default_data_dir,
    default_database_url,
    ensure_runtime_dirs,
)

DEFAULT_SERVICE_NAME = "autoclaw"
DEFAULT_SERVICE_ENV_TEXT = """# Optional overrides for the AutoClaw user service.
# Add environment-only overrides here if you need them.
"""
SYSTEMD_TEMPLATE_RESOURCE = ("systemd", "autoclaw.service")


def _coerce_path(value: str | os.PathLike[str] | Path) -> Path:
    return Path(value).expanduser().resolve()


@contextmanager
def _temporary_env(overrides: dict[str, str | None]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()


@contextmanager
def _command_env(
    *,
    config_path: Path,
    data_dir: Path | None = None,
    database_url: str | None = None,
    api_host: str | None = None,
    api_port: int | None = None,
    log_level: str | None = None,
    api_key: str | None = None,
    internal_api_key: str | None = None,
) -> Iterator[None]:
    overrides = {
        _CONFIG_ENV_VAR: str(config_path),
        "AUTOCLAW_DATA_DIR": str(data_dir) if data_dir is not None else None,
        "AUTOCLAW_DATABASE_URL": database_url,
        "AUTOCLAW_API_HOST": api_host,
        "AUTOCLAW_API_PORT": str(api_port) if api_port is not None else None,
        "AUTOCLAW_LOG_LEVEL": log_level,
        "AUTOCLAW_API_KEY": api_key,
        "AUTOCLAW_INTERNAL_API_KEY": internal_api_key,
    }
    with _temporary_env(overrides):
        yield


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


def _settings_to_config_text(
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
    }

    lines: list[str] = []
    for section, values in payload.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _render_service_unit(
    *,
    python_bin: Path,
    config_path: Path,
    data_dir: Path,
    env_file: Path,
) -> str:
    template_path = resources.files("app.resources").joinpath(*SYSTEMD_TEMPLATE_RESOURCE)
    rendered = template_path.read_text(encoding="utf-8")
    replacements = {
        "@AUTOCLAW_PYTHON@": str(python_bin),
        "@AUTOCLAW_CONFIG@": str(config_path),
        "@AUTOCLAW_DATA_DIR@": str(data_dir),
        "@AUTOCLAW_ENV_FILE@": str(env_file),
    }
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoclaw")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--config", default=str(default_config_path()))
    init_parser.add_argument("--data-dir")
    init_parser.add_argument("--database-url")
    init_parser.add_argument("--host", default="127.0.0.1")
    init_parser.add_argument("--port", type=int, default=8123)
    init_parser.add_argument("--log-level", default="INFO")
    init_parser.add_argument("--api-key")
    init_parser.add_argument("--internal-api-key")
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--skip-db-upgrade", action="store_true")
    init_parser.add_argument("--json", action="store_true")
    init_parser.set_defaults(handler=_cmd_init)

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--config", default=str(default_config_path()))
    serve_parser.set_defaults(handler=_cmd_serve)

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

    service_parser = subparsers.add_parser("service")
    service_subparsers = service_parser.add_subparsers(dest="service_command", required=True)

    service_render_parser = service_subparsers.add_parser("render")
    service_render_parser.add_argument("--config", default=str(default_config_path()))
    service_render_parser.add_argument("--data-dir")
    service_render_parser.add_argument("--env-file")
    service_render_parser.set_defaults(handler=_cmd_service_render)

    service_install_parser = service_subparsers.add_parser("install")
    service_install_parser.add_argument("--config", default=str(default_config_path()))
    service_install_parser.add_argument("--data-dir")
    service_install_parser.add_argument("--env-file")
    service_install_parser.add_argument("--name", default=DEFAULT_SERVICE_NAME)
    service_install_parser.add_argument("--unit-dir")
    service_install_parser.add_argument("--force", action="store_true")
    service_install_parser.add_argument("--no-start", action="store_true")
    service_install_parser.set_defaults(handler=_cmd_service_install)

    return parser


def _sqlite_database_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    return Path(url.database).expanduser().resolve()


def _ensure_sqlite_database(database_url: str) -> Path | None:
    database_path = _sqlite_database_path(database_url)
    if database_path is None:
        return None
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch(exist_ok=True)
    return database_path


def _reset_sqlite_database(database_url: str) -> Path:
    database_path = _sqlite_database_path(database_url)
    if database_path is None:
        raise ValueError("db reset only supports sqlite URLs during Phase 0.5")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()
    database_path.touch()
    return database_path


async def _ensure_database_ready(database_url: str) -> None:
    _ensure_sqlite_database(database_url)
    await ping_database()
    await dispose_db_engine()


def _service_env_file_path(config_path: Path, explicit_env_file: str | None) -> Path:
    if explicit_env_file is not None:
        return _coerce_path(explicit_env_file)
    return config_path.parent / "autoclaw.env"


async def _cmd_init(args: argparse.Namespace) -> int:
    config_path = _coerce_path(args.config)
    data_dir = _coerce_path(args.data_dir or default_data_dir())
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
        _settings_to_config_text(
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

    with _command_env(
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
            await _ensure_database_ready(database_url)

    payload = {
        "ok": True,
        "config_path": str(config_path),
        "data_dir": str(data_dir),
        "database_url": database_url,
    }
    if args.json:
        _print_json(payload)
    else:
        print(f"Initialized config at {config_path}")
    return 0


def _cmd_db_upgrade(args: argparse.Namespace) -> int:
    config_path = _coerce_path(args.config)
    with _command_env(config_path=config_path):
        settings = load_settings()
        asyncio.run(_ensure_database_ready(settings.database_url))
    return 0


async def _cmd_db_reset(args: argparse.Namespace) -> int:
    config_path = _coerce_path(args.config)
    with _command_env(config_path=config_path):
        settings = load_settings()
        await dispose_db_engine()
        await asyncio.to_thread(_reset_sqlite_database, settings.database_url)
        await _ensure_database_ready(settings.database_url)

    payload = {
        "ok": True,
        "database_url": settings.database_url,
    }
    if args.json:
        _print_json(payload)
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    config_path = _coerce_path(args.config)
    with _command_env(config_path=config_path):
        settings = load_settings()
        uvicorn.run(
            "app.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=False,
        )
    return 0


def _cmd_service_render(args: argparse.Namespace) -> int:
    config_path = _coerce_path(args.config)
    with _command_env(config_path=config_path):
        settings = load_settings()

    data_dir = _coerce_path(args.data_dir or settings.data_dir)
    env_file = _service_env_file_path(config_path, args.env_file)
    print(
        _render_service_unit(
            python_bin=Path(sys.executable),
            config_path=config_path,
            data_dir=data_dir,
            env_file=env_file,
        )
    )
    return 0


def _cmd_service_install(args: argparse.Namespace) -> int:
    config_path = _coerce_path(args.config)
    with _command_env(config_path=config_path):
        settings = load_settings()

    data_dir = _coerce_path(args.data_dir or settings.data_dir)
    env_file = _service_env_file_path(config_path, args.env_file)
    unit_dir = _coerce_path(args.unit_dir or Path.home() / ".config" / "systemd" / "user")
    unit_path = unit_dir / f"{args.name}.service"

    unit_dir.mkdir(parents=True, exist_ok=True)
    env_file.parent.mkdir(parents=True, exist_ok=True)
    if env_file.exists() and not args.force:
        raise FileExistsError(
            f"Refusing to overwrite existing env file without --force: {env_file}"
        )
    if unit_path.exists() and not args.force:
        raise FileExistsError(f"Refusing to overwrite existing unit without --force: {unit_path}")

    env_file.write_text(DEFAULT_SERVICE_ENV_TEXT, encoding="utf-8")
    unit_path.write_text(
        _render_service_unit(
            python_bin=Path(sys.executable),
            config_path=config_path,
            data_dir=data_dir,
            env_file=env_file,
        ),
        encoding="utf-8",
    )

    systemctl_bin = os.environ.get("AUTOCLAW_SYSTEMCTL_BIN", "systemctl")
    subprocess.run([systemctl_bin, "--user", "daemon-reload"], check=True)
    subprocess.run([systemctl_bin, "--user", "enable", args.name], check=True)
    if not args.no_start:
        subprocess.run([systemctl_bin, "--user", "restart", args.name], check=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.handler(args)
    if asyncio.iscoroutine(result):
        return int(asyncio.run(result))
    return int(result)
