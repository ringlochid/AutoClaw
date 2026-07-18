from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from autoclaw.config import CONFIG_ENV_VAR, get_settings


def coerce_path(value: str | os.PathLike[str] | Path) -> Path:
    return Path(value).expanduser().resolve()


@contextmanager
def command_env(
    *,
    config_path: Path,
    data_dir: Path | None = None,
    database_url: str | None = None,
    api_host: str | None = None,
    api_port: int | None = None,
    log_level: str | None = None,
    env: str | None = None,
) -> Iterator[None]:
    overrides = {
        CONFIG_ENV_VAR: str(config_path),
        "AUTOCLAW_DATA_DIR": str(data_dir) if data_dir is not None else None,
        "AUTOCLAW_DATABASE_URL": database_url,
        "AUTOCLAW_API_HOST": api_host,
        "AUTOCLAW_API_PORT": str(api_port) if api_port is not None else None,
        "AUTOCLAW_LOG_LEVEL": log_level,
        "AUTOCLAW_ENV": env,
    }
    with temporary_env(overrides):
        yield


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


@contextmanager
def temporary_env(overrides: dict[str, str | None]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                if key == "AUTOCLAW_ENV":
                    continue
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


__all__ = ["coerce_path", "command_env", "print_json", "temporary_env"]
