from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import DispatchCallbackBindingModel, DispatchTurnModel
from app.runtime.control.clock import utc_now
from app.runtime.control.dispatch.authority import (
    NodeSessionAuthority,
    validate_node_session_key,
)
from app.runtime.control.failures import (
    missing_resource_error,
    stale_dispatch_error,
)
from app.runtime.ids import dispatch_callback_binding_id


async def validate_callback_session_key(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
) -> NodeSessionAuthority:
    live_binding = await _live_callback_binding_for_session_key(
        session,
        task_id=task_id,
        session_key=session_key,
    )
    if live_binding is None:
        any_binding = await _any_callback_binding_for_session_key(
            session,
            task_id=task_id,
            session_key=session_key,
        )
        if any_binding is not None:
            raise stale_dispatch_error("stale callback session key")
    return await validate_node_session_key(
        session,
        task_id=task_id,
        session_key=session_key,
        invalid_summary="invalid callback session key",
        stale_summary="stale callback session key",
        inactive_summary="inactive callback session key",
    )


async def revoke_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    binding = await _live_callback_binding(session, task_id=task_id, dispatch_id=dispatch_id)
    if binding is None:
        return
    binding.binding_status = "revoked"
    binding.revoked_at = utc_now()
    await session.flush()


async def create_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    attempt_id: str,
    assignment_id: str,
) -> DispatchCallbackBindingModel:
    dispatch = await session.get(
        DispatchTurnModel,
        dispatch_id,
        options=(raiseload("*"),),
    )
    if dispatch is None:
        raise missing_resource_error(f"missing dispatch '{dispatch_id}'")
    if dispatch.gateway_session_key is None:
        raise stale_dispatch_error(f"dispatch '{dispatch_id}' has no live session key")
    binding = DispatchCallbackBindingModel(
        dispatch_callback_binding_id=dispatch_callback_binding_id(dispatch_id),
        dispatch_id=dispatch_id,
        attempt_id=attempt_id,
        assignment_id=assignment_id,
        task_id=task_id,
        session_key=dispatch.gateway_session_key,
        binding_status="live",
    )
    session.add(binding)
    await session.flush()
    return binding


async def _live_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> DispatchCallbackBindingModel | None:
    return await _first_callback_binding(
        session,
        task_id=task_id,
        where_clauses=(
            DispatchCallbackBindingModel.dispatch_id == dispatch_id,
            DispatchCallbackBindingModel.binding_status == "live",
            DispatchCallbackBindingModel.revoked_at.is_(None),
        ),
    )


async def _live_callback_binding_for_session_key(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
) -> DispatchCallbackBindingModel | None:
    return await _first_callback_binding(
        session,
        task_id=task_id,
        where_clauses=(
            DispatchCallbackBindingModel.session_key == session_key,
            DispatchCallbackBindingModel.binding_status == "live",
            DispatchCallbackBindingModel.revoked_at.is_(None),
        ),
    )


async def _any_callback_binding_for_session_key(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
) -> DispatchCallbackBindingModel | None:
    return await _first_callback_binding(
        session,
        task_id=task_id,
        where_clauses=(DispatchCallbackBindingModel.session_key == session_key,),
    )


async def _first_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    where_clauses: tuple[ColumnElement[bool], ...],
) -> DispatchCallbackBindingModel | None:
    result = await session.execute(
        select(DispatchCallbackBindingModel)
        .options(raiseload("*"))
        .where(
            DispatchCallbackBindingModel.task_id == task_id,
            *where_clauses,
        )
    )
    return result.scalar_one_or_none()
