from __future__ import annotations

import argparse
from contextlib import nullcontext
from pathlib import Path

import app.registry.seeds as registry_seeds
import pytest
from app import cli
from app.db.session import dispose_db_engine


@pytest.mark.asyncio
async def test_init_fails_when_packaged_seed_definitions_are_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    empty_seed_root = tmp_path / "missing-packaged-definitions"
    empty_seed_root.mkdir()

    monkeypatch.setattr(
        registry_seeds.resources,
        "as_file",
        lambda _resource: nullcontext(empty_seed_root),
    )

    try:
        with pytest.raises(FileNotFoundError, match="missing seed definitions for 'roles'"):
            await cli.cmd_init(
                argparse.Namespace(
                    config=str(config_path),
                    data_dir=str(data_dir),
                    database_url=None,
                    host="127.0.0.1",
                    port=8123,
                    log_level="INFO",
                    api_key="api-test-key",
                    internal_api_key="internal-test-key",
                    force=True,
                    skip_db_upgrade=False,
                    json=False,
                )
            )
    finally:
        await dispose_db_engine()
