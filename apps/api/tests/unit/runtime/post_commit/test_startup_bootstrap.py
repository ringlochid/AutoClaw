from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime

import autoclaw.runtime.post_commit.bootstrap as bootstrap_module
import pytest
from autoclaw.runtime.post_commit import CapturedRuntimeEffectPublisher
from autoclaw.runtime.post_commit.bootstrap import audit_startup_runtime_effects
from autoclaw.runtime.post_commit.router import AsyncSessionContextFactory
from autoclaw.runtime.post_commit.signals import (
    BoundaryAccepted,
    CommandRunTerminal,
    DispatchStartDue,
    FlowStartCommitted,
    HumanRequestTerminal,
    RuntimeEffectSignal,
)
from autoclaw.runtime.startup_audit import StartupAuditPage
from sqlalchemy.ext.asyncio import AsyncSession

type PageReader = Callable[
    [AsyncSessionContextFactory, str | None, int],
    Awaitable[StartupAuditPage[RuntimeEffectSignal, str]],
]


def build_page_reader(signal: RuntimeEffectSignal) -> PageReader:
    async def read_page(
        session_factory: AsyncSessionContextFactory,
        cursor: str | None,
        page_size: int,
    ) -> StartupAuditPage[RuntimeEffectSignal, str]:
        del session_factory, cursor, page_size
        return StartupAuditPage((signal,), None)

    return read_page


async def test_runtime_startup_routes_only_registered_wp2_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    due_at = datetime(2030, 1, 1, tzinfo=UTC)
    signals = (
        FlowStartCommitted("flow.alpha"),
        BoundaryAccepted("dispatch.boundary"),
        HumanRequestTerminal("human.alpha"),
        CommandRunTerminal("command.alpha"),
        DispatchStartDue("dispatch.starting", 3, due_at),
    )
    reader_names = (
        "read_flow_start_page",
        "read_boundary_continuation_page",
        "read_human_continuation_page",
        "read_command_continuation_page",
        "read_dispatch_start_page",
    )
    for reader_name, signal in zip(reader_names, signals, strict=True):
        monkeypatch.setattr(bootstrap_module, reader_name, build_page_reader(signal))

    publisher = CapturedRuntimeEffectPublisher()
    results = await audit_startup_runtime_effects(
        session_factory=unused_session_context,
        publish=publisher.publish,
        routed_signal_types=(FlowStartCommitted,),
    )

    assert publisher.signals == (signals[0],)
    assert results["runnable_flow_start"].routed_count == 1
    assert results["runnable_flow_start"].deferred_count == 0
    assert all(result.discovered_count == 1 for result in results.values())
    assert all(
        result.deferred_count == 1
        for family_name, result in results.items()
        if family_name != "runnable_flow_start"
    )


def unused_session_context() -> AbstractAsyncContextManager[AsyncSession]:
    raise AssertionError("startup pager unexpectedly opened a session")
