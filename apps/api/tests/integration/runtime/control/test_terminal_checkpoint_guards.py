from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.integrations.openclaw.gateway.fixtures import agent_wait_fixture
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime import cancel_runtime_flow, pause_runtime_flow, runtime_flow_read
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import (
    bootstrap_parent_runtime,
    current_session_key,
    prepare_runtime_db,
    record_checkpoint,
    runtime_api_context,
    set_dispatch_drain_timeout,
)


@pytest.mark.asyncio
async def test_phase3_pause_rejects_terminal_checkpointed_attempt(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_pause_rejects_terminal_checkpoint"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-pause-terminal-checkpoint",
        )

        async with runtime_api_context(config_path) as api:
            session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            checkpoint = await record_checkpoint(
                api.client,
                task_id=task_id,
                session_key=session_key,
                checkpoint_kind="terminal",
                outcome="green",
                summary="Ready to close.",
                next_step="Emit green boundary.",
            )
            assert checkpoint.status_code == 200

            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                with pytest.raises(
                    ValueError,
                    match="pause is illegal after a terminal checkpoint",
                ):
                    await pause_runtime_flow(
                        session,
                        task_id,
                        expected_active_flow_revision_id=flow_read.active_flow_revision_id,
                    )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_phase3_cancel_rejects_terminal_checkpointed_attempt(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)
    set_dispatch_drain_timeout(config_path, timeout_seconds=30)
    task_root = tmp_path / "task-root"
    task_id = "task_phase3_cancel_rejects_terminal_checkpoint"

    try:
        openclaw_gateway_test_server.set_default_method_payload(
            "agent.wait",
            agent_wait_fixture(status="timeout"),
        )
        await bootstrap_parent_runtime(
            config_path=config_path,
            task_id=task_id,
            task_root=task_root,
            compiler_version="phase-3-control-cancel-terminal-checkpoint",
        )

        async with runtime_api_context(config_path) as api:
            session_key = await current_session_key(
                session_factory=api.session_factory,
                task_id=task_id,
            )
            checkpoint = await record_checkpoint(
                api.client,
                task_id=task_id,
                session_key=session_key,
                checkpoint_kind="terminal",
                outcome="green",
                summary="Ready to close.",
                next_step="Emit green boundary.",
            )
            assert checkpoint.status_code == 200

            async with api.session_factory() as session:
                flow_read = await runtime_flow_read(session, task_id)
                with pytest.raises(
                    ValueError,
                    match="cancel is illegal after a terminal checkpoint",
                ):
                    await cancel_runtime_flow(
                        session,
                        task_id,
                        expected_active_flow_revision_id=flow_read.active_flow_revision_id,
                    )
    finally:
        await dispose_db_engine()
