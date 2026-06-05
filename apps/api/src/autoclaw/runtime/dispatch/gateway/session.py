from __future__ import annotations

from dataclasses import dataclass
from secrets import token_urlsafe

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import get_settings
from autoclaw.integrations.openclaw.gateway.session_keys import normalize_transport_session_key
from autoclaw.persistence.models import DispatchTurnModel, NodeSessionModel
from autoclaw.runtime.contracts import PromptFamily


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
