from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

from pytest import MonkeyPatch


def _reload_config_module() -> ModuleType:
    from app import config as config_module

    return importlib.reload(config_module)


def test_get_settings_reads_default_platform_config(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_home = tmp_path / "config-home"
    data_home = tmp_path / "data-home"
    state_home = tmp_path / "state-home"
    cache_home = tmp_path / "cache-home"
    config_path = config_home / "autoclaw" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
[database]
url = "sqlite+aiosqlite:////tmp/from-config.db"

[openclaw]
base_url = "http://127.0.0.1:19999"
agent_id = "config-agent"

[server]
console_origins = ["http://127.0.0.1:4173"]

[security]
api_key = "config-api-key"
internal_api_key = "config-internal-key"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))
    monkeypatch.delenv("AUTOCLAW_CONFIG", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOCLAW_OPENCLAW_BASE_URL", raising=False)
    monkeypatch.delenv("AUTOCLAW_OPENCLAW_AGENT_ID", raising=False)
    monkeypatch.delenv("AUTOCLAW_API_KEY", raising=False)
    monkeypatch.delenv("AUTOCLAW_INTERNAL_API_KEY", raising=False)

    config_module = _reload_config_module()
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()

    assert settings.database_url == "sqlite+aiosqlite:////tmp/from-config.db"
    assert settings.openclaw_base_url == "http://127.0.0.1:19999"
    assert settings.openclaw_agent_id == "config-agent"
    assert settings.console_origins == ["http://127.0.0.1:4173"]
    assert settings.api_key == "config-api-key"
    assert settings.internal_api_key == "config-internal-key"
    assert settings.config_path == config_path
    assert settings.data_dir == data_home / "autoclaw"


def test_env_overrides_config_file(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    config_path.write_text(
        """
[database]
url = "sqlite+aiosqlite:////tmp/from-config.db"

[security]
api_key = "config-api-key"
internal_api_key = "config-internal-key"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("AUTOCLAW_CONFIG", str(config_path))
    monkeypatch.setenv("AUTOCLAW_DATABASE_URL", "sqlite+aiosqlite:////tmp/from-env.db")
    monkeypatch.setenv("AUTOCLAW_API_KEY", "env-api-key")
    monkeypatch.setenv("AUTOCLAW_INTERNAL_API_KEY", "env-internal-key")

    config_module = _reload_config_module()
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()

    assert settings.database_url == "sqlite+aiosqlite:////tmp/from-env.db"
    assert settings.api_key == "env-api-key"
    assert settings.internal_api_key == "env-internal-key"
    assert settings.config_path == config_path
