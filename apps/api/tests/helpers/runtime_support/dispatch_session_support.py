from __future__ import annotations

from typing import cast

from autoclaw.persistence import DispatchTurnModel, FlowModel, NodeSessionModel
from autoclaw.runtime.post_commit import drive_runtime_once, drive_runtime_until
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers.dispatch_wait_support import (
    commit_dispatch_wait_ok,
    mark_dispatch_provider_completed,
)
from tests.helpers.runtime_support.http_api_support import OPERATOR_HEADERS


async def current_session_key(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
) -> str:
    current_live_session_key: str | None = None

    async def live_session_ready() -> bool:
        nonlocal current_live_session_key
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            dispatch = await load_live_dispatch(session, task_id=task_id, flow=flow)
            session_key = await live_node_session_key_for_dispatch(session, dispatch=dispatch)
            if session_key is not None:
                current_live_session_key = session_key
                return True
        return False

    await drive_runtime_until(
        live_session_ready,
        task_id=task_id,
        max_cycles=40,
    )
    assert current_live_session_key is not None
    return current_live_session_key


async def current_session_key_after_dispatch_progress(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    client: AsyncClient,
    expected_active_flow_revision_id: str,
) -> str:
    progressed_session_key: str | None = None

    async def progressed_session_ready() -> bool:
        nonlocal progressed_session_key
        dispatch_id_to_progress: str | None = None
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            dispatch = await load_live_dispatch(session, task_id=task_id, flow=flow)
            session_key = await live_node_session_key_for_dispatch(session, dispatch=dispatch)
            if (
                dispatch is not None
                and dispatch.accepted_boundary is None
                and session_key is not None
                and dispatch.node_key == flow.current_node_key
            ):
                progressed_session_key = session_key
                return True
            if dispatch is not None and dispatch.accepted_boundary is not None:
                dispatch_id_to_progress = dispatch.dispatch_id
        if dispatch_id_to_progress is not None:
            await mark_dispatch_provider_completed(
                session_factory,
                dispatch_id=dispatch_id_to_progress,
            )
        resumed_key = await resume_live_dispatch_if_needed(
            session_factory=session_factory,
            task_id=task_id,
            client=client,
            expected_active_flow_revision_id=expected_active_flow_revision_id,
        )
        if resumed_key is not None:
            progressed_session_key = resumed_key
            return True
        return False

    await drive_runtime_until(
        progressed_session_ready,
        task_id=task_id,
        max_cycles=40,
    )
    assert progressed_session_key is not None
    return progressed_session_key


async def current_session_key_after_dispatch_progress_for_node(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    client: AsyncClient,
    expected_active_flow_revision_id: str,
    expected_node_key: str,
) -> str:
    progressed_session_key: str | None = None

    async def progressed_session_ready() -> bool:
        nonlocal progressed_session_key
        dispatch_id_to_progress: str | None = None
        async with session_factory() as session:
            flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
            assert flow is not None
            dispatch = await load_live_dispatch(session, task_id=task_id, flow=flow)
            session_key = await live_node_session_key_for_dispatch(session, dispatch=dispatch)
            if (
                flow.current_node_key == expected_node_key
                and dispatch is not None
                and dispatch.node_key == expected_node_key
                and dispatch.accepted_boundary is None
                and session_key is not None
            ):
                progressed_session_key = session_key
                return True
            if (
                dispatch is not None
                and dispatch.node_key != expected_node_key
                and dispatch.accepted_boundary is not None
            ):
                dispatch_id_to_progress = dispatch.dispatch_id
        if dispatch_id_to_progress is not None:
            await mark_dispatch_provider_completed(
                session_factory,
                dispatch_id=dispatch_id_to_progress,
            )
        await resume_live_dispatch_if_needed(
            session_factory=session_factory,
            task_id=task_id,
            client=client,
            expected_active_flow_revision_id=expected_active_flow_revision_id,
        )
        return False

    await drive_runtime_until(
        progressed_session_ready,
        task_id=task_id,
        max_cycles=40,
    )
    assert progressed_session_key is not None
    return progressed_session_key


async def resume_live_dispatch_if_needed(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    task_id: str,
    client: AsyncClient,
    expected_active_flow_revision_id: str,
) -> str | None:
    should_resume_paused_flow = False
    dispatch_id_to_progress: str | None = None
    await drive_runtime_once(task_id=task_id)
    async with session_factory() as session:
        flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
        assert flow is not None
        dispatch = await load_live_dispatch(session, task_id=task_id, flow=flow)
        session_key = await live_node_session_key_for_dispatch(session, dispatch=dispatch)
        if session_key is not None:
            return session_key
        if flow.status == "paused":
            if (
                flow.current_open_dispatch_id is not None
                and dispatch is not None
                and (
                    dispatch.accepted_boundary is not None
                    or dispatch.closed_at is not None
                    or dispatch.delivery_status in {"provider_completed", "provider_failed"}
                )
            ):
                dispatch_id_to_progress = dispatch.dispatch_id
                should_resume_paused_flow = True
            else:
                await drive_runtime_once(task_id=task_id)
                return None
        elif flow.current_open_dispatch_id is not None and dispatch is not None:
            if dispatch.accepted_boundary is not None or dispatch.closed_at is not None:
                dispatch_id_to_progress = dispatch.dispatch_id
            else:
                await drive_runtime_once(task_id=task_id)
                return None
        else:
            await drive_runtime_once(task_id=task_id)
            return None
    if dispatch_id_to_progress is not None:
        await continue_latest_dispatch(
            session_factory=session_factory,
            client=client,
            dispatch_id=dispatch_id_to_progress,
            task_id=task_id,
            expected_active_flow_revision_id=expected_active_flow_revision_id,
            should_resume_paused_flow=should_resume_paused_flow,
        )
    else:
        resumed = await client.post(
            f"/runtime/tasks/{task_id}/continue",
            headers=OPERATOR_HEADERS,
            params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
        )
        assert resumed.status_code == 200
    await drive_runtime_once(task_id=task_id)
    return None


async def continue_latest_dispatch(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    client: AsyncClient,
    dispatch_id: str,
    task_id: str,
    expected_active_flow_revision_id: str,
    should_resume_paused_flow: bool,
) -> None:
    await commit_dispatch_wait_ok(
        session_factory,
        dispatch_id=dispatch_id,
    )
    if should_resume_paused_flow:
        resumed = await client.post(
            f"/runtime/tasks/{task_id}/continue",
            headers=OPERATOR_HEADERS,
            params={"expected_active_flow_revision_id": expected_active_flow_revision_id},
        )
        assert resumed.status_code == 200


async def load_live_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
) -> DispatchTurnModel | None:
    dispatch_id = flow.current_open_dispatch_id
    if dispatch_id is not None:
        return await session.get(DispatchTurnModel, dispatch_id)
    return cast(
        DispatchTurnModel | None,
        await session.scalar(
            select(DispatchTurnModel)
            .where(
                DispatchTurnModel.task_id == task_id,
                DispatchTurnModel.control_state == "live",
                DispatchTurnModel.closed_at.is_(None),
            )
            .order_by(DispatchTurnModel.rendered_at.desc())
        ),
    )


async def live_node_session_key_for_dispatch(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel | None,
) -> str | None:
    if dispatch is None or dispatch.control_state != "live" or dispatch.closed_at is not None:
        return None
    return cast(
        str | None,
        await session.scalar(
            select(NodeSessionModel.session_key)
            .where(
                NodeSessionModel.dispatch_id == dispatch.dispatch_id,
                NodeSessionModel.session_status == "live",
                NodeSessionModel.closed_at.is_(None),
            )
            .order_by(NodeSessionModel.opened_at.desc())
            .limit(1)
        ),
    )


__all__ = [
    "continue_latest_dispatch",
    "current_session_key",
    "current_session_key_after_dispatch_progress",
    "current_session_key_after_dispatch_progress_for_node",
    "live_node_session_key_for_dispatch",
    "load_live_dispatch",
    "resume_live_dispatch_if_needed",
]
