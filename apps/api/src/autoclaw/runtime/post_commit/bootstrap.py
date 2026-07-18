from __future__ import annotations

from collections.abc import Awaitable, Callable, Collection
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    AcceptedBoundaryModel,
    CommandRunModel,
    DispatchTurnModel,
    FlowModel,
    FlowStartSourceModel,
    HumanRequestModel,
)
from autoclaw.persistence.models.runtime.common import COMMAND_RUN_TERMINAL_STATE_VALUES
from autoclaw.runtime.post_commit.signals import (
    BoundaryAccepted,
    CommandRunTerminal,
    DispatchStartDue,
    FlowStartCommitted,
    HumanRequestTerminal,
    RuntimeEffectSignal,
)
from autoclaw.runtime.startup_audit import (
    StartupAuditPage,
    StartupAuditPaginationError,
    StartupAuditRoutingError,
    audit_startup_source_family,
)

type AsyncSessionContextFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]
type RuntimeEffectPublish = Callable[[RuntimeEffectSignal], bool]
type RuntimeEffectPageFetcher = Callable[
    [str | None, int],
    Awaitable[StartupAuditPage[RuntimeEffectSignal, str]],
]

_HUMAN_REQUEST_TERMINAL_STATUSES = ("resolved", "timed_out", "cancelled")


@dataclass(frozen=True, slots=True)
class StartupRuntimeFamilyResult:
    """Discovered, routed, and deliberately deferred rows for one source family."""

    discovered_count: int
    routed_count: int
    deferred_count: int


async def audit_startup_runtime_effects(
    *,
    session_factory: AsyncSessionContextFactory,
    publish: RuntimeEffectPublish,
    routed_signal_types: Collection[type[RuntimeEffectSignal]],
) -> dict[str, StartupRuntimeFamilyResult]:
    """Exhaust exact runtime pages and publish only routes with real handlers."""

    families: tuple[tuple[str, RuntimeEffectPageFetcher], ...] = (
        (
            "runnable_flow_start",
            lambda cursor, size: read_flow_start_page(session_factory, cursor, size),
        ),
        (
            "accepted_boundary",
            lambda cursor, size: read_boundary_continuation_page(
                session_factory,
                cursor,
                size,
            ),
        ),
        (
            "terminal_human_request",
            lambda cursor, size: read_human_continuation_page(
                session_factory,
                cursor,
                size,
            ),
        ),
        (
            "terminal_command_run",
            lambda cursor, size: read_command_continuation_page(
                session_factory,
                cursor,
                size,
            ),
        ),
        (
            "current_starting_dispatch",
            lambda cursor, size: read_dispatch_start_page(session_factory, cursor, size),
        ),
    )
    routable = frozenset(routed_signal_types)
    results: dict[str, StartupRuntimeFamilyResult] = {}
    for family_name, fetch_page in families:
        routed_count = 0
        deferred_count = 0

        async def route(signal: RuntimeEffectSignal) -> None:
            nonlocal routed_count, deferred_count
            if type(signal) not in routable:
                deferred_count += 1
                return
            if not publish(signal):
                raise StartupAuditRoutingError(
                    f"startup audit could not publish {type(signal).__name__}"
                )
            routed_count += 1

        discovered_count = await audit_startup_source_family(
            family_name=family_name,
            fetch_page=fetch_page,
            route_source=route,
            cursor_advances=lambda previous, candidate: candidate > previous,
        )
        results[family_name] = StartupRuntimeFamilyResult(
            discovered_count=discovered_count,
            routed_count=routed_count,
            deferred_count=deferred_count,
        )
    return results


async def read_flow_start_page(
    session_factory: AsyncSessionContextFactory,
    cursor: str | None,
    page_size: int,
) -> StartupAuditPage[RuntimeEffectSignal, str]:
    """Read runnable root sources that still have no committed root dispatch."""

    async with session_factory() as session:
        statement = (
            select(FlowStartSourceModel.flow_id)
            .join(FlowModel, FlowModel.flow_id == FlowStartSourceModel.flow_id)
            .where(
                FlowStartSourceModel.successor_dispatch_id.is_(None),
                FlowModel.status == "running",
                FlowModel.current_dispatch_id.is_(None),
                FlowModel.waiting_cause == "none",
            )
            .order_by(FlowStartSourceModel.flow_id)
            .limit(page_size)
        )
        if cursor is not None:
            statement = statement.where(FlowStartSourceModel.flow_id > cursor)
        source_ids = tuple((await session.scalars(statement)).all())
    return _runtime_signal_page(
        source_ids,
        page_size=page_size,
        build_signal=FlowStartCommitted,
    )


async def read_boundary_continuation_page(
    session_factory: AsyncSessionContextFactory,
    cursor: str | None,
    page_size: int,
) -> StartupAuditPage[RuntimeEffectSignal, str]:
    """Read accepted boundaries that still have no committed successor."""

    async with session_factory() as session:
        statement = (
            select(AcceptedBoundaryModel.source_dispatch_id)
            .where(AcceptedBoundaryModel.successor_dispatch_id.is_(None))
            .order_by(AcceptedBoundaryModel.source_dispatch_id)
            .limit(page_size)
        )
        if cursor is not None:
            statement = statement.where(AcceptedBoundaryModel.source_dispatch_id > cursor)
        source_ids = tuple((await session.scalars(statement)).all())
    return _runtime_signal_page(
        source_ids,
        page_size=page_size,
        build_signal=BoundaryAccepted,
    )


async def read_human_continuation_page(
    session_factory: AsyncSessionContextFactory,
    cursor: str | None,
    page_size: int,
) -> StartupAuditPage[RuntimeEffectSignal, str]:
    """Read terminal human sources that still have no committed successor."""

    async with session_factory() as session:
        statement = (
            select(HumanRequestModel.request_id)
            .where(
                HumanRequestModel.status.in_(_HUMAN_REQUEST_TERMINAL_STATUSES),
                HumanRequestModel.successor_dispatch_id.is_(None),
            )
            .order_by(HumanRequestModel.request_id)
            .limit(page_size)
        )
        if cursor is not None:
            statement = statement.where(HumanRequestModel.request_id > cursor)
        source_ids = tuple((await session.scalars(statement)).all())
    return _runtime_signal_page(
        source_ids,
        page_size=page_size,
        build_signal=HumanRequestTerminal,
    )


async def read_command_continuation_page(
    session_factory: AsyncSessionContextFactory,
    cursor: str | None,
    page_size: int,
) -> StartupAuditPage[RuntimeEffectSignal, str]:
    """Read terminal command sources that still have no committed successor."""

    async with session_factory() as session:
        statement = (
            select(CommandRunModel.run_id)
            .where(
                CommandRunModel.state.in_(COMMAND_RUN_TERMINAL_STATE_VALUES),
                CommandRunModel.successor_dispatch_id.is_(None),
            )
            .order_by(CommandRunModel.run_id)
            .limit(page_size)
        )
        if cursor is not None:
            statement = statement.where(CommandRunModel.run_id > cursor)
        source_ids = tuple((await session.scalars(statement)).all())
    return _runtime_signal_page(
        source_ids,
        page_size=page_size,
        build_signal=CommandRunTerminal,
    )


async def read_dispatch_start_page(
    session_factory: AsyncSessionContextFactory,
    cursor: str | None,
    page_size: int,
) -> StartupAuditPage[RuntimeEffectSignal, str]:
    """Read exact current starting dispatches without consuming or replacing them."""

    async with session_factory() as session:
        statement = (
            select(
                DispatchTurnModel.dispatch_id,
                DispatchTurnModel.provider_start_revision,
                DispatchTurnModel.next_provider_start_at,
            )
            .join(
                FlowModel,
                (FlowModel.flow_id == DispatchTurnModel.flow_id)
                & (FlowModel.current_dispatch_id == DispatchTurnModel.dispatch_id),
            )
            .where(DispatchTurnModel.status == "starting")
            .order_by(DispatchTurnModel.dispatch_id)
            .limit(page_size)
        )
        if cursor is not None:
            statement = statement.where(DispatchTurnModel.dispatch_id > cursor)
        rows = tuple((await session.execute(statement)).all())
    signals: list[RuntimeEffectSignal] = []
    for dispatch_id, provider_start_revision, due_at in rows:
        if due_at is None:
            raise StartupAuditPaginationError(
                f"current starting dispatch {dispatch_id!r} has no provider-start due time"
            )
        signals.append(DispatchStartDue(dispatch_id, provider_start_revision, due_at))
    return StartupAuditPage(
        tuple(signals),
        rows[-1][0] if len(rows) == page_size else None,
    )


def _runtime_signal_page(
    source_ids: tuple[str, ...],
    *,
    page_size: int,
    build_signal: Callable[[str], RuntimeEffectSignal],
) -> StartupAuditPage[RuntimeEffectSignal, str]:
    return StartupAuditPage(
        tuple(build_signal(source_id) for source_id in source_ids),
        source_ids[-1] if len(source_ids) == page_size else None,
    )


__all__ = [
    "StartupRuntimeFamilyResult",
    "audit_startup_runtime_effects",
    "read_boundary_continuation_page",
    "read_command_continuation_page",
    "read_dispatch_start_page",
    "read_flow_start_page",
    "read_human_continuation_page",
]
