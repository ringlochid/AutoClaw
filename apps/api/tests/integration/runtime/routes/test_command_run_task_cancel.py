from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.persistence import (
    CommandRunModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    FlowWaitStateModel,
    PolicyRevisionModel,
    TaskEventModel,
)
from autoclaw.runtime.command_runs import start_command_run
from autoclaw.runtime.contracts import CommandRunStartRequest
from autoclaw.runtime.flow.timestamps import coerce_datetime_to_utc
from autoclaw.runtime.projection.runtime_state import current_runtime_state
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.runtime.routes.support import (
    RuntimeRouteContext,
    SeededRouteTask,
    launch_route_task,
    runtime_route_context,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]

_CONTROL_API_ACTOR_REF = "control_api"


def _command_run_start_payload() -> dict[str, object]:
    return {
        "command": "pytest apps/api/tests/unit/runtime -q",
        "description": "Run focused runtime unit tests.",
        "workdir": "apps/api",
        "timeout_seconds": 900,
    }


async def test_cancel_task_closes_active_command_run_wait_as_cancelled(
    tmp_path: Path,
) -> None:
    async with runtime_route_context(tmp_path) as context:
        task = await launch_route_task(
            context,
            task_id="task_control_command_run_cancelled",
            task_root_name="cancelled-command-run-task-root",
        )
        run_id = await start_route_command_run(context, task)

        cancel_response = await context.client.post(
            f"/runtime/tasks/{task.task_id}/cancel",
            headers=context.operator_headers,
            params={"expected_active_flow_revision_id": task.active_flow_revision_id},
        )

        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"
        async with context.session_factory() as session:
            command_run = await session.get(CommandRunModel, run_id)
            wait_state = await current_wait_state(session, task.task_id)
            cancelled_events = await command_run_events(
                session,
                task.task_id,
                "command_run_cancelled",
            )
            assert command_run is not None
            assert command_run.state == "cancelled"
            assert (
                command_run.terminal_summary
                == "command run cancelled because the task was cancelled"
            )
            assert command_run.cancellation_requested_at is not None
            assert command_run.cancellation_requested_by_actor_ref == _CONTROL_API_ACTOR_REF
            assert command_run.ended_at is not None
            assert wait_state is None
            assert len(cancelled_events) == 1
            cancelled_event = cancelled_events[0]
            assert cancelled_event.event_source == "control_api"
            assert cancelled_event.actor_ref == _CONTROL_API_ACTOR_REF
            assert cancelled_event.payload == {
                "run_id": run_id,
                "state": "cancelled",
                "summary": "command run cancelled because the task was cancelled",
                "exit_code": None,
                "signal": None,
                "ended_at": coerce_datetime_to_utc(command_run.ended_at).isoformat(),
                "log_ref": None,
                "initiated_by_actor_ref": _CONTROL_API_ACTOR_REF,
            }


async def start_route_command_run(
    context: RuntimeRouteContext,
    task: SeededRouteTask,
) -> str:
    await allow_command_run(context.session_factory, task_id=task.task_id)
    async with context.session_factory() as session:
        state = await current_runtime_state(session, task.task_id)
        dispatch = await session.get(DispatchTurnModel, task.current_open_dispatch_id)
        assert dispatch is not None
        response = await start_command_run(
            session,
            task_id=task.task_id,
            request=CommandRunStartRequest.model_validate(_command_run_start_payload()),
            state=state,
            dispatch=dispatch,
        )
        await session.commit()
        return response.run_id


async def allow_command_run(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        node = await session.scalar(
            select(FlowNodeModel).where(
                FlowNodeModel.flow_revision_id == flow.active_flow_revision_id,
                FlowNodeModel.node_key == flow.current_node_key,
            )
        )
        assert node is not None
        assert node.policy_key is not None
        assert node.policy_revision_no is not None
        policy_revision = await session.scalar(
            select(PolicyRevisionModel).where(
                PolicyRevisionModel.policy_key == node.policy_key,
                PolicyRevisionModel.revision_no == node.policy_revision_no,
            )
        )
        assert policy_revision is not None
        content = dict(policy_revision.content_json)
        raw_capabilities = content.get("capabilities")
        capabilities = dict(raw_capabilities) if isinstance(raw_capabilities, dict) else {}
        capabilities.setdefault("human_request", {"mode": "deny", "allowed_kinds": []})
        capabilities["command_run"] = "allow"
        content["capabilities"] = capabilities
        policy_revision.content_json = content
        await session.commit()


async def current_wait_state(session: AsyncSession, task_id: str) -> FlowWaitStateModel | None:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    if flow is None:
        return None
    return await session.get(FlowWaitStateModel, flow.flow_id)


async def command_run_events(
    session: AsyncSession,
    task_id: str,
    event_type: str,
) -> list[TaskEventModel]:
    return list(
        await session.scalars(
            select(TaskEventModel)
            .where(
                TaskEventModel.task_id == task_id,
                TaskEventModel.event_type == event_type,
            )
            .order_by(TaskEventModel.event_seq.asc())
        )
    )
