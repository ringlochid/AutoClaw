from __future__ import annotations

from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import DispatchTurnModel
from app.runtime.contract_models.prompt import PromptFamily
from app.runtime.openclaw.request_builders import agent_scoped_openclaw_session_key


def mint_gateway_session_key(dispatch_id: str) -> str:
    base_session_key = f"gateway-session.{dispatch_id}.{token_urlsafe(12)}"
    return agent_scoped_openclaw_session_key(
        base_session_key,
        get_settings().openclaw.agent_id,
    )


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


async def latest_parent_root_session_key_for_attempt(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
) -> str | None:
    if (
        dispatch.task_id is None
        or dispatch.assignment_id is None
        or dispatch.assignment_key is None
        or dispatch.attempt_id is None
        or dispatch.prompt_name != PromptFamily.PARENT_ROOT_DISPATCH.value
    ):
        return None
    return await session.scalar(
        select(DispatchTurnModel.gateway_session_key)
        .where(
            DispatchTurnModel.task_id == dispatch.task_id,
            DispatchTurnModel.node_key == dispatch.node_key,
            DispatchTurnModel.assignment_id == dispatch.assignment_id,
            DispatchTurnModel.assignment_key == dispatch.assignment_key,
            DispatchTurnModel.attempt_id == dispatch.attempt_id,
            DispatchTurnModel.dispatch_id != dispatch.dispatch_id,
            DispatchTurnModel.gateway_session_key.is_not(None),
            DispatchTurnModel.fenced_at.is_not(None),
        )
        .order_by(DispatchTurnModel.rendered_at.desc())
        .limit(1)
    )
