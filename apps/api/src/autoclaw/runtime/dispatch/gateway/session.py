from __future__ import annotations

from dataclasses import dataclass
from secrets import token_urlsafe

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway.session_keys import normalize_transport_session_key
from autoclaw.persistence.models import (
    CommandRunModel,
    DispatchTurnModel,
    NodeSessionModel,
    PendingHumanRequestModel,
)
from autoclaw.runtime.contracts import (
    TERMINAL_COMMAND_RUN_STATES,
    HumanRequestStatus,
    PromptFamily,
)


@dataclass(frozen=True)
class ParentRootContinuityBasis:
    dispatch_id: str
    session_key: str | None
    is_fenced: bool
    has_continuity_authority: bool


async def resolve_gateway_session_key(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> str:
    external_wait_session_key = await previous_external_wait_session_key(
        session,
        dispatch=dispatch,
    )
    if external_wait_session_key is not None:
        return external_wait_session_key

    reusable_session_key = await latest_parent_root_session_key_for_attempt(
        session,
        dispatch=dispatch,
    )
    if reusable_session_key is not None:
        return reusable_session_key
    return mint_gateway_session_key(dispatch.dispatch_id)


def mint_gateway_session_key(dispatch_id: str) -> str:
    base_session_key = f"gateway-session.{dispatch_id}.{token_urlsafe(12)}"
    return normalize_transport_session_key(
        base_session_key,
        get_settings().openclaw.agent_id,
    )


async def latest_parent_root_session_key_for_attempt(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> str | None:
    basis = await latest_parent_root_continuity_basis(
        session,
        dispatch=dispatch,
    )
    if not parent_root_continuity_basis_is_lawful(basis):
        return None
    assert basis is not None
    assert basis.session_key is not None
    return basis.session_key


async def previous_external_wait_session_key(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> str | None:
    previous_dispatch = await _previous_dispatch_for_external_wait_continuity(
        session,
        dispatch=dispatch,
    )
    if previous_dispatch is None or previous_dispatch.gateway_session_key is None:
        return None
    if not await _dispatch_has_lawful_session_authority(session, dispatch=previous_dispatch):
        return None
    if not await _dispatch_opened_terminal_external_wait(session, dispatch=previous_dispatch):
        return None
    return previous_dispatch.gateway_session_key


async def latest_parent_root_continuity_basis(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> ParentRootContinuityBasis | None:
    if (
        dispatch.task_id is None
        or dispatch.assignment_id is None
        or dispatch.assignment_key is None
        or dispatch.attempt_id is None
        or dispatch.prompt_name != PromptFamily.PARENT_ROOT_DISPATCH.value
    ):
        return None
    continuity_authority_exists = (
        select(NodeSessionModel.node_session_id)
        .where(
            NodeSessionModel.dispatch_id == DispatchTurnModel.dispatch_id,
            NodeSessionModel.session_key == DispatchTurnModel.gateway_session_key,
            NodeSessionModel.session_status == "fenced",
            NodeSessionModel.closed_at.is_not(None),
        )
        .exists()
    )
    row = (
        await session.execute(
            select(
                DispatchTurnModel.dispatch_id,
                DispatchTurnModel.gateway_session_key,
                case(
                    (
                        (DispatchTurnModel.control_state == "fenced")
                        & DispatchTurnModel.fenced_at.is_not(None),
                        True,
                    ),
                    else_=False,
                ).label("fenced"),
                continuity_authority_exists.label("continuity_authority_exists"),
            )
            .where(
                DispatchTurnModel.task_id == dispatch.task_id,
                DispatchTurnModel.node_key == dispatch.node_key,
                DispatchTurnModel.assignment_id == dispatch.assignment_id,
                DispatchTurnModel.assignment_key == dispatch.assignment_key,
                DispatchTurnModel.attempt_id == dispatch.attempt_id,
                DispatchTurnModel.dispatch_id != dispatch.dispatch_id,
                DispatchTurnModel.prompt_name == PromptFamily.PARENT_ROOT_DISPATCH.value,
                DispatchTurnModel.gateway_session_key.is_not(None),
                DispatchTurnModel.closed_at.is_not(None),
            )
            .order_by(DispatchTurnModel.rendered_at.desc())
            .limit(1)
        )
    ).one_or_none()
    if row is None:
        return None
    return ParentRootContinuityBasis(
        dispatch_id=str(row.dispatch_id),
        session_key=row.gateway_session_key,
        is_fenced=bool(row.fenced),
        has_continuity_authority=bool(row.continuity_authority_exists),
    )


def parent_root_continuity_basis_is_lawful(
    basis: ParentRootContinuityBasis | None,
) -> bool:
    return (
        basis is not None
        and basis.session_key is not None
        and basis.is_fenced
        and basis.has_continuity_authority
    )


async def _previous_dispatch_for_external_wait_continuity(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> DispatchTurnModel | None:
    if (
        dispatch.previous_dispatch_id is None
        or dispatch.task_id is None
        or dispatch.assignment_id is None
        or dispatch.assignment_key is None
        or dispatch.attempt_id is None
    ):
        return None
    previous_dispatch = await session.get(DispatchTurnModel, dispatch.previous_dispatch_id)
    if previous_dispatch is None:
        return None
    if (
        previous_dispatch.task_id != dispatch.task_id
        or previous_dispatch.node_key != dispatch.node_key
        or previous_dispatch.assignment_id != dispatch.assignment_id
        or previous_dispatch.assignment_key != dispatch.assignment_key
        or previous_dispatch.attempt_id != dispatch.attempt_id
    ):
        return None
    if (
        previous_dispatch.control_state != "fenced"
        or previous_dispatch.fenced_at is None
        or previous_dispatch.closed_at is None
    ):
        return None
    return previous_dispatch


async def _dispatch_has_lawful_session_authority(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> bool:
    if dispatch.gateway_session_key is None:
        return False
    node_session_id = await session.scalar(
        select(NodeSessionModel.node_session_id)
        .where(
            NodeSessionModel.dispatch_id == dispatch.dispatch_id,
            NodeSessionModel.session_key == dispatch.gateway_session_key,
            NodeSessionModel.session_status == "fenced",
            NodeSessionModel.closed_at.is_not(None),
        )
        .limit(1)
    )
    return node_session_id is not None


async def _dispatch_opened_terminal_external_wait(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> bool:
    if dispatch.task_id is None:
        return False
    if await _dispatch_opened_terminal_human_request(session, dispatch=dispatch):
        return True
    return await _dispatch_opened_terminal_command_run(session, dispatch=dispatch)


async def _dispatch_opened_terminal_human_request(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> bool:
    terminal_statuses = (
        HumanRequestStatus.RESOLVED.value,
        HumanRequestStatus.TIMED_OUT.value,
        HumanRequestStatus.CANCELLED.value,
    )
    request_id = await session.scalar(
        select(PendingHumanRequestModel.request_id)
        .where(
            PendingHumanRequestModel.task_id == dispatch.task_id,
            PendingHumanRequestModel.dispatch_id == dispatch.dispatch_id,
            PendingHumanRequestModel.status.in_(terminal_statuses),
            PendingHumanRequestModel.resolved_at.is_not(None),
        )
        .limit(1)
    )
    return request_id is not None


async def _dispatch_opened_terminal_command_run(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> bool:
    terminal_states = tuple(state.value for state in TERMINAL_COMMAND_RUN_STATES)
    run_id = await session.scalar(
        select(CommandRunModel.run_id)
        .where(
            CommandRunModel.task_id == dispatch.task_id,
            CommandRunModel.dispatch_id == dispatch.dispatch_id,
            CommandRunModel.state.in_(terminal_states),
            CommandRunModel.ended_at.is_not(None),
        )
        .limit(1)
    )
    return run_id is not None
