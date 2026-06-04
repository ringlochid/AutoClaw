"""Temporary Phase 6 shim for the legacy app paths owner."""

from __future__ import annotations

from app.paths import (
    APP_NAME,
    default_cache_dir,
    default_config_dir,
    default_config_path,
    default_data_dir,
    default_database_path,
    default_database_url,
    default_state_dir,
    ensure_runtime_dirs,
)

__all__ = [
    "APP_NAME",
    "default_cache_dir",
    "default_config_dir",
    "default_config_path",
    "default_data_dir",
    "default_database_path",
    "default_database_url",
    "default_state_dir",
    "ensure_runtime_dirs",
]
