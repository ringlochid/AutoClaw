from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from app import cli
from app import config as config_module
from app.db.session import dispose_db_engine


@pytest.mark.asyncio
async def test_init_uses_data_dir_default_sqlite_path_and_runs_upgrade(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    expected_database_url = config_module.default_database_url(data_dir)

    monkeypatch.setitem(config_module.Settings.model_config, "env_file", None)
    monkeypatch.delenv("AUTOCLAW_CONFIG", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOCLAW_DATA_DIR", raising=False)
    monkeypatch.delenv("AUTOCLAW_API_KEY", raising=False)
    monkeypatch.delenv("AUTOCLAW_INTERNAL_API_KEY", raising=False)

    args = argparse.Namespace(
        config=str(config_path),
        data_dir=str(data_dir),
        database_url=None,
        sqlite_path=None,
        force=True,
        skip_bootstrap=True,
        skip_db_upgrade=False,
        revision="head",
        json=True,
    )

    try:
        result = await cli._cmd_init(args)
    finally:
        await dispose_db_engine()

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["config_path"] == str(config_path)
    assert payload["database_url"] == expected_database_url
    assert config_path.exists()
    assert data_dir.joinpath("autoclaw.db").exists()
    assert f'url = "{expected_database_url}"' in config_path.read_text(encoding="utf-8")
