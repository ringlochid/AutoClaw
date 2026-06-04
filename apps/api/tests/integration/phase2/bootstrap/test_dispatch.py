from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app import cli
from app.config import get_settings
from app.db import DispatchDeliveryStateModel, DispatchTurnModel
from app.db.session import dispose_db_engine, get_session_factory
from app.runtime.ids import dispatch_id_for_task
from autoclaw.runtime import PromptSendMode
from autoclaw.runtime.projection import materialize_dispatch_files, render_dispatch_prompt
from tests.integration.phase2.bootstrap.fixtures import (
    persist_bootstrap_runtime,
    seed_dispatch,
)


async def test_launch_materializes_dispatch_files_for_full_prompt_dispatch(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_dispatch_materialization"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    try:
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

        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-dispatch-proof",
                )
                await seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.FULL_PROMPT,
                )
                await materialize_dispatch_files(session, task_id, dispatch_id)

        dispatch_dir = task_root / "_runtime" / "dispatch" / dispatch_id
        prompt_path = dispatch_dir / "prompt.md"
        prompt_request_path = dispatch_dir / "prompt-request.json"
        delivery_state_path = dispatch_dir / "delivery-state.json"
        continuity_state_path = dispatch_dir / "continuity-state.json"
        watchdog_state_path = dispatch_dir / "watchdog-state.json"
        provider_events_path = dispatch_dir / "provider-events.ndjson"

        assert prompt_path.is_file()
        assert prompt_request_path.is_file()
        assert delivery_state_path.is_file()
        assert continuity_state_path.is_file()
        assert watchdog_state_path.is_file()
        assert provider_events_path.is_file()

        full_prompt_request = json.loads(prompt_request_path.read_text(encoding="utf-8"))
        assert full_prompt_request["send_mode"] == "full_prompt"
        assert full_prompt_request["instructions_text"] is not None
        assert "## Operating Model" in prompt_path.read_text(encoding="utf-8")
        assert provider_events_path.read_text(encoding="utf-8") == ""
    finally:
        await dispose_db_engine()


async def test_materialize_dispatch_files_persists_raw_delivery_state_truth(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_raw_delivery_state"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)
    terminal_at = datetime.now(tz=UTC) - timedelta(seconds=7)

    try:
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

        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-raw-delivery-state",
                )
                await seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.FULL_PROMPT,
                )
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
                assert dispatch is not None
                assert delivery_state is not None

                dispatch.accepted_boundary = "yield"
                delivery_state.transport_state = "provider_completed"
                delivery_state.last_controller_terminal_at = terminal_at
                await session.flush()

                await materialize_dispatch_files(session, task_id, dispatch_id)

        delivery_state_payload = json.loads(
            (task_root / "_runtime" / "dispatch" / dispatch_id / "delivery-state.json").read_text(
                encoding="utf-8"
            )
        )
        assert delivery_state_payload["transport_state"] == "provider_completed"
        assert delivery_state_payload["last_controller_terminal_at"] == terminal_at.isoformat()
    finally:
        await dispose_db_engine()


async def test_render_dispatch_prompt_persists_full_prompt_request_for_dispatch(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_full_prompt_render"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    try:
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

        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-full-prompt-render",
                )
                await seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.FULL_PROMPT,
                )
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None

                bundle, record = await render_dispatch_prompt(session, task_id, dispatch)

        prompt_request = json.loads(record.transport_request_path.read_text(encoding="utf-8"))
        assert bundle.instructions_text is not None
        assert record.transport_request.instructions_text is not None
        assert prompt_request["send_mode"] == "full_prompt"
        assert "previous_response_id" not in prompt_request
        assert prompt_request["instructions_text"] == bundle.instructions_text
        assert prompt_request["input_text"] == bundle.input_text
        assert prompt_request["transport_request_hash"] == record.transport_request_hash
        assert "## Operating Model" in bundle.input_text
    finally:
        await dispose_db_engine()


async def test_render_dispatch_prompt_stays_full_prompt_without_legacy_transport_inputs(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "autoclaw-config.toml"
    data_dir = tmp_path / "autoclaw-data"
    task_root = tmp_path / "task-root"
    task_id = "task_phase2_same_session_legacy_dispatch"
    dispatch_id = dispatch_id_for_task(task_id, "root", 1)

    try:
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

        with cli.command_env(config_path=config_path):
            get_settings.cache_clear()
            session_factory = get_session_factory()

            async with session_factory() as session:
                await persist_bootstrap_runtime(
                    session,
                    task_id=task_id,
                    task_root=task_root,
                    compiler_version="phase-2-same-session-legacy-dispatch",
                )
                await seed_dispatch(
                    session,
                    task_id=task_id,
                    dispatch_id=dispatch_id,
                    send_mode=PromptSendMode.FULL_PROMPT,
                )
                dispatch = await session.get(DispatchTurnModel, dispatch_id)
                assert dispatch is not None

                bundle, record = await render_dispatch_prompt(session, task_id, dispatch)

        prompt_request = json.loads(record.transport_request_path.read_text(encoding="utf-8"))
        assert bundle.send_mode == PromptSendMode.FULL_PROMPT
        assert record.send_mode == PromptSendMode.FULL_PROMPT
        assert prompt_request["send_mode"] == "full_prompt"
        assert "previous_response_id" not in prompt_request
    finally:
        await dispose_db_engine()
