from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from autoclaw.cli.support import coerce_path, command_env, print_json
from autoclaw.cli.terminal.theme import accent, rich_enabled
from autoclaw.config import load_settings

REDACTED_VALUE = "__AUTOCLAW_REDACTED__"


def cmd_config_path(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    payload = {"ok": True, "config_path": str(config_path)}
    if args.json:
        print_json(payload)
    else:
        print(accent(str(config_path), is_rich=rich_enabled(args)))
    return 0


def cmd_config_show(args: argparse.Namespace) -> int:
    config_path = coerce_path(args.config)
    with command_env(config_path=config_path):
        settings = load_settings()
    payload = build_settings_payload(settings, config_path)
    print_json(payload)
    return 0


def build_settings_payload(settings: Any, config_path: Path) -> dict[str, Any]:
    payload = {
        "config_path": str(config_path),
        "paths": {
            "data_dir": str(settings.data_dir),
        },
        "database": {
            "url": settings.database_url,
            "echo": settings.database_echo,
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
            "api_key": settings.api_key,
            "internal_api_key": settings.internal_api_key,
        },
        "openclaw": settings.openclaw.model_dump(mode="json"),
        "runtime": settings.runtime.model_dump(mode="json"),
    }
    return _redact_config_payload(payload)


def _redact_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    security = redacted.get("security")
    if isinstance(security, dict):
        security = dict(security)
        for key in ("api_key", "internal_api_key"):
            if security.get(key):
                security[key] = REDACTED_VALUE
        redacted["security"] = security
    openclaw = redacted.get("openclaw")
    if isinstance(openclaw, dict):
        openclaw = dict(openclaw)
        for key in ("gateway_token", "gateway_password"):
            if openclaw.get(key):
                openclaw[key] = REDACTED_VALUE
        redacted["openclaw"] = openclaw
    return redacted


__all__ = [
    "build_settings_payload",
    "cmd_config_path",
    "cmd_config_show",
]
