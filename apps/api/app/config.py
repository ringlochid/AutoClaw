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
        default="postgresql+asyncpg://autoclaw:autoclaw@localhost:5432/autoclaw"
    )
    openclaw_base_url: str = "http://127.0.0.1:18789"
    openclaw_account: str = "orin_a"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
