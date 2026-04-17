from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "autoclaw"
_CONFIG_FILENAME = "config.toml"
_DATABASE_FILENAME = "autoclaw.db"


def _platform_dirs() -> PlatformDirs:
    return PlatformDirs(appname=APP_NAME, appauthor=False)


def default_config_dir() -> Path:
    return Path(_platform_dirs().user_config_path)


def default_data_dir() -> Path:
    return Path(_platform_dirs().user_data_path)


def default_state_dir() -> Path:
    return Path(_platform_dirs().user_state_path)


def default_cache_dir() -> Path:
    return Path(_platform_dirs().user_cache_path)


def default_config_path() -> Path:
    return default_config_dir() / _CONFIG_FILENAME


def default_database_path(data_dir: Path | None = None) -> Path:
    return (data_dir or default_data_dir()) / _DATABASE_FILENAME


def default_database_url(data_dir: Path | None = None) -> str:
    return f"sqlite+aiosqlite:///{default_database_path(data_dir)}"


def ensure_runtime_dirs() -> dict[str, Path]:
    directories = {
        "config_dir": default_config_dir(),
        "data_dir": default_data_dir(),
        "state_dir": default_state_dir(),
        "cache_dir": default_cache_dir(),
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return directories
