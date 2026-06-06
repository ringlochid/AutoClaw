from __future__ import annotations

from pathlib import Path

import autoclaw.interfaces.cli as cli
import pytest
from autoclaw.config import get_settings
from autoclaw.runtime.post_commit import start_runtime_effect_runner
from autoclaw.runtime.post_commit import worker as runtime_worker
from autoclaw.runtime.watchdog import manager as watchdog_manager
from autoclaw.runtime.watchdog import start_runtime_watchdog
from tests.helpers.runtime_support import (
    initialize_runtime_from_template,
    runtime_bootstrap_context,
)
from tests.integration.bootstrap.fixtures import (
    compile_workflow_fixture,
    load_seeded_lookup,
    load_workflow_definition,
    persist_bootstrap_runtime,
    seed_child_terminal_retry_checkpoint,
    seed_dispatch,
    task_compose_payload,
)

__all__ = [
    "compile_workflow_fixture",
    "load_seeded_lookup",
    "load_workflow_definition",
    "persist_bootstrap_runtime",
    "seed_child_terminal_retry_checkpoint",
    "seed_dispatch",
    "task_compose_payload",
]


def test_task_compose_payload_smoke() -> None:
    payload = task_compose_payload("minimal-implement-change")

    assert payload.workflow.key == "minimal-implement-change"
    assert payload.task.key == "auth-refresh-hardening"


@pytest.mark.asyncio
async def test_runtime_bootstrap_reset_clears_lifecycle_managers(tmp_path: Path) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    await initialize_runtime_from_template(
        config_path=config_path,
        data_dir=data_dir,
        log_level="WARNING",
        api_key="api-test-key",
        internal_api_key="internal-test-key",
        host="127.0.0.1",
        port=8123,
    )

    with cli.command_env(config_path=config_path):
        get_settings.cache_clear()
        await start_runtime_effect_runner()
        await start_runtime_watchdog()
        assert len(runtime_worker._MANAGER_BY_LOOP) == 1
        assert len(watchdog_manager._MANAGER_BY_LOOP) == 1

    async with runtime_bootstrap_context(tmp_path):
        assert len(runtime_worker._MANAGER_BY_LOOP) == 0
        assert len(watchdog_manager._MANAGER_BY_LOOP) == 0

    assert len(runtime_worker._MANAGER_BY_LOOP) == 0
    assert len(watchdog_manager._MANAGER_BY_LOOP) == 0
