from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    CheckpointStatus,
    FlowNodeState,
    FlowStatus,
    NodeAttemptStatus,
    NodeSessionStatus,
    WaitReason,
)
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import Flow, FlowNode, NodeAttempt, NodeCheckpoint
from app.integrations.openclaw import (
    OpenClawClient,
    OpenClawIntegrationError,
    OpenClawRequestError,
    OpenClawTimeoutError,
)
from app.runtime.control import (
    ensure_current_attempt,
    idle_node_session,
    latest_attempt,
    lock_flow,
    refresh_flow_status,
    waiting_block_reason,
)
from app.runtime.runner import get_flow_with_relations
from app.runtime.scheduler import ordered_nodes
from app.runtime.state import (
    mark_node_attempt_blocked,
    mark_node_attempt_running,
    utcnow_naive,
)
from app.schemas.runtime import FlowWatchdogRecoveryAction, FlowWatchdogRecoveryReason
from app.services.openclaw_bridge import OpenClawDispatchResult, dispatch_flow_to_openclaw


@dataclass(slots=True)
class FlowWatchdogRecoveryResult:
    flow: Flow
    recovery_action: FlowWatchdogRecoveryAction
    recovery_reason: FlowWatchdogRecoveryReason
    flow_node: FlowNode | None = None
    node_attempt: NodeAttempt | None = None
    dispatch_result: OpenClawDispatchResult | None = None
    detail: str | None = None
    operator_next_step: str | None = None


def _visible_checkpoints(node_attempt: NodeAttempt) -> list[NodeCheckpoint]:
    return [checkpoint for checkpoint in node_attempt.checkpoints if checkpoint.sequence_no > 0]


def _last_progress_at(flow_node: FlowNode, node_attempt: NodeAttempt) -> datetime:
    visible_checkpoints = _visible_checkpoints(node_attempt)
    if visible_checkpoints:
        return visible_checkpoints[-1].created_at
    return node_attempt.started_at


async def run_flow_watchdog(
    session: AsyncSession,
    *,
    flow_id: UUID,
    stale_after_seconds: int = 300,
) -> tuple[Flow, list[UUID], list[NodeCheckpoint]]:
    await lock_flow(session, flow_id)
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")
    if flow.status in {FlowStatus.CANCELLED, FlowStatus.FAILED, FlowStatus.SUCCEEDED}:
        raise ConflictError(f"Flow is already terminal: {flow.status.value}")

    threshold = utcnow_naive() - timedelta(seconds=stale_after_seconds)
    stalled_attempt_ids: list[UUID] = []
    checkpoints: list[NodeCheckpoint] = []

    if flow.active_flow_revision is None:
        return flow, stalled_attempt_ids, checkpoints

    for flow_node in flow.active_flow_revision.nodes:
        latest_node_attempt = flow_node.attempts[-1] if flow_node.attempts else None
        if latest_node_attempt is None or latest_node_attempt.status != NodeAttemptStatus.RUNNING:
            continue

        if (
            flow_node.node_session is not None
            and flow_node.node_session.node_attempt_id != latest_node_attempt.id
        ):
            raise ConflictError("Node session is no longer bound to the running node attempt")

        visible_checkpoints = _visible_checkpoints(latest_node_attempt)
        last_progress_time = _last_progress_at(flow_node, latest_node_attempt)
        if last_progress_time >= threshold:
            continue

        latest_node_attempt.status = NodeAttemptStatus.BLOCKED
        flow_node.state = FlowNodeState.WAITING
        idle_node_session(flow_node.node_session)
        checkpoint = NodeCheckpoint(
            flow_id=flow.id,
            flow_node_id=flow_node.id,
            node_attempt_id=latest_node_attempt.id,
            sequence_no=(visible_checkpoints[-1].sequence_no + 1) if visible_checkpoints else 1,
            status=CheckpointStatus.BLOCKED,
            summary="watchdog stalled attempt",
            payload={
                "stale_after_seconds": stale_after_seconds,
                "last_progress_at": last_progress_time.isoformat(),
            },
            recommended_next_action="retry",
            wait_reason=WaitReason.WATCHDOG,
        )
        session.add(checkpoint)
        checkpoints.append(checkpoint)
        stalled_attempt_ids.append(latest_node_attempt.id)

    if stalled_attempt_ids:
        refresh_flow_status(flow)

    await session.flush()
    return flow, stalled_attempt_ids, checkpoints


def _watchdog_auto_wake_count(flow_node: FlowNode, *, node_attempt_id: UUID) -> int:
    status_payload = flow_node.status_payload if isinstance(flow_node.status_payload, dict) else {}
    recovery = status_payload.get("watchdog_recovery")
    if not isinstance(recovery, dict):
        return 0
    recorded_attempt_id = recovery.get("node_attempt_id")
    if recorded_attempt_id != str(node_attempt_id):
        return 0
    wake_count = recovery.get("auto_wake_count")
    return wake_count if isinstance(wake_count, int) and wake_count >= 0 else 0


def _set_watchdog_recovery_metadata(
    flow_node: FlowNode,
    *,
    node_attempt_id: UUID,
    auto_wake_count: int,
    last_action: str,
) -> None:
    status_payload = (
        dict(flow_node.status_payload) if isinstance(flow_node.status_payload, dict) else {}
    )
    recovery = status_payload.get("watchdog_recovery")
    recovery_payload = dict(recovery) if isinstance(recovery, dict) else {}
    recovery_payload.update(
        {
            "node_attempt_id": str(node_attempt_id),
            "auto_wake_count": auto_wake_count,
            "last_action": last_action,
            "updated_at": utcnow_naive().isoformat(),
        }
    )
    status_payload["watchdog_recovery"] = recovery_payload
    flow_node.status_payload = status_payload


async def recover_flow_watchdog(
    session: AsyncSession,
    *,
    flow_id: UUID,
    client: OpenClawClient | None = None,
    max_auto_wakes: int = 1,
) -> FlowWatchdogRecoveryResult:
    await lock_flow(session, flow_id)
    flow = await get_flow_with_relations(session, flow_id)
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")
    if flow.status in {FlowStatus.CANCELLED, FlowStatus.FAILED, FlowStatus.SUCCEEDED}:
        raise ConflictError(f"Flow is already terminal: {flow.status.value}")
    if flow.active_flow_revision is None:
        return FlowWatchdogRecoveryResult(
            flow=flow,
            recovery_action=FlowWatchdogRecoveryAction.NONE,
            recovery_reason=FlowWatchdogRecoveryReason.NO_ACTIVE_REVISION,
            detail="flow has no active revision",
        )

    candidates: list[tuple[FlowNode, NodeAttempt]] = []
    for flow_node in ordered_nodes(flow):
        node_attempt = latest_attempt(flow_node)
        if node_attempt is None:
            continue
        if node_attempt.status != NodeAttemptStatus.BLOCKED:
            continue
        if flow_node.state != FlowNodeState.WAITING:
            continue
        if waiting_block_reason(flow, flow_node, node_attempt) != WaitReason.WATCHDOG:
            continue
        candidates.append((flow_node, node_attempt))

    if not candidates:
        return FlowWatchdogRecoveryResult(
            flow=flow,
            recovery_action=FlowWatchdogRecoveryAction.NONE,
            recovery_reason=FlowWatchdogRecoveryReason.NO_ELIGIBLE_NODE,
            detail="no watchdog-blocked node is eligible for recovery",
        )

    if len(candidates) > 1:
        return FlowWatchdogRecoveryResult(
            flow=flow,
            recovery_action=FlowWatchdogRecoveryAction.ESCALATE,
            recovery_reason=FlowWatchdogRecoveryReason.MULTIPLE_WATCHDOG_BLOCKED_NODES,
            detail="multiple watchdog-blocked nodes require operator review",
            operator_next_step=(
                "Inspect the blocked nodes and recover one explicitly; the runtime cannot "
                "prove a single safe wake target."
            ),
        )

    flow_node, node_attempt = candidates[0]
    if flow_node.node_session is None or flow_node.node_session.node_attempt_id != node_attempt.id:
        _set_watchdog_recovery_metadata(
            flow_node,
            node_attempt_id=node_attempt.id,
            auto_wake_count=_watchdog_auto_wake_count(flow_node, node_attempt_id=node_attempt.id),
            last_action="escalate:missing-or-rebound-session",
        )
        await session.flush()
        return FlowWatchdogRecoveryResult(
            flow=flow,
            recovery_action=FlowWatchdogRecoveryAction.ESCALATE,
            recovery_reason=FlowWatchdogRecoveryReason.MISSING_OR_REBOUND_SESSION,
            flow_node=flow_node,
            node_attempt=node_attempt,
            detail=(
                "watchdog recovery needs operator help because the delegated session is "
                "missing or no longer bound"
            ),
            operator_next_step=(
                "Inspect the delegated session binding and create a fresh operator retry if "
                "the attempt is no longer resumable."
            ),
        )

    ensure_current_attempt(
        flow,
        flow_node,
        node_attempt,
        allowed_statuses={NodeAttemptStatus.BLOCKED},
        require_current_session=True,
        node_session=flow_node.node_session,
    )

    wake_count = _watchdog_auto_wake_count(flow_node, node_attempt_id=node_attempt.id)
    if wake_count >= max_auto_wakes:
        _set_watchdog_recovery_metadata(
            flow_node,
            node_attempt_id=node_attempt.id,
            auto_wake_count=wake_count,
            last_action="escalate:wake-budget-exhausted",
        )
        await session.flush()
        return FlowWatchdogRecoveryResult(
            flow=flow,
            recovery_action=FlowWatchdogRecoveryAction.ESCALATE,
            recovery_reason=FlowWatchdogRecoveryReason.WAKE_BUDGET_EXHAUSTED,
            flow_node=flow_node,
            node_attempt=node_attempt,
            detail="watchdog auto-wake budget exhausted for this node attempt",
            operator_next_step=(
                "Inspect flow state before retrying and prefer a fresh operator retry over "
                "another same-session wake."
            ),
        )

    mark_node_attempt_running(flow, flow_node, node_attempt)
    flow_node.node_session.status = NodeSessionStatus.ACTIVE
    flow_node.node_session.last_seen_at = utcnow_naive()
    await session.flush()

    try:
        dispatch_result = await dispatch_flow_to_openclaw(
            session,
            flow_id=flow.id,
            client=client,
            instruction_override=(
                "Watchdog recovery wake-up. Resume the current node attempt in the existing "
                "session. Do not restart from scratch. If work is already complete, record the "
                "next valid control fact instead of repeating analysis."
            ),
            target_flow_node_id=flow_node.id,
            target_node_attempt_id=node_attempt.id,
        )
    except OpenClawTimeoutError as exc:
        _set_watchdog_recovery_metadata(
            flow_node,
            node_attempt_id=node_attempt.id,
            auto_wake_count=wake_count + 1,
            last_action="escalate:wake-dispatch-timeout",
        )
        await session.flush()
        refreshed_flow = await get_flow_with_relations(session, flow.id)
        return FlowWatchdogRecoveryResult(
            flow=refreshed_flow or flow,
            recovery_action=FlowWatchdogRecoveryAction.ESCALATE,
            recovery_reason=FlowWatchdogRecoveryReason.WAKE_DISPATCH_TIMEOUT,
            flow_node=flow_node,
            node_attempt=node_attempt,
            detail=(
                f"{exc} (wake delivery is ambiguous; the delegated worker may still resume and "
                "emit late callbacks)"
            ),
            operator_next_step=(
                "Inspect the delegated session and recent checkpoints before retrying; treat "
                "this timeout as ambiguous delivery, not a proven failed wake."
            ),
        )
    except (OpenClawRequestError, OpenClawIntegrationError) as exc:
        mark_node_attempt_blocked(flow, flow_node, node_attempt)
        idle_node_session(flow_node.node_session)
        _set_watchdog_recovery_metadata(
            flow_node,
            node_attempt_id=node_attempt.id,
            auto_wake_count=wake_count + 1,
            last_action="escalate:wake-dispatch-failed",
        )
        await session.flush()
        refreshed_flow = await get_flow_with_relations(session, flow.id)
        return FlowWatchdogRecoveryResult(
            flow=refreshed_flow or flow,
            recovery_action=FlowWatchdogRecoveryAction.ESCALATE,
            recovery_reason=FlowWatchdogRecoveryReason.WAKE_DISPATCH_FAILED,
            flow_node=flow_node,
            node_attempt=node_attempt,
            detail=f"watchdog wake dispatch failed: {exc}",
            operator_next_step=(
                "Inspect the failure detail and delegated session state before deciding whether "
                "to operator-retry the node."
            ),
        )

    _set_watchdog_recovery_metadata(
        flow_node,
        node_attempt_id=node_attempt.id,
        auto_wake_count=wake_count + 1,
        last_action="wake-dispatched",
    )
    await session.flush()
    refreshed_flow = await get_flow_with_relations(session, flow.id)
    return FlowWatchdogRecoveryResult(
        flow=refreshed_flow or dispatch_result.flow,
        recovery_action=FlowWatchdogRecoveryAction.WAKE,
        recovery_reason=FlowWatchdogRecoveryReason.WAKE_DISPATCHED,
        flow_node=flow_node,
        node_attempt=node_attempt,
        dispatch_result=dispatch_result,
        detail="watchdog recovery dispatched a same-session wake-up",
        operator_next_step="Wait for callbacks; only retry if the node stalls again.",
    )
