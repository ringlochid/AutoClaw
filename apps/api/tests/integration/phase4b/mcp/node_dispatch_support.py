from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.db import (
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowModel,
    NodeSessionModel,
)
from app.runtime import PromptSendMode
from app.runtime.control.dispatch.provider_events import append_provider_event
from app.runtime.effects import commit_runtime_session, stage_dispatch_open_outputs
from autoclaw.openclaw.bindings import NodeToolContext, load_current_node_tool_context
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.integration.phase2.bootstrap.fixtures import persist_bootstrap_runtime, seed_dispatch


async def seed_live_node_mcp_dispatch(
    session_factory: async_sessionmaker,
    *,
    task_id: str,
    task_root: Path,
    compiler_version: str = "phase-4b-node-mcp-stale-authority",
    bootstrap_runtime: bool = True,
    dispatch_id: str | None = None,
) -> NodeToolContext:
    async with session_factory() as session:
        if bootstrap_runtime:
            await persist_bootstrap_runtime(
                session,
                task_id=task_id,
                task_root=task_root,
                compiler_version=compiler_version,
            )
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        dispatch_count = await session.scalar(
            select(func.count(DispatchTurnModel.dispatch_id)).where(
                DispatchTurnModel.task_id == task_id
            )
        )
        next_dispatch_id = dispatch_id or (
            f"dispatch.{task_id}.{flow.current_node_key}.{int(dispatch_count or 0) + 1:02d}"
        )
        dispatch = await seed_dispatch(
            session,
            task_id=task_id,
            dispatch_id=next_dispatch_id,
            send_mode=PromptSendMode.FULL_PROMPT,
        )
        delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
        assert delivery_state is not None
        flow.status = "running"
        flow.current_open_dispatch_id = dispatch.dispatch_id
        dispatch.gateway_session_key = f"gateway-session.{dispatch.dispatch_id}"
        delivery_state.accepted_at = dispatch.rendered_at
        assert dispatch.attempt_id is not None
        session.add(
            NodeSessionModel(
                node_session_id=f"node-session.{dispatch.dispatch_id}",
                flow_node_id=dispatch.flow_node_id,
                assignment_id=dispatch.assignment_id,
                attempt_id=dispatch.attempt_id,
                dispatch_id=dispatch.dispatch_id,
                session_key=dispatch.gateway_session_key,
                session_status="live",
                opened_at=dispatch.rendered_at,
            )
        )
        await append_provider_event(
            session,
            dispatch=dispatch,
            attempt_id=dispatch.attempt_id,
            event_source="adapter",
            event_kind="accepted",
            summary="Dispatch accepted and waiting for provider or adapter progress.",
            detail=f"Dispatch opened for node '{dispatch.node_key}'.",
        )
        stage_dispatch_open_outputs(
            session,
            task_id=task_id,
            dispatch_id=dispatch.dispatch_id,
        )
        await commit_runtime_session(session)
    return await load_current_node_tool_context(task_id)


async def seed_node_mcp_session_pair(
    session_factory: async_sessionmaker,
    tmp_path: Path,
    *,
    task_a_id: str,
    task_b_id: str,
    compiler_stem: str,
) -> tuple[NodeToolContext, NodeToolContext]:
    return (
        await seed_live_node_mcp_dispatch(
            session_factory,
            task_id=task_a_id,
            task_root=tmp_path / "task-a-root",
            compiler_version=f"{compiler_stem}-a",
        ),
        await seed_live_node_mcp_dispatch(
            session_factory,
            task_id=task_b_id,
            task_root=tmp_path / "task-b-root",
            compiler_version=f"{compiler_stem}-b",
        ),
    )


async def revoke_same_dispatch_node_session(
    session_factory: async_sessionmaker,
    *,
    task_id: str,
    context: NodeToolContext,
    flow_status: str,
    control_state: str,
    control_state_reason: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        current_dispatch = await session.get(DispatchTurnModel, context.dispatch_id)
        node_session = await session.get(NodeSessionModel, context.node_session_id)
        assert flow is not None
        assert current_dispatch is not None
        assert node_session is not None
        flow.status = flow_status
        flow.current_open_dispatch_id = context.dispatch_id
        current_dispatch.control_state = control_state
        current_dispatch.control_state_reason = control_state_reason
        if flow_status == "running" and control_state == "live":
            node_session.session_status = "revoked"
            node_session.closed_at = datetime.now(tz=UTC)
        await session.commit()


async def assert_same_dispatch_node_session_state(
    session_factory: async_sessionmaker,
    *,
    task_id: str,
    context: NodeToolContext,
    flow_status: str,
    control_state: str,
) -> None:
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        current_dispatch = await session.get(DispatchTurnModel, context.dispatch_id)
        node_session = await session.get(NodeSessionModel, context.node_session_id)
        assert flow is not None
        assert current_dispatch is not None
        assert node_session is not None
        assert flow.current_open_dispatch_id == context.dispatch_id
        assert flow.status == flow_status
        assert current_dispatch.control_state == control_state
        if flow_status == "running" and control_state == "live":
            assert node_session.session_status == "revoked"
            assert node_session.closed_at is not None


__all__ = [
    "assert_same_dispatch_node_session_state",
    "revoke_same_dispatch_node_session",
    "seed_live_node_mcp_dispatch",
    "seed_node_mcp_session_pair",
]
