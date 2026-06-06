from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from autoclaw.persistence import DispatchTurnModel, FlowModel, ProviderEventRecordModel
from autoclaw.runtime.dispatch.provider_events import append_provider_event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.helpers.openclaw_gateway_support import LocalGatewayTestServer
from tests.helpers.runtime_support import runtime_bootstrap_context
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload


async def _load_current_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
) -> DispatchTurnModel:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    assert flow is not None
    assert flow.current_open_dispatch_id is not None
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
    assert dispatch is not None
    assert dispatch.attempt_id is not None
    return dispatch


async def _append_event_with_deferred_commit(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    event_kind: str,
    summary: str,
    detail: str,
    flushed: asyncio.Event | None = None,
    release: asyncio.Event | None = None,
) -> int:
    async with session_factory() as session:
        dispatch = await _load_current_dispatch(session, task_id=task_id)
        attempt_id = dispatch.attempt_id
        assert attempt_id is not None
        row = await append_provider_event(
            session,
            dispatch=dispatch,
            attempt_id=attempt_id,
            event_source="adapter",
            event_kind=event_kind,
            summary=summary,
            detail=detail,
        )
        if flushed is not None:
            flushed.set()
        if release is not None:
            await release.wait()
        await session.commit()
        return row.event_no


@pytest.mark.asyncio
async def test_concurrent_provider_event_appends_use_unique_monotonic_event_numbers(
    tmp_path: Path,
    openclaw_gateway_test_server: LocalGatewayTestServer,
) -> None:
    task_id = "task_phase4a_provider_event_concurrency"

    async with runtime_bootstrap_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("minimal-implement-change"),
                compiler_version="phase-4a-provider-event-concurrency",
            )
            await session.commit()

        async with runtime.session_factory() as session:
            dispatch = await _load_current_dispatch(session, task_id=task_id)
            starting_event_nos = list(
                await session.scalars(
                    select(ProviderEventRecordModel.event_no)
                    .where(ProviderEventRecordModel.dispatch_id == dispatch.dispatch_id)
                    .order_by(ProviderEventRecordModel.event_no.asc())
                )
            )
            dispatch_id = dispatch.dispatch_id

        first_writer_flushed = asyncio.Event()
        race_release = asyncio.Event()
        expected_first_new_event_no = (starting_event_nos[-1] if starting_event_nos else 0) + 1

        first_task = asyncio.create_task(
            _append_event_with_deferred_commit(
                runtime.session_factory,
                task_id=task_id,
                event_kind="tool_event",
                summary="First concurrent provider-event append reserved an event number.",
                detail="Hold the first writer open until the second writer attempts its append.",
                flushed=first_writer_flushed,
                release=race_release,
            )
        )
        await first_writer_flushed.wait()
        second_task = asyncio.create_task(
            _append_event_with_deferred_commit(
                runtime.session_factory,
                task_id=task_id,
                event_kind="response_completed",
                summary="Second concurrent provider-event append reserved the next event number.",
                detail="This append starts before the first writer commits its transaction.",
            )
        )
        await asyncio.sleep(0.1)
        race_release.set()
        first_event_no, second_event_no = await asyncio.gather(first_task, second_task)

        assert (first_event_no, second_event_no) == (
            expected_first_new_event_no,
            expected_first_new_event_no + 1,
        )

        async with runtime.session_factory() as session:
            provider_events = list(
                await session.scalars(
                    select(ProviderEventRecordModel)
                    .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
                    .order_by(ProviderEventRecordModel.event_no.asc())
                )
            )

        new_events = provider_events[len(starting_event_nos) :]
        assert [event.event_no for event in new_events] == [
            expected_first_new_event_no,
            expected_first_new_event_no + 1,
        ]
        assert [event.event_kind for event in new_events] == [
            "tool_event",
            "response_completed",
        ]
