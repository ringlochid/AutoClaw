from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from app.core.enums import Environment
from app.paths import (
    default_config_path,
    default_data_dir,
    default_database_url,
    default_definitions_root,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = REPO_ROOT / ".env"
_CONFIG_ENV_VAR = "AUTOCLAW_CONFIG"


def _coerce_path(value: str | os.PathLike[str] | Path) -> Path:
    return Path(value).expanduser().resolve()


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _load_toml_settings() -> dict[str, Any]:
    config_path = _coerce_path(os.environ.get(_CONFIG_ENV_VAR, default_config_path()))
    if not config_path.is_file():
        return {"config_path": config_path, "data_dir": default_data_dir()}

    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    loaded: dict[str, Any] = {
        "config_path": config_path,
        "data_dir": _coerce_path(_nested_get(payload, "paths", "data_dir") or default_data_dir()),
    }

    field_mapping = {
        "env": ("app", "env"),
        "debug": ("app", "debug"),
        "app_name": ("app", "name"),
        "database_url": ("database", "url"),
        "openclaw_base_url": ("openclaw", "base_url"),
        "definitions_root": ("paths", "definitions_root"),
        "openclaw_gateway_token": ("openclaw", "gateway_token"),
        "openclaw_internal_api_key": ("openclaw", "internal_api_key"),
        "openclaw_agent_id": ("openclaw", "agent_id"),
        "openclaw_timeout_ms": ("openclaw", "timeout_ms"),
        "openclaw_account": ("openclaw", "account"),
        "console_origins": ("server", "console_origins"),
        "api_host": ("server", "host"),
        "api_port": ("server", "port"),
        "log_level": ("logging", "level"),
        "api_key": ("security", "api_key"),
        "internal_api_key": ("security", "internal_api_key"),
    }
    for field_name, key_path in field_mapping.items():
        value = _nested_get(payload, *key_path)
        if value is not None:
            loaded[field_name] = value
    return loaded


class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        data = self()
        return data.get(field_name), field_name, False

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        return _load_toml_settings()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_prefix="AUTOCLAW_",
        extra="ignore",
    )

    env: Environment = Environment.DEVELOPMENT
    debug: bool = False
    app_name: str = "autoclaw"
    database_url: str = Field(default_factory=default_database_url)
    openclaw_base_url: str = "http://127.0.0.1:18789"
    openclaw_gateway_token: str = ""
    openclaw_internal_api_key: str = ""
    openclaw_agent_id: str = "autoclaw-worker"
    openclaw_timeout_ms: int = 120_000
    openclaw_account: str = "orin_a"
    console_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ]
    )
    api_host: str = "127.0.0.1"
    api_port: int = 8123
    log_level: str = "INFO"
    config_path: Path = Field(default_factory=default_config_path)
    data_dir: Path = Field(default_factory=default_data_dir)
    definitions_root: Path | None = Field(default_factory=default_definitions_root)
    api_key: str = ""
    internal_api_key: str = ""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )


def load_settings() -> Settings:
    settings = Settings()
    settings.config_path = _coerce_path(settings.config_path)
    settings.data_dir = _coerce_path(settings.data_dir)
    if "definitions_root" not in settings.model_fields_set:
        settings.definitions_root = default_definitions_root(settings.config_path.parent)
    if settings.definitions_root is not None:
        settings.definitions_root = _coerce_path(settings.definitions_root)
    if "database_url" not in settings.model_fields_set:
        settings.database_url = default_database_url(settings.data_dir)
    if settings.env == Environment.TEST:
        if not settings.api_key:
            settings.api_key = "autoclaw-test-key"
        if not settings.internal_api_key:
            settings.internal_api_key = settings.api_key
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = load_settings()
    if settings.env == Environment.TEST:
        return settings

    if not settings.api_key:
        raise RuntimeError("AUTOCLAW_API_KEY is required for non-test environments")
    if not settings.internal_api_key:
        raise RuntimeError("AUTOCLAW_INTERNAL_API_KEY is required for non-test environments")
    return settings
