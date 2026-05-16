from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import (
    AssignmentModel,
    AttemptModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
)
from app.runtime.contracts import PromptSendMode
from app.runtime.control.clock import dispatch_control_deadline, utc_now
from app.runtime.control.dispatch.callbacks import revoke_callback_binding
from app.runtime.control.dispatch.opening import activate_dispatch_turn, prepare_dispatch_turn
from app.runtime.control.flow.queries import flow_node_by_key
from app.runtime.effects import commit_runtime_session
from app.runtime.effects.cases import stage_dispatch_open_outputs


@dataclass(frozen=True)
class WatchdogRecoveryRequest:
    dispatch: DispatchTurnModel
    watchdog_state: DispatchWatchdogStateModel
    flow: FlowModel
    delivery_state: DispatchDeliveryStateModel | None


async def execute_watchdog_recovery(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    task_id: str,
    dispatch_id: str,
) -> bool:
    async with session_factory() as session:
        recovery = await _load_watchdog_recovery_request(session, dispatch_id=dispatch_id)
        if recovery is None:
            return False
        if await _record_existing_recovery_dispatch(
            session,
            task_id=task_id,
            recovery=recovery,
        ):
            return True
        await _normalize_terminal_abort_requested_dispatch(session, recovery=recovery)
        dispatch = recovery.dispatch
        flow = recovery.flow
        if dispatch.control_state in {"launching", "abort_requested", "ambiguous"}:
            return False
        if dispatch.control_state != "fenced":
            return await _request_watchdog_abort(
                session,
                task_id=task_id,
                flow=flow,
                dispatch=dispatch,
                delivery_state=recovery.delivery_state,
                reason=recovery.watchdog_state.current_watchdog_kind or "watchdog_recovery",
            )
        if flow.current_open_dispatch_id is not None:
            return False
        return await _open_watchdog_recovery_dispatch(
            session,
            task_id=task_id,
            recovery=recovery,
        )


async def _load_watchdog_recovery_request(
    session: AsyncSession,
    *,
    dispatch_id: str,
) -> WatchdogRecoveryRequest | None:
    dispatch = await session.get(DispatchTurnModel, dispatch_id)
    watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
    if dispatch is None or watchdog_state is None:
        return None
    if watchdog_state.recovery_action != "redispatch_same_attempt":
        return None
    if watchdog_state.recovery_dispatch_id is not None or dispatch.flow_id is None:
        return None
    flow = await session.get(FlowModel, dispatch.flow_id)
    if flow is None:
        return None
    return WatchdogRecoveryRequest(
        dispatch=dispatch,
        watchdog_state=watchdog_state,
        flow=flow,
        delivery_state=await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id),
    )


async def _record_existing_recovery_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    recovery: WatchdogRecoveryRequest,
) -> bool:
    if recovery.dispatch.superseded_by_dispatch_id is None:
        return False
    recovery.watchdog_state.recovery_dispatch_id = recovery.dispatch.superseded_by_dispatch_id
    recovery.watchdog_state.updated_at = utc_now()
    stage_dispatch_open_outputs(
        session,
        task_id=task_id,
        dispatch_id=recovery.dispatch.dispatch_id,
    )
    await commit_runtime_session(session)
    return True


async def _normalize_terminal_abort_requested_dispatch(
    session: AsyncSession,
    *,
    recovery: WatchdogRecoveryRequest,
) -> None:
    dispatch = recovery.dispatch
    if (
        dispatch.control_state == "abort_requested"
        and dispatch.delivery_status in {"provider_completed", "provider_failed"}
        and recovery.flow.current_open_dispatch_id is None
    ):
        dispatch.control_state = "fenced"
        dispatch.control_state_reason = dispatch.control_state_reason or "watchdog:inactive_proven"
        dispatch.fenced_at = dispatch.fenced_at or utc_now()
        await session.flush()


async def _open_watchdog_recovery_dispatch(
    session: AsyncSession,
    *,
    task_id: str,
    recovery: WatchdogRecoveryRequest,
) -> bool:
    dispatch = recovery.dispatch
    assignment = await session.get(AssignmentModel, dispatch.assignment_id)
    if assignment is None:
        return False
    attempt = await _same_attempt_recovery_target(
        session,
        assignment=assignment,
        dispatch=dispatch,
    )
    if attempt is None:
        return False
    node = await flow_node_by_key(
        session,
        recovery.flow.active_flow_revision_id or "",
        dispatch.node_key,
    )
    recovery_dispatch = await prepare_dispatch_turn(
        session,
        task_id=task_id,
        flow=recovery.flow,
        node=node,
        assignment=assignment,
        attempt=attempt,
        send_mode=PromptSendMode.FULL_PROMPT,
        previous_dispatch=dispatch,
        staged_child_assignment_id=None,
    )
    await _stage_recovery_dispatch_projection(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
        watchdog_state=recovery.watchdog_state,
        recovery_dispatch_id=recovery_dispatch.dispatch_id,
    )
    await activate_dispatch_turn(
        session,
        task_id=task_id,
        flow=recovery.flow,
        dispatch=recovery_dispatch,
        assignment=assignment,
        attempt=attempt,
        stage_launch_projection_outputs=False,
    )
    await _stage_recovery_dispatch_projection(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
        watchdog_state=recovery.watchdog_state,
        recovery_dispatch_id=recovery_dispatch.dispatch_id,
    )
    await commit_runtime_session(session)
    return True


async def _stage_recovery_dispatch_projection(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    watchdog_state: DispatchWatchdogStateModel,
    recovery_dispatch_id: str,
) -> None:
    watchdog_state.recovery_dispatch_id = recovery_dispatch_id
    watchdog_state.updated_at = utc_now()
    stage_dispatch_open_outputs(
        session,
        task_id=task_id,
        dispatch_id=dispatch_id,
    )
    await session.flush()


async def _request_watchdog_abort(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    dispatch: DispatchTurnModel,
    delivery_state: DispatchDeliveryStateModel | None,
    reason: str,
) -> bool:
    if flow.current_open_dispatch_id != dispatch.dispatch_id:
        return False
    if dispatch.accepted_boundary is not None:
        return False
    requested_at = utc_now()
    changed = False
    if dispatch.status != "closed":
        dispatch.status = "closed"
        changed = True
    if dispatch.closed_at is None:
        dispatch.closed_at = requested_at
        changed = True
    if dispatch.abort_requested_at is None:
        dispatch.abort_requested_at = requested_at
        changed = True
    dispatch.control_state = "abort_requested"
    dispatch.control_state_reason = f"watchdog:{reason}"
    dispatch.control_deadline_at = dispatch_control_deadline(base=requested_at)
    await revoke_callback_binding(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
    )
    if delivery_state is not None:
        delivery_state.controller_observation_state = "abort_requested"
        delivery_state.updated_at = requested_at
    stage_dispatch_open_outputs(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
    )
    await session.flush()
    if not changed:
        return False
    await commit_runtime_session(session)
    return True


async def _same_attempt_recovery_target(
    session: AsyncSession,
    *,
    assignment: AssignmentModel,
    dispatch: DispatchTurnModel,
) -> AttemptModel | None:
    if assignment.current_attempt_id != dispatch.attempt_id or dispatch.attempt_id is None:
        return None
    attempt = await session.get(AttemptModel, dispatch.attempt_id)
    if attempt is None or attempt.closed_at is not None or attempt.terminal_outcome is not None:
        return None
    return attempt


__all__ = ["execute_watchdog_recovery"]
