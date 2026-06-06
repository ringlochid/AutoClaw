from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import autoclaw.interfaces.cli as cli
from autoclaw.config import get_settings
from autoclaw.persistence.session import dispose_db_engine, get_session_factory
from autoclaw.runtime.lifecycle import shutdown_runtime_lifecycle
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers.runtime_support.runtime_config_support import (
    set_dispatch_drain_timeout,
)
from tests.helpers.runtime_support.runtime_template_support import (
    initialize_runtime_from_template,
)


@dataclass(frozen=True)
class RuntimeBootstrapPaths:
    config_path: Path
    data_dir: Path
    task_root: Path


@dataclass(frozen=True)
class RuntimeBootstrapContext:
    paths: RuntimeBootstrapPaths
    session_factory: async_sessionmaker[AsyncSession]


def runtime_bootstrap_paths(tmp_path: Path) -> RuntimeBootstrapPaths:
    return RuntimeBootstrapPaths(
        config_path=tmp_path / "autoclaw-config.toml",
        data_dir=tmp_path / "autoclaw-data",
        task_root=tmp_path / "task-root",
    )


def runtime_bootstrap_init_args(paths: RuntimeBootstrapPaths) -> argparse.Namespace:
    return argparse.Namespace(
        config=str(paths.config_path),
        data_dir=str(paths.data_dir),
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


@asynccontextmanager
async def runtime_bootstrap_context(
    tmp_path: Path,
    *,
    dispatch_drain_timeout_seconds: int | None = None,
    quiet_init: bool = False,
    init_log_level: str | None = None,
) -> AsyncIterator[RuntimeBootstrapContext]:
    del quiet_init

    paths = runtime_bootstrap_paths(tmp_path)
    get_settings.cache_clear()
    await shutdown_runtime_lifecycle()
    await dispose_db_engine()
    init_args = runtime_bootstrap_init_args(paths)
    if init_log_level is not None:
        init_args.log_level = init_log_level
    await initialize_runtime_from_template(
        config_path=paths.config_path,
        data_dir=paths.data_dir,
        log_level=init_args.log_level,
        api_key=init_args.api_key,
        internal_api_key=init_args.internal_api_key,
        host=init_args.host,
        port=init_args.port,
    )
    if dispatch_drain_timeout_seconds is not None:
        set_dispatch_drain_timeout(
            paths.config_path,
            timeout_seconds=dispatch_drain_timeout_seconds,
        )
    try:
        with cli.command_env(config_path=paths.config_path):
            get_settings.cache_clear()
            yield RuntimeBootstrapContext(
                paths=paths,
                session_factory=get_session_factory(),
            )
    finally:
        get_settings.cache_clear()
        await shutdown_runtime_lifecycle()
        await dispose_db_engine()


__all__ = [
    "RuntimeBootstrapContext",
    "RuntimeBootstrapPaths",
    "runtime_bootstrap_context",
    "runtime_bootstrap_init_args",
    "runtime_bootstrap_paths",
]
