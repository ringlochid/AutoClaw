from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import webbrowser
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, cast

import httpx
import uvicorn
from alembic.config import Config

from alembic import command
from app.config import _CONFIG_ENV_VAR, get_settings, load_settings
from app.db.session import dispose_db_engine, get_session_factory, ping_database
from app.integrations.openclaw import OpenClawConfigurationError, create_openclaw_client
from app.paths import (
    default_cache_dir,
    default_config_dir,
    default_config_path,
    default_data_dir,
    default_database_path,
    default_database_url,
    default_state_dir,
)
from app.services.registry_service import bootstrap_registry, iter_definition_files

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_ALEMBIC_ROOT = REPO_ROOT / "alembic"
REPO_CONSOLE_DIST_ROOT = REPO_ROOT.parent / "console" / "dist"
PACKAGED_RESOURCE_PACKAGE = "app.resources"
_console_resource_stacks: list[ExitStack] = []


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
    config_path: str | None = None,
    data_dir: str | None = None,
    database_url: str | None = None,
    base_url: str | None = None,
    gateway_token: str | None = None,
    agent_id: str | None = None,
    log_level: str | None = None,
) -> Iterator[None]:
    overrides = {
        _CONFIG_ENV_VAR: config_path,
        "AUTOCLAW_DATA_DIR": data_dir,
        "AUTOCLAW_DATABASE_URL": database_url,
        "AUTOCLAW_OPENCLAW_BASE_URL": base_url,
        "AUTOCLAW_OPENCLAW_GATEWAY_TOKEN": gateway_token,
        "AUTOCLAW_OPENCLAW_AGENT_ID": agent_id,
        "AUTOCLAW_LOG_LEVEL": log_level,
    }
    with _temporary_env(overrides):
        yield


def _default_paths() -> dict[str, Path]:
    return {
        "config_path": default_config_path().resolve(),
        "config_dir": default_config_dir().resolve(),
        "data_dir": default_data_dir().resolve(),
        "state_dir": default_state_dir().resolve(),
        "cache_dir": default_cache_dir().resolve(),
    }


def _resolved_paths(settings: Any) -> dict[str, Path]:
    config_path = _coerce_path(settings.config_path)
    data_dir = _coerce_path(settings.data_dir)
    return {
        "config_path": config_path,
        "config_dir": config_path.parent,
        "data_dir": data_dir,
        "state_dir": default_state_dir().resolve(),
        "cache_dir": default_cache_dir().resolve(),
    }


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
    settings: Any,
    *,
    api_key: str,
    internal_api_key: str,
) -> str:
    payload: dict[str, dict[str, Any]] = {
        "app": {
            "env": settings.env.value,
            "debug": settings.debug,
            "name": settings.app_name,
        },
        "paths": {
            "data_dir": settings.data_dir,
        },
        "database": {
            "url": settings.database_url,
        },
        "openclaw": {
            "base_url": settings.openclaw_base_url,
            "gateway_token": settings.openclaw_gateway_token,
            "agent_id": settings.openclaw_agent_id,
            "timeout_ms": settings.openclaw_timeout_ms,
            "account": settings.openclaw_account,
        },
        "server": {
            "host": settings.api_host,
            "port": settings.api_port,
            "console_origins": settings.console_origins,
        },
        "logging": {
            "level": settings.log_level,
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


def _redact_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}…{value[-4:]}"


def _public_settings_payload(settings: Any, *, include_defaults: bool) -> dict[str, Any]:
    payload = cast(
        dict[str, Any],
        settings.model_dump(mode="json", exclude_defaults=not include_defaults),
    )
    payload["config_path"] = str(settings.config_path)
    payload["data_dir"] = str(settings.data_dir)
    payload["api_key"] = _redact_secret(settings.api_key)
    payload["internal_api_key"] = _redact_secret(settings.internal_api_key)
    payload["default_database_url"] = default_database_url(settings.data_dir)
    return payload


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _resolve_database_url(args: argparse.Namespace) -> str | None:
    database_url = cast(str | None, args.database_url)
    sqlite_path = cast(str | None, args.sqlite_path)
    if database_url and sqlite_path:
        raise SystemExit("Use either --database-url or --sqlite-path, not both.")
    if sqlite_path:
        return f"sqlite+aiosqlite:///{_coerce_path(sqlite_path)}"
    return database_url


def _ensure_parent_dirs(paths: dict[str, Path]) -> None:
    paths["config_dir"].mkdir(parents=True, exist_ok=True)
    paths["data_dir"].mkdir(parents=True, exist_ok=True)
    paths["state_dir"].mkdir(parents=True, exist_ok=True)
    paths["cache_dir"].mkdir(parents=True, exist_ok=True)


def _write_config_if_needed(
    settings: Any,
    *,
    force: bool,
    api_key: str,
    internal_api_key: str,
) -> tuple[bool, Path]:
    config_path = _coerce_path(settings.config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists() and not force:
        return False, config_path

    config_path.write_text(
        _settings_to_config_text(
            settings,
            api_key=api_key,
            internal_api_key=internal_api_key,
        ),
        encoding="utf-8",
    )
    return True, config_path


@contextmanager
def _alembic_script_root() -> Iterator[Path]:
    try:
        from importlib import resources

        resource_root = resources.files(PACKAGED_RESOURCE_PACKAGE).joinpath("alembic")
        if resource_root.is_dir():
            stack = ExitStack()
            try:
                resolved_root = Path(stack.enter_context(resources.as_file(resource_root)))
                yield resolved_root
                return
            finally:
                stack.close()
    except ModuleNotFoundError:
        pass

    yield REPO_ALEMBIC_ROOT


def _resolve_packaged_console_dist_root() -> Path | None:
    try:
        from importlib import resources

        resource_root = resources.files(PACKAGED_RESOURCE_PACKAGE).joinpath("web")
        if not resource_root.is_dir():
            return None

        resource_stack = ExitStack()
        resolved_root = Path(resource_stack.enter_context(resources.as_file(resource_root)))
        if not resolved_root.is_dir():
            resource_stack.close()
            return None

        _console_resource_stacks.append(resource_stack)
        return resolved_root
    except ModuleNotFoundError:
        return None



def _resolve_console_dist_root() -> Path | None:
    packaged_root = _resolve_packaged_console_dist_root()
    if packaged_root is not None:
        return packaged_root
    if REPO_CONSOLE_DIST_ROOT.is_dir():
        return REPO_CONSOLE_DIST_ROOT
    return None



def _build_alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _run_db_upgrade(database_url: str, revision: str) -> None:
    with _alembic_script_root() as script_root:
        config = _build_alembic_config(database_url)
        config.set_main_option("script_location", str(script_root))
        command.upgrade(config, revision)


async def _run_db_upgrade_async(database_url: str, revision: str) -> None:
    await asyncio.to_thread(_run_db_upgrade, database_url, revision)


async def _run_db_bootstrap(*, definitions_root: Path | None = None) -> dict[str, int]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await bootstrap_registry(
            session,
            publish=True,
            definitions_root=definitions_root,
        )
        await session.commit()
        return result


async def _check_openclaw_reachability(
    *,
    base_url: str,
    gateway_token: str,
    agent_id: str,
) -> dict[str, Any]:
    del agent_id

    headers = {"Authorization": f"Bearer {gateway_token}"}
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=10.0) as client:
        last_response: httpx.Response | None = None
        for path in ("/healthz", "/readyz", "/"):
            response = await client.get(path, headers=headers)
            last_response = response
            if response.status_code < 500:
                return {
                    "ok": True,
                    "path": path,
                    "status_code": response.status_code,
                }

    return {
        "ok": False,
        "path": last_response.request.url.path if last_response is not None else None,
        "status_code": last_response.status_code if last_response is not None else None,
    }


async def _cmd_init(args: argparse.Namespace) -> int:
    database_url_override = _resolve_database_url(args)
    config_override = str(_coerce_path(args.config)) if args.config else None
    data_dir_override = str(_coerce_path(args.data_dir)) if args.data_dir else None

    with _command_env(
        config_path=config_override,
        data_dir=data_dir_override,
        database_url=database_url_override,
    ):
        settings = load_settings()
        resolved_paths = _resolved_paths(settings)
        _ensure_parent_dirs(resolved_paths)

        if settings.database_url.startswith("sqlite+"):
            default_database_path(settings.data_dir).parent.mkdir(parents=True, exist_ok=True)
            if args.sqlite_path:
                _coerce_path(args.sqlite_path).parent.mkdir(parents=True, exist_ok=True)

        api_key = settings.api_key or secrets.token_urlsafe(24)
        internal_api_key = settings.internal_api_key or secrets.token_urlsafe(24)
        wrote_config, config_path = _write_config_if_needed(
            settings,
            force=args.force,
            api_key=api_key,
            internal_api_key=internal_api_key,
        )

        if not args.skip_db_upgrade:
            await _run_db_upgrade_async(settings.database_url, args.revision)
        bootstrap_result: dict[str, int] | None = None
        if not args.skip_bootstrap:
            bootstrap_result = await _run_db_bootstrap()

        payload = {
            "ok": True,
            "config_path": str(config_path),
            "config_written": wrote_config,
            "database_url": settings.database_url,
            "bootstrap": bootstrap_result,
        }
        if args.json:
            _print_json(payload)
        else:
            print(f"Initialized AutoClaw at {config_path}")
            print(f"Database: {settings.database_url}")
            if bootstrap_result is not None:
                print(
                    "Bootstrapped definitions: "
                    + ", ".join(f"{key}={value}" for key, value in bootstrap_result.items())
                )
        return 0


def _serve_browser_host(host: str) -> str:
    if host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return host


def _cmd_serve(args: argparse.Namespace) -> int:
    database_url_override = _resolve_database_url(args)
    config_override = str(_coerce_path(args.config)) if args.config else None
    with _command_env(
        config_path=config_override,
        database_url=database_url_override,
        log_level=args.log_level,
    ):
        settings = get_settings()
        host = args.host or settings.api_host
        port = args.port or settings.api_port
        if args.open_browser:
            webbrowser.open(f"http://{_serve_browser_host(host)}:{port}")
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=args.reload,
            log_level=(args.log_level or settings.log_level).lower(),
        )
    return 0


async def _cmd_db_upgrade(args: argparse.Namespace) -> int:
    database_url_override = _resolve_database_url(args)
    config_override = str(_coerce_path(args.config)) if args.config else None
    with _command_env(
        config_path=config_override,
        database_url=database_url_override,
    ):
        settings = load_settings()
        await _run_db_upgrade_async(settings.database_url, args.revision)
        if args.json:
            _print_json(
                {
                    "ok": True,
                    "database_url": settings.database_url,
                    "revision": args.revision,
                }
            )
        else:
            print(f"Upgraded database to {args.revision}: {settings.database_url}")
        return 0


async def _cmd_db_bootstrap(args: argparse.Namespace) -> int:
    database_url_override = _resolve_database_url(args)
    config_override = str(_coerce_path(args.config)) if args.config else None
    definitions_root = _coerce_path(args.definitions_root) if args.definitions_root else None
    with _command_env(
        config_path=config_override,
        database_url=database_url_override,
    ):
        result = await _run_db_bootstrap(definitions_root=definitions_root)
        if args.json:
            _print_json({"ok": True, **result})
        else:
            print(
                "Bootstrapped definitions: "
                + ", ".join(f"{key}={value}" for key, value in result.items())
            )
        return 0


async def _cmd_doctor(args: argparse.Namespace) -> int:
    database_url_override = _resolve_database_url(args)
    config_override = str(_coerce_path(args.config)) if args.config else None
    with _command_env(
        config_path=config_override,
        database_url=database_url_override,
    ):
        settings = load_settings()
        roles = iter_definition_files("roles")
        policies = iter_definition_files("policies")
        workflows = iter_definition_files("workflows")
        console_root = _resolve_console_dist_root()

        database_check: dict[str, bool | str | None] = {"ok": True, "detail": None}
        try:
            await ping_database()
        except Exception as exc:
            database_check = {"ok": False, "detail": str(exc)}

        token_configured = False
        openclaw_check: dict[str, Any] = {
            "configured": bool(settings.openclaw_base_url),
            "base_url": settings.openclaw_base_url,
            "agent_id": settings.openclaw_agent_id,
            "token_configured": False,
            "reachable": None,
            "detail": None,
        }
        try:
            client = create_openclaw_client(settings)
            token_configured = True
            openclaw_check["token_configured"] = True
            reachability = await _check_openclaw_reachability(
                base_url=client.base_url,
                gateway_token=client.gateway_token,
                agent_id=client.agent_id,
            )
            openclaw_check["reachable"] = reachability["ok"]
            openclaw_check["detail"] = reachability
        except OpenClawConfigurationError as exc:
            openclaw_check["detail"] = str(exc)
        except Exception as exc:
            openclaw_check["reachable"] = False
            openclaw_check["detail"] = str(exc)

        payload = {
            "ok": database_check["ok"]
            and bool(roles)
            and bool(policies)
            and bool(workflows)
            and console_root is not None,
            "config_path": str(settings.config_path),
            "database": {
                "url": settings.database_url,
                **database_check,
            },
            "resources": {
                "console": {
                    "ok": console_root is not None,
                    "root": str(console_root) if console_root is not None else None,
                },
                "definitions": {
                    "ok": bool(roles) and bool(policies) and bool(workflows),
                    "roles": len(roles),
                    "policies": len(policies),
                    "workflows": len(workflows),
                },
                "alembic": {
                    "ok": REPO_ALEMBIC_ROOT.is_dir() or True,
                },
            },
            "openclaw": openclaw_check,
            "warnings": [] if token_configured else ["OpenClaw gateway token is not configured."],
        }
        if args.json:
            _print_json(payload)
        else:
            print(f"Config: {settings.config_path}")
            print(f"Database: {'ok' if database_check['ok'] else 'failed'}")
            print(f"Console assets: {'ok' if console_root is not None else 'missing'}")
            print(
                "Definitions: "
                f"roles={len(roles)} policies={len(policies)} workflows={len(workflows)}"
            )
            if openclaw_check["reachable"] is True:
                print(f"OpenClaw: reachable at {settings.openclaw_base_url}")
            elif token_configured:
                print(f"OpenClaw: configured but unreachable ({openclaw_check['detail']})")
            else:
                print("OpenClaw: token not configured")
        return 0 if payload["ok"] else 1


def _cmd_config_path(args: argparse.Namespace) -> int:
    config_override = str(_coerce_path(args.config)) if getattr(args, "config", None) else None
    with _command_env(config_path=config_override):
        settings = load_settings()
        payload = {key: str(value) for key, value in _resolved_paths(settings).items()}
        if args.json:
            _print_json(payload)
        else:
            print(f"config_path={payload['config_path']}")
            print(f"config_dir={payload['config_dir']}")
            print(f"data_dir={payload['data_dir']}")
            print(f"state_dir={payload['state_dir']}")
            print(f"cache_dir={payload['cache_dir']}")
        return 0


def _cmd_config_show(args: argparse.Namespace) -> int:
    config_override = str(_coerce_path(args.config)) if args.config else None
    with _command_env(config_path=config_override):
        settings = load_settings()
        payload = _public_settings_payload(settings, include_defaults=args.include_defaults)
        if args.json:
            _print_json(payload)
        else:
            for key, value in payload.items():
                print(f"{key}={value}")
        return 0


async def _cmd_openclaw_check(args: argparse.Namespace) -> int:
    config_override = str(_coerce_path(args.config)) if args.config else None
    with _command_env(
        config_path=config_override,
        base_url=args.base_url,
        gateway_token=args.token,
        agent_id=args.agent_id,
    ):
        settings = load_settings()
        client = create_openclaw_client(settings)
        payload = await _check_openclaw_reachability(
            base_url=client.base_url,
            gateway_token=client.gateway_token,
            agent_id=client.agent_id,
        )
        result = {
            "ok": payload["ok"],
            "base_url": client.base_url,
            "agent_id": client.agent_id,
            **payload,
        }
        if args.json:
            _print_json(result)
        else:
            if result["ok"]:
                print(
                    f"OpenClaw reachable at {client.base_url} via {result['path']} "
                    f"(HTTP {result['status_code']})"
                )
            else:
                print(
                    f"OpenClaw check failed for {client.base_url}: "
                    f"HTTP {result['status_code']} on {result['path']}"
                )
        return 0 if result["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autoclaw")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--config")
    init_parser.add_argument("--data-dir")
    init_parser.add_argument("--database-url")
    init_parser.add_argument("--sqlite-path")
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--skip-bootstrap", action="store_true")
    init_parser.add_argument("--skip-db-upgrade", action="store_true")
    init_parser.add_argument("--revision", default="head")
    init_parser.add_argument("--json", action="store_true")
    init_parser.set_defaults(handler=_cmd_init)

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--config")
    serve_parser.add_argument("--host")
    serve_parser.add_argument("--port", type=int)
    serve_parser.add_argument("--reload", action="store_true")
    serve_parser.add_argument("--open-browser", action="store_true")
    serve_parser.add_argument("--database-url")
    serve_parser.add_argument("--sqlite-path")
    serve_parser.add_argument("--log-level")
    serve_parser.set_defaults(handler=_cmd_serve)

    db_parser = subparsers.add_parser("db")
    db_subparsers = db_parser.add_subparsers(dest="db_command", required=True)

    db_upgrade_parser = db_subparsers.add_parser("upgrade")
    db_upgrade_parser.add_argument("--config")
    db_upgrade_parser.add_argument("--database-url")
    db_upgrade_parser.add_argument("--sqlite-path")
    db_upgrade_parser.add_argument("--revision", default="head")
    db_upgrade_parser.add_argument("--json", action="store_true")
    db_upgrade_parser.set_defaults(handler=_cmd_db_upgrade)

    db_bootstrap_parser = db_subparsers.add_parser("bootstrap")
    db_bootstrap_parser.add_argument("--config")
    db_bootstrap_parser.add_argument("--database-url")
    db_bootstrap_parser.add_argument("--sqlite-path")
    db_bootstrap_parser.add_argument("--definitions-root")
    db_bootstrap_parser.add_argument("--force", action="store_true")
    db_bootstrap_parser.add_argument("--json", action="store_true")
    db_bootstrap_parser.set_defaults(handler=_cmd_db_bootstrap)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--config")
    doctor_parser.add_argument("--database-url")
    doctor_parser.add_argument("--sqlite-path")
    doctor_parser.add_argument("--json", action="store_true")
    doctor_parser.set_defaults(handler=_cmd_doctor)

    config_parser = subparsers.add_parser("config")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)

    config_path_parser = config_subparsers.add_parser("path")
    config_path_parser.add_argument("--config")
    config_path_parser.add_argument("--json", action="store_true")
    config_path_parser.set_defaults(handler=_cmd_config_path)

    config_show_parser = config_subparsers.add_parser("show")
    config_show_parser.add_argument("--config")
    config_show_parser.add_argument("--json", action="store_true")
    config_show_parser.add_argument("--include-defaults", action="store_true")
    config_show_parser.set_defaults(handler=_cmd_config_show)

    openclaw_parser = subparsers.add_parser("openclaw")
    openclaw_subparsers = openclaw_parser.add_subparsers(dest="openclaw_command", required=True)

    openclaw_check_parser = openclaw_subparsers.add_parser("check")
    openclaw_check_parser.add_argument("--config")
    openclaw_check_parser.add_argument("--base-url")
    openclaw_check_parser.add_argument("--token")
    openclaw_check_parser.add_argument("--agent-id")
    openclaw_check_parser.add_argument("--json", action="store_true")
    openclaw_check_parser.set_defaults(handler=_cmd_openclaw_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    try:
        result = handler(args)
        if asyncio.iscoroutine(result):
            return int(asyncio.run(cast(Any, result)))
        return int(result or 0)
    finally:
        asyncio.run(dispose_db_engine())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
