from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import Environment

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_prefix="AUTOCLAW_",
        extra="ignore",
    )

    env: Environment = Environment.DEVELOPMENT
    debug: bool = False
    app_name: str = "autoclaw"
    database_url: str = Field(
        default="postgresql+asyncpg://autoclaw:autoclaw@localhost:5433/autoclaw"
    )
    openclaw_base_url: str = "http://127.0.0.1:18789"
    openclaw_account: str = "orin_a"
    console_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ]
    )
    api_key: str = ""
    internal_api_key: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    if settings.env == Environment.TEST:
        if not settings.api_key:
            settings.api_key = "autoclaw-test-key"
        if not settings.internal_api_key:
            settings.internal_api_key = settings.api_key
        return settings

    if not settings.api_key:
        raise RuntimeError("AUTOCLAW_API_KEY is required for non-test environments")
    if not settings.internal_api_key:
        raise RuntimeError("AUTOCLAW_INTERNAL_API_KEY is required for non-test environments")
    return settings
