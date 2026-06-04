from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from app.core.enums import Environment
from app.paths import default_config_path, default_data_dir, default_database_url

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_ENV_VAR = "AUTOCLAW_CONFIG"
DEFAULT_LOG_LEVEL = "WARNING"
DEFAULT_API_PORT = 18125
_ENV_FILE = REPO_ROOT / ".env"


class OpenClawSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    base_url: str = "http://127.0.0.1:18789"
    gateway_token: str = ""
    gateway_password: str = ""
    config_path: str = ""
    binary_path: str = ""
    agent_id: str = "autoclaw-worker"
    operator_agent_id: str = ""
    timeout_ms: int = 120000


class RuntimeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dispatch_drain_timeout_seconds: int = 30
    watchdog_enabled: bool = True
    watchdog_interval_seconds: int = 15
    watchdog_execution_stale_after_seconds: int = 300
    watchdog_bootstrap_first_progress_timeout_seconds: int = Field(
        default=120,
        validation_alias=AliasChoices(
            "watchdog_bootstrap_first_progress_timeout_seconds",
            "watchdog_bootstrap_ack_timeout_seconds",
        ),
    )
    watchdog_same_attempt_redispatch_limit: int = 2
    watchdog_auto_recover: bool = True
    watchdog_max_flows_per_tick: int = 50
    watchdog_max_auto_recoveries_per_tick: int = 10


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_prefix="AUTOCLAW_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    env: Environment = Environment.DEVELOPMENT
    debug: bool = False
    database_url: str = Field(default_factory=default_database_url)
    database_echo: bool = False
    console_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ]
    )
    api_host: str = "127.0.0.1"
    api_port: int = DEFAULT_API_PORT
    log_level: str = DEFAULT_LOG_LEVEL
    config_path: Path = Field(default_factory=default_config_path)
    data_dir: Path = Field(default_factory=default_data_dir)
    api_key: str = ""
    internal_api_key: str = ""
    openclaw: OpenClawSettings = Field(default_factory=OpenClawSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)

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


def load_settings() -> Settings:
    settings = Settings()
    settings.config_path = _coerce_path(settings.config_path)
    settings.data_dir = _coerce_path(settings.data_dir)
    if "database_url" not in settings.model_fields_set:
        settings.database_url = default_database_url(settings.data_dir)
    if settings.env == Environment.TEST:
        if not settings.api_key:
            settings.api_key = "autoclaw-test-key"
        if not settings.internal_api_key:
            settings.internal_api_key = settings.api_key
    return settings


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
    config_path = _coerce_path(os.environ.get(CONFIG_ENV_VAR, default_config_path()))
    if not config_path.is_file():
        return {"config_path": config_path, "data_dir": default_data_dir()}

    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    loaded: dict[str, Any] = {
        "config_path": config_path,
        "data_dir": _coerce_path(_nested_get(payload, "paths", "data_dir") or default_data_dir()),
    }

    field_mapping = {
        "database_url": ("database", "url"),
        "database_echo": ("database", "echo"),
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
    if isinstance(payload.get("openclaw"), dict):
        loaded["openclaw"] = {
            key: value
            for key, value in payload["openclaw"].items()
            if key not in {"internal_api_key", "account"}
        }
    if isinstance(payload.get("runtime"), dict):
        loaded["runtime"] = payload["runtime"]
    return loaded


__all__ = [
    "CONFIG_ENV_VAR",
    "DEFAULT_API_PORT",
    "DEFAULT_LOG_LEVEL",
    "Environment",
    "OpenClawSettings",
    "RuntimeSettings",
    "Settings",
    "TomlConfigSettingsSource",
    "get_settings",
    "load_settings",
]
