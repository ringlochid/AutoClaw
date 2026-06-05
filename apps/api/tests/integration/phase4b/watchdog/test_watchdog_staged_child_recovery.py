from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from autoclaw.persistence import (
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
)
from autoclaw.runtime import CheckpointKind, EgressBoundary
from autoclaw.runtime.boundary.service import accept_boundary
from autoclaw.runtime.checkpoint.recording import record_checkpoint
from autoclaw.runtime.contracts import (
    BoundaryWrite,
    CheckpointHandoffRead,
    CheckpointWrite,
    CheckpointWriteBody,
)
from autoclaw.runtime.watchdog.recovery import execute_watchdog_recovery
from sqlalchemy import select
from tests.integration.phase3.dispatch_support import current_open_dispatch_id
from tests.integration.phase3.runtime_support import assign_child, runtime_read_json
from tests.integration.phase4a.support import LocalGatewayTestServer
from tests.integration.phase4b.watchdog.case_support import configure_watchdog_env
from tests.integration.phase4b.watchdog.support import (
    Phase4BWatchdogContext,
    phase4b_watchdog_api,
)


async def _stage_parent_child_assignment(
    context: Phase4BWatchdogContext,
    *,
    child_node_key: str,
) -> tuple[str, str]:
    dispatch_id = await current_open_dispatch_id(
        context.api.session_factory,
        task_id=context.task_id,
    )
    runtime_payload = await runtime_read_json(context.api.client, context.task_id)
    async with context.api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == context.task_id))
        assert flow is not None
        assert flow.current_open_dispatch_id == dispatch_id
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        root_session_key = next(
            row.session_key
            for row in dispatch.node_sessions
            if row.session_status == "live" and row.closed_at is None
        )
    assign = await assign_child(
        context.api.client,
        task_id=context.task_id,
        session_key=root_session_key,
        child_node_key=child_node_key,
        active_flow_revision_id=runtime_payload["active_flow_revision_id"],
    )
    assert assign.status_code == 200
    async with context.api.session_factory() as session:
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        assert dispatch is not None
        staged_child_assignment_id = dispatch.staged_child_assignment_id
        assert isinstance(staged_child_assignment_id, str)
    return dispatch_id, staged_child_assignment_id


async def _seed_same_attempt_recovery_request(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
    stale_at: datetime,
) -> None:
    async with context.api.session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == context.task_id))
        dispatch = await session.get(DispatchTurnModel, dispatch_id)
        delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
        watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
        assert flow is not None
        assert dispatch is not None
        assert delivery_state is not None
        assert watchdog_state is not None
        flow.current_open_dispatch_id = None
        dispatch.control_state = "fenced"
        dispatch.fenced_at = stale_at
        dispatch.closed_at = stale_at
        dispatch.delivery_status = "provider_failed"
        delivery_state.transport_state = "provider_failed"
        delivery_state.last_controller_progress_at = stale_at
        delivery_state.last_controller_terminal_at = stale_at
        delivery_state.updated_at = stale_at
        watchdog_state.watchdog_state = "classified"
        watchdog_state.current_watchdog_kind = "execution_running.execution_stale"
        watchdog_state.current_watchdog_reason = "test recovery path"
        watchdog_state.recovery_action = "redispatch_same_attempt"
        watchdog_state.recovery_reason = "test recovery path"
        watchdog_state.recovery_dispatch_id = None
        watchdog_state.updated_at = stale_at
        await session.commit()


async def _replacement_dispatch_id(
    context: Phase4BWatchdogContext,
    *,
    dispatch_id: str,
) -> str:
    async with context.api.session_factory() as session:
        watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
        assert watchdog_state is not None
        replacement_dispatch_id = watchdog_state.recovery_dispatch_id
        assert isinstance(replacement_dispatch_id, str)
        return replacement_dispatch_id


async def _assert_checkpoint_and_yield_after_recovery(
    context: Phase4BWatchdogContext,
    *,
    replacement_dispatch_id: str,
) -> None:
    async with context.api.session_factory() as session:
        replacement_dispatch = await session.get(DispatchTurnModel, replacement_dispatch_id)
        assert replacement_dispatch is not None
        checkpoint = await record_checkpoint(
            session,
            context.task_id,
            CheckpointWrite(
                checkpoint=CheckpointWriteBody(
                    checkpoint_kind=CheckpointKind.PROGRESS,
                    handoff=CheckpointHandoffRead(
                        summary="Recovered parent dispatch is ready to yield the staged child.",
                        next_step="Emit yield for the staged child assignment.",
                    ),
                )
            ),
        )
        yielded = await accept_boundary(
            session,
            context.task_id,
            BoundaryWrite(boundary=EgressBoundary.YIELD),
        )
        await session.commit()
        assert checkpoint.attempt_id == replacement_dispatch.attempt_id
        assert yielded.accepted_boundary == EgressBoundary.YIELD
        assert yielded.flow.current_node_key == "implementation_subtree"


@pytest.mark.asyncio
async def test_phase4b_watchdog_preserves_valid_parent_staged_child_basis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    configure_watchdog_env(
        monkeypatch,
        bootstrap_timeout_seconds=300,
        execution_stale_after_seconds=1,
    )

    async with phase4b_watchdog_api(
        tmp_path,
        task_id="task_phase4b_watchdog_parent_staged_child_recovery",
        compiler_version="phase-4b-watchdog-parent-staged-child-recovery",
        openclaw_gateway_test_server=openclaw_gateway_test_server,
    ) as context:
        dispatch_id, staged_child_assignment_id = await _stage_parent_child_assignment(
            context,
            child_node_key="implementation_subtree",
        )
        stale_at = datetime.now(tz=UTC) - timedelta(seconds=5)
        await _seed_same_attempt_recovery_request(
            context,
            dispatch_id=dispatch_id,
            stale_at=stale_at,
        )

        changed = await execute_watchdog_recovery(
            context.api.session_factory,
            task_id=context.task_id,
            dispatch_id=dispatch_id,
        )
        assert changed is True
        replacement_dispatch_id = await _replacement_dispatch_id(
            context,
            dispatch_id=dispatch_id,
        )

        async with context.api.session_factory() as session:
            replacement_dispatch = await session.get(DispatchTurnModel, replacement_dispatch_id)
            assert replacement_dispatch is not None
            assert replacement_dispatch.previous_dispatch_id == dispatch_id
            assert replacement_dispatch.staged_child_assignment_id == staged_child_assignment_id

        await _assert_checkpoint_and_yield_after_recovery(
            context,
            replacement_dispatch_id=replacement_dispatch_id,
        )
