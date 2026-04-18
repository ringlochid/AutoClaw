from __future__ import annotations

from pathlib import Path
from uuid import UUID

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


def task_data_dir(task_id: UUID | str, data_dir: Path | None = None) -> Path:
    return (data_dir or default_data_dir()) / "tasks" / str(task_id)


def task_workspace_dir(task_id: UUID | str, data_dir: Path | None = None) -> Path:
    return task_data_dir(task_id, data_dir) / "workspace"


def task_context_dir(task_id: UUID | str, data_dir: Path | None = None) -> Path:
    return task_data_dir(task_id, data_dir) / "context"


def task_manifests_dir(task_id: UUID | str, data_dir: Path | None = None) -> Path:
    return task_data_dir(task_id, data_dir) / "manifests"


def ensure_task_dirs(task_id: UUID | str, data_dir: Path | None = None) -> dict[str, Path]:
    directories = {
        "task_dir": task_data_dir(task_id, data_dir),
        "workspace": task_workspace_dir(task_id, data_dir),
        "context": task_context_dir(task_id, data_dir),
        "manifests": task_manifests_dir(task_id, data_dir),
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return directories


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
