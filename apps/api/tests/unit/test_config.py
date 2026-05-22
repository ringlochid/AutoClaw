from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest
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

[server]
console_origins = ["http://127.0.0.1:4173"]

[security]
api_key = "config-api-key"
internal_api_key = "config-internal-key"

[openclaw]
base_url = "http://127.0.0.1:18789"
gateway_token = "gateway-config-token"
agent_id = "worker-agent"
timeout_ms = 60000

[runtime]
dispatch_drain_timeout_seconds = 45
watchdog_enabled = false
watchdog_interval_seconds = 20
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
    monkeypatch.delenv("AUTOCLAW_API_KEY", raising=False)
    monkeypatch.delenv("AUTOCLAW_INTERNAL_API_KEY", raising=False)

    config_module = _reload_config_module()
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()

    assert settings.database_url == "sqlite+aiosqlite:////tmp/from-config.db"
    assert settings.console_origins == ["http://127.0.0.1:4173"]
    assert settings.api_key == "config-api-key"
    assert settings.internal_api_key == "config-internal-key"
    assert settings.config_path == config_path
    assert settings.data_dir == data_home / "autoclaw"
    assert settings.openclaw.base_url == "http://127.0.0.1:18789"
    assert settings.openclaw.gateway_token == "gateway-config-token"
    assert settings.openclaw.agent_id == "worker-agent"
    assert settings.openclaw.timeout_ms == 60000
    assert settings.runtime.dispatch_drain_timeout_seconds == 45
    assert settings.runtime.watchdog_enabled is False
    assert settings.runtime.watchdog_interval_seconds == 20


def test_env_overrides_config_file(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    config_path.write_text(
        """
[database]
url = "sqlite+aiosqlite:////tmp/from-config.db"

[server]
port = 8123

[security]
api_key = "config-api-key"
internal_api_key = "config-internal-key"

[openclaw]
base_url = "http://127.0.0.1:18789"
timeout_ms = 120000

[runtime]
watchdog_enabled = true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("AUTOCLAW_CONFIG", str(config_path))
    monkeypatch.setenv("AUTOCLAW_DATABASE_URL", "sqlite+aiosqlite:////tmp/from-env.db")
    monkeypatch.setenv("AUTOCLAW_API_KEY", "env-api-key")
    monkeypatch.setenv("AUTOCLAW_INTERNAL_API_KEY", "env-internal-key")
    monkeypatch.setenv("AUTOCLAW_API_PORT", "9001")
    monkeypatch.setenv("AUTOCLAW_OPENCLAW__BASE_URL", "https://gateway.example.test")
    monkeypatch.setenv("AUTOCLAW_RUNTIME__WATCHDOG_ENABLED", "false")
    monkeypatch.setenv("AUTOCLAW_RUNTIME__WATCHDOG_INTERVAL_SECONDS", "99")
    config_module = _reload_config_module()
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()

    assert settings.database_url == "sqlite+aiosqlite:////tmp/from-env.db"
    assert settings.api_key == "env-api-key"
    assert settings.internal_api_key == "env-internal-key"
    assert settings.api_port == 9001
    assert settings.config_path == config_path
    assert settings.openclaw.base_url == "https://gateway.example.test"
    assert settings.runtime.watchdog_enabled is False
    assert settings.runtime.watchdog_interval_seconds == 99


def test_removed_watchdog_keys_fail_fast(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    config_path.write_text(
        """
[security]
api_key = "config-api-key"
internal_api_key = "config-internal-key"

[runtime]
watchdog_stale_after_seconds = 123
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("AUTOCLAW_CONFIG", str(config_path))
    config_module = _reload_config_module()
    config_module.get_settings.cache_clear()

    with pytest.raises(Exception, match="watchdog_stale_after_seconds"):
        config_module.get_settings()


def test_watchdog_bootstrap_first_progress_timeout_accepts_canonical_name_and_alias(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    config_path.write_text(
        """
[security]
api_key = "config-api-key"
internal_api_key = "config-internal-key"

[runtime]
watchdog_bootstrap_first_progress_timeout_seconds = 77
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("AUTOCLAW_CONFIG", str(config_path))
    config_module = _reload_config_module()
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()
    assert settings.runtime.watchdog_bootstrap_first_progress_timeout_seconds == 77

    config_path.write_text(
        """
[security]
api_key = "config-api-key"
internal_api_key = "config-internal-key"

[runtime]
watchdog_bootstrap_ack_timeout_seconds = 88
""".strip()
        + "\n",
        encoding="utf-8",
    )
    config_module = _reload_config_module()
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()
    assert settings.runtime.watchdog_bootstrap_first_progress_timeout_seconds == 88
