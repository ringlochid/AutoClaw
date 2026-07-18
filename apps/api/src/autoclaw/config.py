from __future__ import annotations

import os
import re
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from autoclaw.definitions.contracts.workflow import ProviderKind
from autoclaw.paths import default_config_path, default_data_dir, default_database_url
from autoclaw.platform.environment import Environment

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_ENV_VAR = "AUTOCLAW_CONFIG"
DEFAULT_LOG_LEVEL = "WARNING"
DEFAULT_API_PORT = 18125
_ENV_FILE = REPO_ROOT / ".env"
ConfigText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ProviderConfigText = Annotated[str, StringConstraints(strip_whitespace=True)]
_POSTGRES_SCHEMA_PATTERN = re.compile(r"[a-z_][a-z0-9_$]{0,62}\Z")


class CodexSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    model: ProviderConfigText | None = None
    effort: ProviderConfigText | None = None


class ClaudeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    model: ProviderConfigText | None = None
    effort: ProviderConfigText | None = None


class OpenClawSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    gateway_url: ProviderConfigText = "ws://127.0.0.1:18789"
    gateway_profile: ProviderConfigText = "default"


class RuntimeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    default_provider: ProviderKind | None = None
    dispatch_launch_retry_initial_backoff_seconds: float = Field(default=1.0, ge=0.0)
    dispatch_launch_retry_max_backoff_seconds: float = Field(default=30.0, ge=0.0)
    watchdog_inactivity_timeout_seconds: int = Field(default=900, ge=1)
    watchdog_same_attempt_replacement_limit: int = Field(default=2, ge=0)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_prefix="AUTOCLAW_",
        env_nested_delimiter="__",
        extra="ignore",
        populate_by_name=True,
        serialize_by_alias=True,
    )

    env: Environment = Environment.DEVELOPMENT
    is_debug_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("debug", "is_debug_enabled"),
        serialization_alias="debug",
    )
    database_url: str = Field(default_factory=default_database_url)
    postgres_schema: ConfigText = "autoclaw"
    should_echo_database: bool = Field(
        default=False,
        validation_alias=AliasChoices("database_echo", "should_echo_database"),
        serialization_alias="database_echo",
    )
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
    codex: CodexSettings = Field(default_factory=CodexSettings)
    claude: ClaudeSettings = Field(default_factory=ClaudeSettings)
    openclaw: OpenClawSettings = Field(default_factory=OpenClawSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)

    @field_validator("postgres_schema")
    @classmethod
    def validate_postgres_schema(cls, value: str) -> str:
        if _POSTGRES_SCHEMA_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "postgres_schema must be a lowercase unquoted PostgreSQL identifier "
                "of at most 63 ASCII characters"
            )
        if value == "public" or value == "information_schema" or value.startswith("pg_"):
            raise ValueError("postgres_schema must name a dedicated non-system schema")
        return value

    @property
    def debug(self) -> bool:
        return self.is_debug_enabled

    @property
    def database_echo(self) -> bool:
        return self.should_echo_database

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
        del value_is_complex
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
    return settings


def load_settings() -> Settings:
    settings = Settings()
    debug_override = _environment_boolean_override("AUTOCLAW_DEBUG")
    if debug_override is not None:
        settings.is_debug_enabled = debug_override
    database_echo_override = _environment_boolean_override("AUTOCLAW_DATABASE_ECHO")
    if database_echo_override is not None:
        settings.should_echo_database = database_echo_override
    settings.config_path = _coerce_path(settings.config_path)
    settings.data_dir = _coerce_path(settings.data_dir)
    if "database_url" not in settings.model_fields_set:
        settings.database_url = default_database_url(settings.data_dir)
    if settings.env == Environment.TEST:
        if not settings.api_key:
            settings.api_key = "autoclaw-test-key"
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


def _environment_boolean_override(name: str) -> bool | None:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return None

    normalized_value = raw_value.strip().casefold()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a recognizable boolean value")


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
        "postgres_schema": ("database", "postgres_schema"),
        "database_echo": ("database", "echo"),
        "console_origins": ("server", "console_origins"),
        "api_host": ("server", "host"),
        "api_port": ("server", "port"),
        "log_level": ("logging", "level"),
        "api_key": ("security", "api_key"),
    }
    for field_name, key_path in field_mapping.items():
        value = _nested_get(payload, *key_path)
        if value is not None:
            loaded[field_name] = value
    for provider in ("codex", "claude", "openclaw"):
        if provider in payload:
            loaded[provider] = payload[provider]
    if "runtime" in payload:
        loaded["runtime"] = payload["runtime"]
    return loaded


__all__ = [
    "CONFIG_ENV_VAR",
    "DEFAULT_API_PORT",
    "DEFAULT_LOG_LEVEL",
    "ClaudeSettings",
    "CodexSettings",
    "Environment",
    "OpenClawSettings",
    "RuntimeSettings",
    "Settings",
    "TomlConfigSettingsSource",
    "get_settings",
    "load_settings",
]
