from __future__ import annotations

from datetime import UTC
from pathlib import Path
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowNodeModel,
)
from app.runtime.contracts import (
    DispatchDeliveryStatus,
    EgressBoundary,
    FlowStatus,
    NodeKind,
    PromptFamily,
    PromptSendMode,
)
from app.runtime.control.support import (
    _append_provider_event,
    _attempt_checkpoint_projection_failure,
    _count_for_node,
    _create_callback_binding,
    _current_surfaced_ref_failure,
    _flow_by_task,
    _is_path_current,
    _now,
    _queue_dispatch_materialization,
)
from app.runtime.ids import (
    dispatch_id_for_task,
)
from app.runtime.projection import (
    build_dispatch_prompt,
)
from app.schemas.runtime import (
    WorkflowManifestRef,
)

_REPLACEMENT_BLOCKING_CONTROL_STATES = {"launching", "live", "abort_requested", "ambiguous"}
_WAITING_INACTIVITY_CONTROL_STATES = {"launching", "live"}
_INACTIVITY_PROVEN_DELIVERY_STATUSES = {
    DispatchDeliveryStatus.PROVIDER_COMPLETED.value,
    DispatchDeliveryStatus.PROVIDER_FAILED.value,
    DispatchDeliveryStatus.TRANSPORT_FAILED.value,
}


async def _flow_node_assignment_attempt_rows(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    parent_flow_node_id: str | None = None,
) -> list[tuple[FlowNodeModel, AssignmentModel | None, AttemptModel | None]]:
    query = (
        select(FlowNodeModel, AssignmentModel, AttemptModel)
        .options(raiseload("*"))
        .outerjoin(
            AssignmentModel,
            AssignmentModel.assignment_id == FlowNodeModel.current_assignment_id,
        )
        .outerjoin(
            AttemptModel,
            AttemptModel.attempt_id == AssignmentModel.current_attempt_id,
        )
        .where(FlowNodeModel.flow_revision_id == flow_revision_id)
        .order_by(FlowNodeModel.order_index.asc(), FlowNodeModel.node_key.asc())
    )
    if parent_flow_node_id is not None:
        query = query.where(FlowNodeModel.parent_flow_node_id == parent_flow_node_id)
    return cast(
        list[tuple[FlowNodeModel, AssignmentModel | None, AttemptModel | None]],
        (await session.execute(query)).all(),
    )


async def _current_pointer_pairs(
    session: AsyncSession,
    *,
    task_id: str,
    assignment_keys: set[str],
    slots: set[str],
) -> set[tuple[str, str]]:
    if not assignment_keys or not slots:
        return set()
    return {
        (assignment_key, slot)
        for assignment_key, slot, current_path in cast(
            list[tuple[str, str, str]],
            (
                await session.execute(
                    select(
                        ArtifactCurrentPointerModel.assignment_key,
                        ArtifactCurrentPointerModel.slot,
                        ArtifactCurrentPointerModel.current_path,
                    ).where(
                        ArtifactCurrentPointerModel.task_id == task_id,
                        ArtifactCurrentPointerModel.assignment_key.in_(assignment_keys),
                        ArtifactCurrentPointerModel.slot.in_(slots),
                    )
                )
            ).all(),
        )
        if _is_path_current(current_path)
    }


async def _ensure_release_green_preconditions(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    current_node_key: str,
    current_assignment: AssignmentModel,
) -> None:
    current_node = await _flow_node_by_key(session, flow_revision_id, current_node_key)
    await _ensure_current_assignment_basis_is_current(
        session,
        task_id=task_id,
        assignment=current_assignment,
        action_name="release_green",
    )
    await _ensure_assignment_required_publications(
        session,
        task_id=task_id,
        assignment=current_assignment,
    )
    child_assignment_rows = await _flow_node_assignment_attempt_rows(
        session,
        flow_revision_id=flow_revision_id,
        parent_flow_node_id=current_node.flow_node_id,
    )
    child_pointer_pairs = await _current_pointer_pairs(
        session,
        task_id=task_id,
        assignment_keys={
            assignment.assignment_key
            for _, assignment, _ in child_assignment_rows
            if assignment is not None and assignment.produces_json
        },
        slots={
            str(requirement["slot"])
            for _, assignment, _ in child_assignment_rows
            if assignment is not None
            for requirement in assignment.produces_json
        },
    )
    for child, child_assignment, attempt in child_assignment_rows:
        if child.current_assignment_id is None:
            raise ValueError(f"child node '{child.node_key}' has no current assignment")
        if child_assignment is None:
            raise ValueError(f"missing child assignment '{child.current_assignment_id}'")
        await _ensure_current_assignment_basis_is_current(
            session,
            task_id=task_id,
            assignment=child_assignment,
            action_name="release_green",
        )
        if child_assignment.current_attempt_id is None or attempt is None:
            raise ValueError(
                f"child assignment '{child_assignment.assignment_key}' has no current attempt"
            )
        if (
            attempt.latest_checkpoint_id is None
            or attempt.terminal_outcome != EgressBoundary.GREEN.value
        ):
            raise ValueError(
                f"child assignment '{child_assignment.assignment_key}' is not terminal-green"
            )
        await _ensure_current_checkpoint_projection(
            session,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
            action_name="release_green",
        )
        for requirement in child_assignment.produces_json:
            if (
                child_assignment.assignment_key,
                str(requirement["slot"]),
            ) not in child_pointer_pairs:
                raise ValueError(
                    "missing required publication for child assignment "
                    f"'{child_assignment.assignment_key}'"
                )


async def _ensure_current_assignment_basis_is_current(
    session: AsyncSession,
    *,
    task_id: str,
    assignment: AssignmentModel,
    action_name: str,
) -> None:
    for ref in [*assignment.criteria_json, *assignment.consumes_json]:
        failure = await _current_surfaced_ref_failure(session, task_id=task_id, ref=ref)
        if failure is not None:
            raise ValueError(f"{action_name} requires current surfaced evidence: {failure}")


async def _ensure_current_checkpoint_projection(
    session: AsyncSession,
    *,
    task_id: str,
    attempt_id: str,
    action_name: str,
    allow_current_dispatch_truth: bool = False,
) -> None:
    failure = await _attempt_checkpoint_projection_failure(
        session,
        task_id=task_id,
        attempt_id=attempt_id,
    )
    if (
        failure == "current checkpoint projection files are missing"
        and allow_current_dispatch_truth
    ):
        flow = await _flow_by_task(session, task_id)
        if flow.current_open_dispatch_id is not None:
            dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
            if dispatch is not None and dispatch.attempt_id == attempt_id:
                return
    if failure is not None:
        raise ValueError(f"{action_name} requires current checkpoint evidence: {failure}")


async def _ensure_assignment_required_publications(
    session: AsyncSession,
    *,
    task_id: str,
    assignment: AssignmentModel,
    allow_pending_current_attempt_publications: bool = False,
) -> None:
    slots = {str(requirement["slot"]) for requirement in assignment.produces_json}
    pointer_pairs = await _current_pointer_pairs(
        session,
        task_id=task_id,
        assignment_keys={assignment.assignment_key},
        slots=slots,
    )
    current_pointers = {
        pointer.slot: pointer
        for pointer in await session.scalars(
            select(ArtifactCurrentPointerModel).where(
                ArtifactCurrentPointerModel.task_id == task_id,
                ArtifactCurrentPointerModel.assignment_key == assignment.assignment_key,
                ArtifactCurrentPointerModel.slot.in_(slots),
            )
        )
    }
    for requirement in assignment.produces_json:
        slot = str(requirement["slot"])
        if (assignment.assignment_key, slot) in pointer_pairs:
            continue
        pending_pointer = current_pointers.get(slot)
        if allow_pending_current_attempt_publications and pending_pointer is not None:
            continue
        raise ValueError(
            f"missing required publication for assignment '{assignment.assignment_key}'"
        )


async def _ensure_release_blocked_preconditions(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    current_node_key: str,
    current_assignment: AssignmentModel,
) -> None:
    await _ensure_current_assignment_basis_is_current(
        session,
        task_id=task_id,
        assignment=current_assignment,
        action_name="release_blocked",
    )
    if current_assignment.current_attempt_id is None:
        raise ValueError("release_blocked requires a current root attempt")
    root_attempt = await session.get(AttemptModel, current_assignment.current_attempt_id)
    if root_attempt is None:
        raise ValueError(f"missing root attempt '{current_assignment.current_attempt_id}'")
    root_checkpoint = None
    if root_attempt.latest_checkpoint_id is not None:
        root_checkpoint = await session.get(
            AttemptCheckpointModel,
            root_attempt.latest_checkpoint_id,
        )
    if (
        root_checkpoint is None
        or root_checkpoint.checkpoint_kind != "terminal"
        or root_checkpoint.outcome != EgressBoundary.BLOCKED.value
    ):
        raise ValueError("release_blocked requires the current root basis to be terminal-blocked")
    await _ensure_current_checkpoint_projection(
        session,
        task_id=task_id,
        attempt_id=root_attempt.attempt_id,
        action_name="release_blocked",
        allow_current_dispatch_truth=True,
    )

    blocked_found = False
    for node, assignment, attempt in await _flow_node_assignment_attempt_rows(
        session,
        flow_revision_id=flow_revision_id,
    ):
        if node.current_assignment_id is None:
            continue
        if assignment is None or assignment.current_attempt_id is None or attempt is None:
            raise ValueError(f"node '{node.node_key}' has no current attempt")
        await _ensure_current_assignment_basis_is_current(
            session,
            task_id=task_id,
            assignment=assignment,
            action_name="release_blocked",
        )
        if node.node_key == current_node_key:
            blocked_found = True
            continue
        if attempt.latest_checkpoint_id is None or attempt.terminal_outcome is None:
            raise ValueError(
                "release_blocked requires terminal whole-flow truth; "
                f"node '{node.node_key}' is still active"
            )
        await _ensure_current_checkpoint_projection(
            session,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
            action_name="release_blocked",
        )
        blocked_found = blocked_found or attempt.terminal_outcome == EgressBoundary.BLOCKED.value
    if not blocked_found:
        raise ValueError("release_blocked requires a current blocked basis")


async def _ensure_previous_dispatch_replaced_legally(
    session: AsyncSession,
    *,
    task_id: str,
    previous_dispatch_id: str | None,
) -> None:
    if previous_dispatch_id is None:
        return
    previous_dispatch = await session.get(DispatchTurnModel, previous_dispatch_id)
    if previous_dispatch is None or previous_dispatch.task_id != task_id:
        raise ValueError(f"missing previous dispatch '{previous_dispatch_id}'")
    if previous_dispatch.control_state in _REPLACEMENT_BLOCKING_CONTROL_STATES:
        raise ValueError(
            "replacement dispatch is illegal until the previous dispatch is proven inactive"
        )
    if previous_dispatch.control_state != "fenced":
        raise ValueError("replacement dispatch requires a fenced previous dispatch")


def _dispatch_deadline_expired(dispatch: DispatchTurnModel) -> bool:
    deadline = dispatch.control_deadline_at
    if deadline is not None and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    return (
        dispatch.control_state in _REPLACEMENT_BLOCKING_CONTROL_STATES
        and deadline is not None
        and deadline <= _now()
    )


def _dispatch_waiting_for_inactivity(dispatch: DispatchTurnModel) -> bool:
    return (
        dispatch.accepted_boundary is not None
        and dispatch.control_state in _WAITING_INACTIVITY_CONTROL_STATES
        and dispatch.fenced_at is None
    )


def _dispatch_inactivity_proven(dispatch: DispatchTurnModel) -> bool:
    return dispatch.delivery_status in _INACTIVITY_PROVEN_DELIVERY_STATUSES


async def _mark_dispatch_fenced(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    reason: str,
) -> None:
    fenced_at = _now()
    delivery_status = (
        dispatch.delivery_status
        if dispatch.delivery_status in _INACTIVITY_PROVEN_DELIVERY_STATUSES
        else DispatchDeliveryStatus.PROVIDER_COMPLETED.value
    )
    dispatch.control_state = "fenced"
    dispatch.control_state_reason = reason
    dispatch.control_deadline_at = None
    dispatch.fenced_at = dispatch.fenced_at or fenced_at
    dispatch.delivery_status = delivery_status
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_state = delivery_status
        delivery_state.controller_observation_state = "fenced"
        delivery_state.last_controller_terminal_at = fenced_at
        delivery_state.updated_at = fenced_at
    await session.flush()


async def _mark_dispatch_ambiguous(
    session: AsyncSession,
    *,
    dispatch: DispatchTurnModel,
    reason: str,
) -> None:
    ambiguous_at = _now()
    dispatch.control_state = "ambiguous"
    dispatch.control_state_reason = reason
    dispatch.control_deadline_at = None
    dispatch.delivery_status = DispatchDeliveryStatus.TRANSPORT_AMBIGUOUS.value
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.transport_state = DispatchDeliveryStatus.TRANSPORT_AMBIGUOUS.value
        delivery_state.controller_observation_state = "ambiguous"
        delivery_state.last_controller_terminal_at = ambiguous_at
        delivery_state.updated_at = ambiguous_at
    await session.flush()


async def _open_dispatch_for_attempt(
    session: AsyncSession,
    *,
    task_id: str,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    send_mode: PromptSendMode,
    previous_dispatch_id: str | None,
    staged_child_assignment_id: str | None = None,
    phase: str = "execution",
) -> DispatchTurnModel:
    flow = await _flow_by_task(session, task_id)
    if flow.current_open_dispatch_id is not None:
        raise ValueError("cannot open a replacement dispatch while another dispatch is current")
    await _ensure_previous_dispatch_replaced_legally(
        session,
        task_id=task_id,
        previous_dispatch_id=previous_dispatch_id,
    )
    dispatch_id = dispatch_id_for_task(
        task_id,
        node.node_key,
        await _count_for_node(session, DispatchTurnModel, task_id, node.node_key),
    )
    rendered_at = _now()
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
        previous_dispatch_id=previous_dispatch_id,
        staged_child_assignment_id=staged_child_assignment_id,
        rendered_at=rendered_at,
        opened_at=rendered_at,
    )
    session.add(dispatch)
    flow.current_open_dispatch_id = dispatch.dispatch_id
    flow.current_node_key = node.node_key
    flow.status = FlowStatus.RUNNING.value
    flow.updated_at = _now()
    attempt.status = "running"
    await session.flush()
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
            previous_dispatch_id=previous_dispatch_id,
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
            previous_dispatch_id=previous_dispatch_id,
        )
    )
    await session.flush()
    if previous_dispatch_id is not None:
        previous_dispatch = await session.get(DispatchTurnModel, previous_dispatch_id)
        if previous_dispatch is not None:
            previous_dispatch.superseded_by_dispatch_id = dispatch.dispatch_id
        previous_delivery_state = await session.get(
            DispatchDeliveryStateModel,
            previous_dispatch_id,
        )
        if previous_delivery_state is not None:
            previous_delivery_state.superseded_by_dispatch_id = dispatch.dispatch_id
        previous_watchdog_state = await session.get(
            DispatchWatchdogStateModel,
            previous_dispatch_id,
        )
        if previous_watchdog_state is not None:
            previous_watchdog_state.superseded_by_dispatch_id = dispatch.dispatch_id
    binding = await _create_callback_binding(
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
        delivery_state.updated_at = _now()
    await _append_provider_event(
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
    _queue_dispatch_materialization(session, task_id=task_id, dispatch_id=dispatch.dispatch_id)
    return dispatch


async def _flow_node_by_key(
    session: AsyncSession,
    flow_revision_id: str,
    node_key: str,
) -> FlowNodeModel:
    node = await session.scalar(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == flow_revision_id,
            FlowNodeModel.node_key == node_key,
        )
    )
    if node is None:
        raise ValueError(f"unknown node_key '{node_key}'")
    return node


def _workflow_manifest_ref(task_root_paths: Path, task_id: str) -> WorkflowManifestRef:
    del task_id
    return WorkflowManifestRef(
        path=task_root_paths / "_runtime" / "workflow-manifest.md",
        description="Whole-workflow visible contract for the current task.",
    )
