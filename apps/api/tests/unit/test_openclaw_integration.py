from __future__ import annotations

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from app.config import Settings
from app.integrations.openclaw import OpenClawConfigurationError, create_openclaw_client


@pytest.fixture
def base_settings() -> Settings:
    return Settings.model_construct(
        openclaw_gateway_token="",
        openclaw_base_url="http://127.0.0.1:18789",
        openclaw_agent_id="autoclaw-worker",
        openclaw_timeout_ms=20_000,
        api_key="autoclaw-operator-test-key",
        internal_api_key="autoclaw-internal-test-key",
    )


def test_create_openclaw_client_prefers_explicit_autoclaw_token(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "from-openclaw-env")
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "from-autoclaw-config"

    client = create_openclaw_client(base_settings)

    assert client.gateway_token == "from-autoclaw-config"


def test_create_openclaw_client_falls_back_to_openclaw_gateway_env(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "from-openclaw-env")
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "__OPENCLAW_REDACTED__"

    client = create_openclaw_client(base_settings)

    assert client.gateway_token == "from-openclaw-env"


def test_create_openclaw_client_falls_back_to_openclaw_config(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    config_path = tmp_path / "openclaw.json"
    config_path.write_text('{"gateway":{"auth":{"token":"from-openclaw-config"}}}')
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(config_path))
    base_settings.openclaw_gateway_token = "__OPENCLAW_REDACTED__"

    client = create_openclaw_client(base_settings)

    assert client.gateway_token == "from-openclaw-config"


def test_create_openclaw_client_raises_when_no_token_source_exists(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    base_settings: Settings,
) -> None:
    monkeypatch.delenv("OPENCLAW_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    base_settings.openclaw_gateway_token = "__OPENCLAW_REDACTED__"

    with pytest.raises(OpenClawConfigurationError):
        create_openclaw_client(base_settings)
