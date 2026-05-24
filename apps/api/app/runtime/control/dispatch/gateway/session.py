from __future__ import annotations

from dataclasses import dataclass
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import (
    DispatchContinuityStateModel,
    DispatchTurnModel,
    NodeSessionModel,
)
from app.runtime.contract_models.prompt import PromptFamily
from app.runtime.control.failures import illegal_state_error
from app.runtime.openclaw.session_keys import normalize_transport_session_key

PARENT_ROOT_CONTINUITY_NEXT_STEP = (
    "Inspect the latest fenced parent/root dispatch and continuity invalidation, then "
    "escalate or open a new legal attempt instead of redispatching this same attempt."
)


@dataclass(frozen=True)
class ParentRootContinuityBasis:
    dispatch_id: str
    session_key: str | None
    invalidation_reason: str | None
    continuity_authority_exists: bool


def mint_gateway_session_key(dispatch_id: str) -> str:
    base_session_key = f"gateway-session.{dispatch_id}.{token_urlsafe(12)}"
    return normalize_transport_session_key(
        base_session_key,
        get_settings().openclaw.agent_id,
    )


async def resolve_gateway_session_key(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> str:
    if await parent_root_continuity_basis_missing_or_invalid(
        session,
        dispatch=dispatch,
    ):
        raise illegal_state_error(
            "parent/root same-attempt redispatch lost its continuity basis",
            suggested_next_step=PARENT_ROOT_CONTINUITY_NEXT_STEP,
        )
    reusable_session_key = await latest_parent_root_session_key_for_attempt(
        session,
        dispatch=dispatch,
    )
    if reusable_session_key is not None:
        return reusable_session_key
    return mint_gateway_session_key(dispatch.dispatch_id)


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


async def parent_root_continuity_basis_missing_or_invalid(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> bool:
    if (
        dispatch.previous_dispatch_id is None
        or dispatch.prompt_name != PromptFamily.PARENT_ROOT_DISPATCH.value
        or dispatch.task_id is None
        or dispatch.assignment_id is None
        or dispatch.assignment_key is None
        or dispatch.attempt_id is None
    ):
        return False
    basis = await latest_parent_root_continuity_basis(
        session,
        dispatch=dispatch,
    )
    if basis is not None:
        return not parent_root_continuity_basis_is_lawful(basis)
    return await parent_root_continuity_candidate_exists(
        session,
        dispatch=dispatch,
    )


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
        )
        .exists()
    )
    row = (
        await session.execute(
            select(
                DispatchTurnModel.dispatch_id,
                DispatchTurnModel.gateway_session_key,
                DispatchContinuityStateModel.invalidation_reason,
                continuity_authority_exists.label("continuity_authority_exists"),
            )
            .join(
                DispatchContinuityStateModel,
                DispatchContinuityStateModel.dispatch_id == DispatchTurnModel.dispatch_id,
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
                DispatchContinuityStateModel.session_key_present.is_(True),
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
        invalidation_reason=row.invalidation_reason,
        continuity_authority_exists=bool(row.continuity_authority_exists),
    )


async def parent_root_continuity_candidate_exists(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> bool:
    candidate = await session.scalar(
        select(DispatchTurnModel.dispatch_id)
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
    return candidate is not None


def parent_root_continuity_basis_is_lawful(
    basis: ParentRootContinuityBasis | None,
) -> bool:
    return (
        basis is not None
        and basis.session_key is not None
        and basis.invalidation_reason is None
        and basis.continuity_authority_exists
    )
