from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import DispatchTurnModel, FlowModel


@dataclass(frozen=True, slots=True)
class ProviderStartAcceptanceResult:
    """Report whether one exact provider-start generation won acceptance."""

    task_id: str
    dispatch_id: str
    provider_start_revision: int
    is_accepted: bool


async def accept_provider_start_if_current(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    expected_provider_start_revision: int,
    accepted_at: datetime,
) -> ProviderStartAcceptanceResult:
    """Move one exact current starting dispatch to open without provider I/O.

    The caller owns the transaction and may publish follow-up scheduling hints only
    after commit. A zero-row update is an ordinary loser: another controller
    transition or provider-start generation already won.
    """

    accepted_dispatch_id = await session.scalar(
        update(DispatchTurnModel)
        .where(
            DispatchTurnModel.dispatch_id == dispatch_id,
            DispatchTurnModel.task_id == task_id,
            DispatchTurnModel.status == "starting",
            DispatchTurnModel.provider_start_revision == expected_provider_start_revision,
            exists(
                select(FlowModel.flow_id).where(
                    FlowModel.flow_id == DispatchTurnModel.flow_id,
                    FlowModel.task_id == DispatchTurnModel.task_id,
                    FlowModel.status == "running",
                    FlowModel.current_dispatch_id == DispatchTurnModel.dispatch_id,
                    FlowModel.waiting_cause == "none",
                )
            ),
        )
        .values(
            status="open",
            adapter_started_at=accepted_at,
            next_provider_start_at=None,
            provider_start_retry_kind=None,
            provider_start_last_error_code=None,
        )
        .returning(DispatchTurnModel.dispatch_id)
    )
    return ProviderStartAcceptanceResult(
        task_id=task_id,
        dispatch_id=dispatch_id,
        provider_start_revision=expected_provider_start_revision,
        is_accepted=accepted_dispatch_id is not None,
    )


__all__ = [
    "ProviderStartAcceptanceResult",
    "accept_provider_start_if_current",
]
