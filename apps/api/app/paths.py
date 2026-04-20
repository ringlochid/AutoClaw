from __future__ import annotations

from pathlib import Path
from uuid import UUID


def task_slug(task_id: UUID | str, task_key: str | None = None) -> str:
    task_id_str = str(task_id)
    suffix = task_id_str.replace('-', '')[:5]
    if task_key:
        normalized = ''.join(ch.lower() if ch.isalnum() else '-' for ch in task_key).strip('-')
        normalized = '-'.join(part for part in normalized.split('-') if part)
        if normalized:
            return f"{normalized}_{suffix}"
    return task_id_str

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


def default_definitions_root(config_dir: Path | None = None) -> Path:
    return (config_dir or default_config_dir()) / "definitions"


def default_database_path(data_dir: Path | None = None) -> Path:
    return (data_dir or default_data_dir()) / _DATABASE_FILENAME


def default_database_url(data_dir: Path | None = None) -> str:
    return f"sqlite+aiosqlite:///{default_database_path(data_dir)}"


def task_data_dir(
    task_id: UUID | str,
    data_dir: Path | None = None,
    *,
    task_key: str | None = None,
) -> Path:
    return (data_dir or default_data_dir()) / "tasks" / task_slug(task_id, task_key)


def task_workspace_dir(
    task_id: UUID | str,
    data_dir: Path | None = None,
    *,
    task_key: str | None = None,
) -> Path:
    return task_data_dir(task_id, data_dir, task_key=task_key) / "workspace"


def task_context_dir(
    task_id: UUID | str,
    data_dir: Path | None = None,
    *,
    task_key: str | None = None,
) -> Path:
    return task_data_dir(task_id, data_dir, task_key=task_key) / "context"


def task_manifests_dir(
    task_id: UUID | str,
    data_dir: Path | None = None,
    *,
    task_key: str | None = None,
) -> Path:
    return task_data_dir(task_id, data_dir, task_key=task_key) / "manifests"


def ensure_task_dirs(
    task_id: UUID | str,
    data_dir: Path | None = None,
    *,
    task_key: str | None = None,
) -> dict[str, Path]:
    directories = {
        "task_dir": task_data_dir(task_id, data_dir, task_key=task_key),
        "workspace": task_workspace_dir(task_id, data_dir, task_key=task_key),
        "context": task_context_dir(task_id, data_dir, task_key=task_key),
        "manifests": task_manifests_dir(task_id, data_dir, task_key=task_key),
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
