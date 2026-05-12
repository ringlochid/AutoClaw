from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssignmentModel,
    AttemptModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
    FlowNodeModel,
)
from app.runtime.contracts import (
    DispatchDeliveryStatus,
    FlowStatus,
    NodeKind,
    PromptFamily,
    PromptSendMode,
)
from app.runtime.control.clock import utc_now
from app.runtime.control.dispatch.callbacks import create_callback_binding
from app.runtime.control.dispatch.provider_events import append_provider_event
from app.runtime.control.flow.queries import next_node_sequence_number
from app.runtime.effects.queue import queue_dispatch_materialization
from app.runtime.ids import dispatch_id_for_task
from app.runtime.projection import build_dispatch_prompt


async def prepare_dispatch_turn(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    send_mode: PromptSendMode,
    previous_dispatch: DispatchTurnModel | None,
    staged_child_assignment_id: str | None,
    phase: str,
) -> DispatchTurnModel:
    dispatch = await _build_dispatch_turn(
        session,
        task_id=task_id,
        flow=flow,
        node=node,
        assignment=assignment,
        attempt=attempt,
        send_mode=send_mode,
        previous_dispatch=previous_dispatch,
        staged_child_assignment_id=staged_child_assignment_id,
        phase=phase,
    )
    session.add(dispatch)
    flow.current_open_dispatch_id = dispatch.dispatch_id
    flow.current_node_key = node.node_key
    flow.status = FlowStatus.RUNNING.value
    flow.updated_at = utc_now()
    attempt.status = "running"
    await session.flush()
    _add_dispatch_state_rows(
        session,
        task_id=task_id,
        dispatch=dispatch,
        node=node,
        assignment=assignment,
        attempt=attempt,
        send_mode=send_mode,
    )
    await session.flush()
    await link_previous_dispatch_opening(
        session,
        previous_dispatch_id=dispatch.previous_dispatch_id,
        dispatch_id=dispatch.dispatch_id,
    )
    return dispatch


async def _build_dispatch_turn(
    session: AsyncSession,
    *,
    task_id: str,
    flow: FlowModel,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    send_mode: PromptSendMode,
    previous_dispatch: DispatchTurnModel | None,
    staged_child_assignment_id: str | None,
    phase: str,
) -> DispatchTurnModel:
    dispatch_id = dispatch_id_for_task(
        task_id,
        node.node_key,
        await next_node_sequence_number(session, DispatchTurnModel, task_id, node.node_key),
    )
    rendered_at = utc_now()
    dispatch = DispatchTurnModel(
        dispatch_id=dispatch_id,
        flow_id=flow.flow_id,
        flow_revision_id=flow.active_flow_revision_id,
        flow_node_id=node.flow_node_id,
        task_id=task_id,
        node_key=node.node_key,
        assignment_id=assignment.assignment_id,
        assignment_key=assignment.assignment_key,
        attempt_id=attempt.attempt_id,
        phase=phase,
        status=DispatchDeliveryStatus.PREPARED.value,
        prompt_name=(
            PromptFamily.WORKER_DISPATCH.value
            if node.structural_kind == NodeKind.WORKER.value
            else PromptFamily.PARENT_ROOT_DISPATCH.value
        ),
        send_mode=send_mode.value,
        delivery_status=DispatchDeliveryStatus.PREPARED.value,
        control_state="launching",
        control_state_reason="launch_requested",
        prompt_path="",
        content_hash="",
        previous_dispatch_id=(None if previous_dispatch is None else previous_dispatch.dispatch_id),
        relevant_checkpoint_attempt_id=_relevant_checkpoint_attempt_id(
            previous_dispatch,
            attempt,
        ),
        staged_child_assignment_id=staged_child_assignment_id,
        rendered_at=rendered_at,
        opened_at=rendered_at,
    )
    return dispatch


def _add_dispatch_state_rows(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    send_mode: PromptSendMode,
) -> None:
    session.add(
        DispatchDeliveryStateModel(
            dispatch_id=dispatch.dispatch_id,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
            assignment_key=assignment.assignment_key,
            node_key=node.node_key,
            transport_family="phase3_local_runtime",
            transport_state=DispatchDeliveryStatus.PREPARED.value,
            controller_observation_state="launching",
            send_mode=send_mode.value,
            previous_dispatch_id=dispatch.previous_dispatch_id,
        )
    )
    session.add(
        DispatchContinuityStateModel(
            dispatch_id=dispatch.dispatch_id,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
            assignment_key=assignment.assignment_key,
            node_key=node.node_key,
            continuity_state="candidate",
            session_key_present=False,
        )
    )
    session.add(
        DispatchWatchdogStateModel(
            dispatch_id=dispatch.dispatch_id,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
            assignment_key=assignment.assignment_key,
            node_key=node.node_key,
            watchdog_state="clear",
            previous_dispatch_id=dispatch.previous_dispatch_id,
        )
    )


async def activate_dispatch_turn(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
) -> DispatchTurnModel:
    binding = await create_callback_binding(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
        attempt_id=attempt.attempt_id,
        assignment_id=assignment.assignment_id,
    )
    dispatch.gateway_session_key = binding.session_key
    _bundle, prompt_record = await build_dispatch_prompt(session, task_id, dispatch)
    dispatch.prompt_path = str(prompt_record.rendered_markdown_path)
    dispatch.content_hash = prompt_record.content_hash
    dispatch.status = DispatchDeliveryStatus.ACCEPTED.value
    dispatch.delivery_status = DispatchDeliveryStatus.ACCEPTED.value
    dispatch.control_state = "live"
    dispatch.control_state_reason = "launch_confirmed"
    dispatch.rendered_at = prompt_record.rendered_at
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_state = DispatchDeliveryStatus.ACCEPTED.value
        delivery_state.controller_observation_state = "live"
        delivery_state.accepted_at = prompt_record.rendered_at
        delivery_state.updated_at = utc_now()
    await append_provider_event(
        session,
        dispatch=dispatch,
        attempt_id=attempt.attempt_id,
        event_source="adapter",
        event_kind="accepted",
        summary="Dispatch accepted and waiting for provider or adapter progress.",
        detail=(
            f"Dispatch opened for node '{node.node_key}' with send mode '{dispatch.send_mode}'."
        ),
        event_payload_json={
            "transport_family": (
                delivery_state.transport_family
                if delivery_state is not None
                else "phase3_local_runtime"
            ),
            "send_mode": dispatch.send_mode,
        },
    )
    await session.flush()
    queue_dispatch_materialization(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
    )
    return dispatch


async def link_previous_dispatch_opening(
    session: AsyncSession,
    *,
    previous_dispatch_id: str | None,
    dispatch_id: str,
) -> None:
    if previous_dispatch_id is None:
        return
    previous_dispatch = await session.get(DispatchTurnModel, previous_dispatch_id)
    if previous_dispatch is not None:
        previous_dispatch.superseded_by_dispatch_id = dispatch_id
    previous_delivery_state = await session.get(
        DispatchDeliveryStateModel,
        previous_dispatch_id,
    )
    if previous_delivery_state is not None:
        previous_delivery_state.superseded_by_dispatch_id = dispatch_id
    previous_watchdog_state = await session.get(
        DispatchWatchdogStateModel,
        previous_dispatch_id,
    )
    if previous_watchdog_state is not None:
        previous_watchdog_state.superseded_by_dispatch_id = dispatch_id


def _relevant_checkpoint_attempt_id(
    previous_dispatch: DispatchTurnModel | None,
    attempt: AttemptModel,
) -> str | None:
    if (
        previous_dispatch is None
        or previous_dispatch.attempt_id is None
        or previous_dispatch.attempt_id == attempt.attempt_id
        or previous_dispatch.accepted_boundary is None
    ):
        return None
    return previous_dispatch.attempt_id
