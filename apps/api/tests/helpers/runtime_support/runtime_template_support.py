from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import autoclaw.interfaces.cli as cli
from autoclaw.config import get_settings
from autoclaw.interfaces.cli.commands.bootstrap import update_config_sections
from autoclaw.paths import default_database_path, default_database_url, ensure_runtime_dirs
from autoclaw.persistence.session import dispose_test_db_engine
from autoclaw.runtime.lifecycle import shutdown_runtime_lifecycle

_TEMPLATE_ROOT = Path(tempfile.gettempdir()) / "autoclaw-runtime-init-template-v3"
_TEMPLATE_READY_STAMP = _TEMPLATE_ROOT / ".ready"


@dataclass(frozen=True)
class RuntimeInitTemplate:
    config_path: Path
    data_dir: Path
    database_path: Path


async def initialize_runtime_from_template(
    *,
    config_path: Path,
    data_dir: Path,
    log_level: str,
    api_key: str,
    internal_api_key: str,
    host: str,
    port: int,
) -> None:
    await _reset_runtime_test_state()
    template = await ensure_runtime_init_template(
        log_level=log_level,
        api_key=api_key,
        internal_api_key=internal_api_key,
        host=host,
        port=port,
    )
    ensure_runtime_dirs(config_dir=config_path.parent, data_dir=data_dir)
    database_path = default_database_path(data_dir)
    if database_path.exists():
        database_path.unlink()
    await asyncio.to_thread(shutil.copy2, template.database_path, database_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(
        config_path.write_text,
        cli.settings_to_config_text(
            data_dir=data_dir,
            database_url=default_database_url(data_dir),
            host=host,
            port=port,
            log_level=log_level,
            api_key=api_key,
            internal_api_key=internal_api_key,
        ),
        encoding="utf-8",
    )
    await asyncio.to_thread(
        update_config_sections,
        config_path,
        section_updates={
            "openclaw": {
                "binary_path": sys.executable,
            },
            "runtime": {
                "dispatch_drain_timeout_seconds": 2,
                "watchdog_interval_seconds": 1,
            },
        },
    )
    get_settings.cache_clear()


async def _reset_runtime_test_state() -> None:
    await shutdown_runtime_lifecycle()
    await dispose_test_db_engine()


async def ensure_runtime_init_template(
    *,
    log_level: str,
    api_key: str,
    internal_api_key: str,
    host: str,
    port: int,
) -> RuntimeInitTemplate:
    config_path = _TEMPLATE_ROOT / "autoclaw-config.toml"
    data_dir = _TEMPLATE_ROOT / "autoclaw-data"
    database_path = default_database_path(data_dir)
    if _TEMPLATE_READY_STAMP.is_file() and database_path.is_file():
        return RuntimeInitTemplate(
            config_path=config_path,
            data_dir=data_dir,
            database_path=database_path,
        )

    if _TEMPLATE_ROOT.exists():
        shutil.rmtree(_TEMPLATE_ROOT)
    _TEMPLATE_ROOT.mkdir(parents=True, exist_ok=True)
    await cli.cmd_init(
        argparse.Namespace(
            config=str(config_path),
            data_dir=str(data_dir),
            database_url=None,
            host=host,
            port=port,
            log_level=log_level,
            api_key=api_key,
            internal_api_key=internal_api_key,
            force=True,
            skip_db_upgrade=False,
            json=False,
        )
    )
    await _reset_runtime_test_state()
    _TEMPLATE_READY_STAMP.write_text("ready\n", encoding="utf-8")
    return RuntimeInitTemplate(
        config_path=config_path,
        data_dir=data_dir,
        database_path=database_path,
    )


__all__ = [
    "RuntimeInitTemplate",
    "ensure_runtime_init_template",
    "initialize_runtime_from_template",
]
