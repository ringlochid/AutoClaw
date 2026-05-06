from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ArtifactCurrentPointerModel,
    ArtifactPublicationModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptConsumedRefModel,
    AttemptModel,
    AttemptProducedRefModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    FlowNodeModel,
)
from app.runtime.contracts import (
    CheckpointKind,
    EgressBoundary,
    EvidenceKind,
    EvidenceRef,
    FlowStatus,
    NodeKind,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    PromptSendMode,
)
from app.runtime.control.flows import runtime_flow_read
from app.runtime.control.release import (
    _ensure_assignment_required_publications,
    _ensure_release_blocked_preconditions,
    _ensure_release_green_preconditions,
    _flow_node_by_key,
    _open_dispatch_for_attempt,
)
from app.runtime.control.support import (
    _coerce_source_path,
    _consume_assignment_budget,
    _count_for_node,
    _dispatch_control_deadline,
    _flow_by_task,
    _latest_checkpoint_for_attempt,
    _now,
    _queue_artifact_current_pointer_materialization,
    _queue_attempt_materialization,
    _queue_dispatch_materialization,
    _queue_file_copy,
    _queue_manifest_materialization,
    _revoke_callback_binding,
    _terminal_release_basis_committed,
)
from app.runtime.ids import (
    artifact_current_pointer_id,
    artifact_publication_id,
    attempt_consumed_ref_id,
    attempt_id_for_task,
)
from app.runtime.ids import (
    checkpoint_id as runtime_checkpoint_id,
)
from app.runtime.projection import (
    current_runtime_state,
    load_task_root_paths,
)
from app.runtime.resources import planned_transient_surface_path
from app.schemas.runtime import (
    BoundaryRead,
    BoundaryWrite,
    CheckpointFileRef,
    CheckpointRead,
    CheckpointWrite,
)


async def record_checkpoint(
    session: AsyncSession,
    task_id: str,
    payload: CheckpointWrite,
) -> CheckpointRead:
    state = await current_runtime_state(session, task_id)
    flow = state.flow
    if flow.current_open_dispatch_id is None:
        raise ValueError("no current open dispatch")
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
    if dispatch is None:
        raise ValueError(f"missing dispatch '{flow.current_open_dispatch_id}'")
    latest_checkpoint = await _latest_checkpoint_for_attempt(session, state.current_attempt)
    if (
        state.current_attempt.closed_at is not None
        or state.current_attempt.terminal_outcome is not None
    ):
        raise ValueError("closed attempt cannot record new checkpoints")
    if (
        latest_checkpoint is not None
        and latest_checkpoint.checkpoint_kind == CheckpointKind.TERMINAL.value
    ):
        raise ValueError("attempt already has a terminal checkpoint")
    checkpoint_write = payload.checkpoint
    checkpoint_seq = (
        int(
            await session.scalar(
                select(func.count())
                .select_from(AttemptCheckpointModel)
                .where(AttemptCheckpointModel.attempt_id == state.current_attempt.attempt_id)
            )
            or 0
        )
        + 1
    )
    paths = await load_task_root_paths(session, task_id)
    produced_refs: list[EvidenceRef] = []
    produced_file_copies: list[tuple[Path, Path]] = []
    claim_slots: set[str] = set()
    produce_requirements = {
        str(requirement["slot"]): requirement
        for requirement in state.current_assignment.produces_json
    }
    for claim in checkpoint_write.produced_artifacts:
        if claim.slot in claim_slots:
            raise ValueError(f"duplicate produced artifact slot '{claim.slot}' in one checkpoint")
        claim_slots.add(claim.slot)
        requirement = produce_requirements.get(claim.slot)
        if requirement is None:
            raise ValueError(
                f"produced artifact slot '{claim.slot}' is not declared for current assignment"
            )
        source_path = await asyncio.to_thread(_coerce_source_path, claim.path)
        if not source_path.is_file():
            raise FileNotFoundError(f"produced artifact does not exist: {source_path}")
        version = (
            int(
                await session.scalar(
                    select(func.max(ArtifactPublicationModel.version)).where(
                        ArtifactPublicationModel.task_id == task_id,
                        ArtifactPublicationModel.owner_node_key == state.current_node.node_key,
                        ArtifactPublicationModel.slot == claim.slot,
                    )
                )
                or 0
            )
            + 1
        )
        description = str(requirement["description"])
        destination_dir = paths.artifacts_path / state.current_node.node_key / claim.slot
        suffix = source_path.suffix
        destination = destination_dir / f"{claim.slot}.v{version:02d}{suffix}"
        produced_file_copies.append((source_path, destination))
        artifact_ref = EvidenceRef(
            kind=EvidenceKind.ARTIFACT,
            slot=claim.slot,
            version=version,
            path=destination,
            description=description,
        )
        produced_refs.append(artifact_ref)
        previous_pointer = await session.scalar(
            select(ArtifactCurrentPointerModel).where(
                ArtifactCurrentPointerModel.task_id == task_id,
                ArtifactCurrentPointerModel.owner_node_key == state.current_node.node_key,
                ArtifactCurrentPointerModel.slot == claim.slot,
            )
        )
        previous_current_version = previous_pointer.current_version if previous_pointer else None
        previous_current_path = previous_pointer.current_path if previous_pointer else None
        session.add(
            ArtifactPublicationModel(
                artifact_publication_id=artifact_publication_id(
                    state.current_attempt.attempt_id,
                    claim.slot,
                    version,
                ),
                task_id=task_id,
                flow_node_id=state.current_assignment.flow_node_id,
                owner_node_key=state.current_node.node_key,
                slot=claim.slot,
                version=version,
                path=str(destination),
                description=description,
                assignment_key=state.current_assignment.assignment_key,
                attempt_id=state.current_attempt.attempt_id,
                supersedes_version=previous_current_version,
                supersedes_path=previous_current_path,
            )
        )
        pointer = previous_pointer or ArtifactCurrentPointerModel(
            artifact_current_pointer_id=artifact_current_pointer_id(
                task_id,
                state.current_node.node_key,
                claim.slot,
            ),
            task_id=task_id,
            flow_node_id=state.current_assignment.flow_node_id,
            owner_node_key=state.current_node.node_key,
            slot=claim.slot,
            current_version=version,
            current_path=str(destination),
            description=description,
            assignment_key=state.current_assignment.assignment_key,
            attempt_id=state.current_attempt.attempt_id,
            published_at=_now(),
            supersedes_path=previous_current_path,
        )
        if previous_pointer is None:
            session.add(pointer)
        else:
            pointer.flow_node_id = state.current_assignment.flow_node_id
            pointer.current_version = version
            pointer.current_path = str(destination)
            pointer.description = str(description)
            pointer.assignment_key = state.current_assignment.assignment_key
            pointer.attempt_id = state.current_attempt.attempt_id
            pointer.published_at = _now()
            pointer.supersedes_path = previous_current_path
    transient_refs = tuple(
        EvidenceRef(
            kind=EvidenceKind.TRANSIENT,
            path=planned_transient_surface_path(
                paths=paths,
                source_path=surface.path,
                owner_node_key=state.current_node.node_key,
            ),
            description=surface.description,
        )
        for surface in checkpoint_write.transient_surfaces
    )
    transient_file_copies: list[tuple[Path, Path]] = []
    for surface, transient_ref in zip(
        checkpoint_write.transient_surfaces,
        transient_refs,
        strict=True,
    ):
        transient_source = await asyncio.to_thread(_coerce_source_path, surface.path)
        if not transient_source.is_file():
            raise FileNotFoundError(f"transient surface does not exist: {transient_source}")
        transient_file_copies.append((transient_source, transient_ref.path))
    checkpoint_id = runtime_checkpoint_id(state.current_attempt.attempt_id, checkpoint_seq)
    session.add(
        AttemptCheckpointModel(
            checkpoint_id=checkpoint_id,
            assignment_id=state.current_assignment.assignment_id,
            assignment_key=state.current_assignment.assignment_key,
            attempt_id=state.current_attempt.attempt_id,
            flow_node_id=state.current_assignment.flow_node_id,
            node_key=state.current_node.node_key,
            checkpoint_kind=checkpoint_write.checkpoint_kind.value,
            outcome=(
                checkpoint_write.outcome.value if checkpoint_write.outcome is not None else None
            ),
            summary=checkpoint_write.handoff.summary,
            next_step=checkpoint_write.handoff.next_step,
            blockers_json=list(checkpoint_write.handoff.blockers),
            risks_json=list(checkpoint_write.handoff.risks),
            produced_artifact_claims_json=[
                claim.model_dump(mode="json") for claim in checkpoint_write.produced_artifacts
            ],
            produced_artifacts_json=[ref.model_dump(mode="json") for ref in produced_refs],
            artifact_refs_json=[ref.model_dump(mode="json") for ref in produced_refs],
            transient_refs_json=[ref.model_dump(mode="json") for ref in transient_refs],
            task_memory_search_hints_json=list(checkpoint_write.task_memory_search_hints),
        )
    )
    state.current_attempt.latest_checkpoint_id = checkpoint_id
    for index, ref in enumerate(produced_refs, start=1):
        session.add(
            AttemptProducedRefModel(
                attempt_produced_ref_id=artifact_publication_id(
                    state.current_attempt.attempt_id,
                    ref.slot or f"artifact-{index}",
                    ref.version or index,
                ),
                attempt_id=state.current_attempt.attempt_id,
                owner_node_key=state.current_node.node_key,
                assignment_key=state.current_assignment.assignment_key,
                slot=ref.slot or f"artifact-{index}",
                version=ref.version or index,
                path=str(ref.path),
                description=ref.description,
                published_at=_now(),
                became_current=True,
                order_index=index,
            )
        )
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        if checkpoint_write.checkpoint_kind == CheckpointKind.PROGRESS:
            delivery_state.last_controller_progress_at = _now()
        else:
            delivery_state.last_controller_terminal_at = _now()
        delivery_state.updated_at = _now()
    await session.flush()
    for source_path, destination in produced_file_copies:
        _queue_file_copy(
            session,
            source_path=source_path,
            destination=destination,
        )
    for source_path, destination in transient_file_copies:
        _queue_file_copy(
            session,
            source_path=source_path,
            destination=destination,
        )
    _queue_attempt_materialization(
        session,
        task_id=task_id,
        attempt_id=state.current_attempt.attempt_id,
    )
    _queue_manifest_materialization(session, task_id=task_id)
    for ref in produced_refs:
        if ref.slot is not None:
            _queue_artifact_current_pointer_materialization(
                session,
                task_id=task_id,
                owner_node_key=state.current_node.node_key,
                slot=ref.slot,
            )
    if delivery_state is not None:
        _queue_dispatch_materialization(
            session,
            task_id=task_id,
            dispatch_id=dispatch.dispatch_id,
        )
    checkpoint_ref = CheckpointFileRef(
        path=(paths.attempts_path / state.current_attempt.attempt_id / "latest-checkpoint.md"),
        description="Latest checkpoint for the current attempt.",
    )
    return CheckpointRead(
        attempt_id=state.current_attempt.attempt_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ref=checkpoint_ref,
        latest_checkpoint_ref=checkpoint_ref,
    )


async def _parent_node_from_relation(
    session: AsyncSession,
    *,
    node: FlowNodeModel,
) -> FlowNodeModel | None:
    if node.parent_flow_node_id is None:
        if node.parent_node_key is not None:
            raise ValueError(
                "runtime node mirror parent_node_key exists without relational parent_flow_node_id"
            )
        return None
    parent = await session.get(FlowNodeModel, node.parent_flow_node_id)
    if parent is None:
        raise ValueError(
            "missing relational parent flow node "
            f"'{node.parent_flow_node_id}' for node '{node.node_key}'"
        )
    return parent


async def _redispatch_parent(
    session: AsyncSession,
    *,
    task_id: str,
    parent_node_key: str,
    previous_dispatch_id: str,
) -> DispatchTurnModel:
    flow = await _flow_by_task(session, task_id)
    parent = await _flow_node_by_key(
        session,
        flow.active_flow_revision_id or "",
        parent_node_key,
    )
    if parent.current_assignment_id is None:
        raise ValueError(f"parent node '{parent_node_key}' has no current assignment")
    assignment = await session.get(AssignmentModel, parent.current_assignment_id)
    if assignment is None or assignment.current_attempt_id is None:
        raise ValueError(
            f"parent assignment '{parent.current_assignment_id}' has no current attempt"
        )
    attempt = await session.get(AttemptModel, assignment.current_attempt_id)
    if attempt is None:
        raise ValueError(f"missing attempt '{assignment.current_attempt_id}'")
    return await _open_dispatch_for_attempt(
        session,
        task_id=task_id,
        node=parent,
        assignment=assignment,
        attempt=attempt,
        send_mode=PromptSendMode.FULL_PROMPT,
        previous_dispatch_id=previous_dispatch_id,
    )


async def accept_boundary(
    session: AsyncSession,
    task_id: str,
    payload: BoundaryWrite,
) -> BoundaryRead:
    state = await current_runtime_state(session, task_id)
    flow = state.flow
    if flow.current_open_dispatch_id is None:
        raise ValueError("no current open dispatch")
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
    if dispatch is None:
        raise ValueError(f"missing dispatch '{flow.current_open_dispatch_id}'")
    checkpoint_ref = None
    latest_checkpoint = await _latest_checkpoint_for_attempt(session, state.current_attempt)
    if latest_checkpoint is not None:
        paths = await load_task_root_paths(session, task_id)
        checkpoint_ref = CheckpointFileRef(
            path=paths.attempts_path / state.current_attempt.attempt_id / "latest-checkpoint.md",
            description="Latest checkpoint for the current attempt.",
        )
    if payload.boundary == EgressBoundary.YIELD:
        if dispatch.staged_child_assignment_id is None:
            raise ValueError("yield requires exactly one staged child assignment")
        if _terminal_release_basis_committed(dispatch):
            raise ValueError("yield is illegal after terminal release basis was committed")
    elif (
        state.current_node.structural_kind != NodeKind.WORKER.value
        and payload.boundary == EgressBoundary.RETRY
    ):
        raise ValueError("parent/root retry is illegal")
    elif (
        latest_checkpoint is None
        or latest_checkpoint.checkpoint_kind != CheckpointKind.TERMINAL.value
    ):
        raise ValueError("terminal boundaries require a terminal checkpoint")
    elif latest_checkpoint.outcome != payload.boundary.value:
        raise ValueError("boundary does not match latest terminal checkpoint outcome")

    closed_at = _now()
    dispatch.accepted_boundary = payload.boundary.value
    dispatch.closed_by_boundary = payload.boundary.value
    dispatch.closed_at = closed_at
    dispatch.status = "closed"
    if dispatch.control_state == "live":
        dispatch.control_deadline_at = _dispatch_control_deadline(base=closed_at)
        dispatch.control_state_reason = f"boundary:{payload.boundary.value}:awaiting_inactivity"
    elif dispatch.control_state == "launching":
        dispatch.control_deadline_at = dispatch.control_deadline_at or _dispatch_control_deadline(
            base=closed_at
        )
        dispatch.control_state_reason = f"boundary:{payload.boundary.value}:launch_unconfirmed"
    elif dispatch.control_state == "fenced":
        dispatch.control_deadline_at = None
        dispatch.fenced_at = dispatch.fenced_at or closed_at
    await _revoke_callback_binding(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
    )
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    if delivery_state is not None:
        delivery_state.controller_observation_state = dispatch.control_state
        delivery_state.updated_at = closed_at

    if payload.boundary in {EgressBoundary.GREEN, EgressBoundary.RETRY, EgressBoundary.BLOCKED}:
        state.current_attempt.terminal_outcome = payload.boundary.value
        state.current_attempt.closed_at = closed_at
        state.current_attempt.status = (
            "succeeded"
            if payload.boundary == EgressBoundary.GREEN
            else "blocked"
            if payload.boundary == EgressBoundary.BLOCKED
            else "failed"
        )

    if state.current_node.structural_kind == NodeKind.WORKER.value:
        if payload.boundary == EgressBoundary.RETRY:
            await _consume_assignment_budget(
                session,
                budget_family="retry",
                limit_field="retry_limit",
                policy_key=state.current_node.policy_key,
                policy_revision_no=state.current_node.policy_revision_no,
                flow_id=state.flow.flow_id,
                flow_node_id=state.current_assignment.flow_node_id,
                assignment_id=state.current_assignment.assignment_id,
                attempt_id=state.current_attempt.attempt_id,
            )
            retry_attempt_id = attempt_id_for_task(
                task_id,
                state.current_node.node_key,
                await _count_for_node(session, AttemptModel, task_id, state.current_node.node_key),
            )
            retry_checkpoint_ref = None
            if checkpoint_ref is not None:
                retry_checkpoint_ref = NodeRuntimeFileRef(
                    kind=NodeRuntimeFileKind.CHECKPOINT,
                    path=checkpoint_ref.path,
                    description="Prior terminal retry checkpoint for the same assignment.",
                )
            retry_consumed_refs = [
                ref
                for ref in state.current_assignment.consumes_json
                if ref.get("kind") != NodeRuntimeFileKind.CHECKPOINT.value
            ]
            if retry_checkpoint_ref is not None:
                retry_consumed_refs.insert(0, retry_checkpoint_ref.model_dump(mode="json"))
            state.current_assignment.current_attempt_id = retry_attempt_id
            retry_attempt = AttemptModel(
                attempt_id=retry_attempt_id,
                assignment_id=state.current_assignment.assignment_id,
                assignment_key=state.current_assignment.assignment_key,
                flow_node_id=state.current_assignment.flow_node_id,
                task_id=task_id,
                node_key=state.current_node.node_key,
                retry_of_attempt_id=state.current_attempt.attempt_id,
                status="running",
            )
            session.add(retry_attempt)
            await session.flush()
            for index, ref in enumerate(
                [*state.current_assignment.criteria_json, *retry_consumed_refs],
                start=1,
            ):
                session.add(
                    AttemptConsumedRefModel(
                        attempt_consumed_ref_id=attempt_consumed_ref_id(retry_attempt_id, index),
                        attempt_id=retry_attempt_id,
                        ref_kind=str(ref["kind"]),
                        slot=ref.get("slot"),
                        version=ref.get("version"),
                        path=str(ref["path"]),
                        description=str(ref["description"]),
                        order_index=index,
                    )
                )
            await session.flush()
            _queue_attempt_materialization(
                session,
                task_id=task_id,
                attempt_id=retry_attempt_id,
            )
            _queue_manifest_materialization(session, task_id=task_id)
            flow.current_node_key = state.current_node.node_key
        else:
            parent_node = await _parent_node_from_relation(session, node=state.current_node)
            if parent_node is not None:
                if payload.boundary == EgressBoundary.GREEN:
                    await _ensure_assignment_required_publications(
                        session,
                        task_id=task_id,
                        assignment=state.current_assignment,
                        allow_pending_current_attempt_publications=True,
                    )
                flow.current_node_key = parent_node.node_key
            else:
                if payload.boundary == EgressBoundary.GREEN:
                    await _ensure_assignment_required_publications(
                        session,
                        task_id=task_id,
                        assignment=state.current_assignment,
                        allow_pending_current_attempt_publications=True,
                    )
                flow.status = (
                    FlowStatus.SUCCEEDED.value
                    if payload.boundary == EgressBoundary.GREEN
                    else FlowStatus.BLOCKED.value
                )
    else:
        if payload.boundary == EgressBoundary.YIELD:
            assignment = await session.get(AssignmentModel, dispatch.staged_child_assignment_id)
            if assignment is None or assignment.current_attempt_id is None:
                raise ValueError("staged child assignment is incomplete")
        elif payload.boundary == EgressBoundary.GREEN:
            if dispatch.release_precondition_kind != "release_green":
                raise ValueError("green requires release_green first")
            if (
                dispatch.release_precondition_flow_revision_id != flow.active_flow_revision_id
                or dispatch.release_precondition_assignment_id
                != state.current_assignment.assignment_id
            ):
                raise ValueError("green release precondition is stale")
            await _ensure_release_green_preconditions(
                session,
                task_id=task_id,
                flow_revision_id=flow.active_flow_revision_id or "",
                current_node_key=state.current_node.node_key,
                current_assignment=state.current_assignment,
            )
            parent_node = await _parent_node_from_relation(session, node=state.current_node)
            if parent_node is None:
                flow.status = FlowStatus.SUCCEEDED.value
            else:
                flow.current_node_key = parent_node.node_key
        else:
            if (
                state.current_node.structural_kind != NodeKind.ROOT.value
                or dispatch.release_precondition_kind != "release_blocked"
            ):
                raise ValueError("blocked requires root release_blocked first")
            if (
                dispatch.release_precondition_flow_revision_id != flow.active_flow_revision_id
                or dispatch.release_precondition_assignment_id
                != state.current_assignment.assignment_id
            ):
                raise ValueError("blocked release precondition is stale")
            await _ensure_release_blocked_preconditions(
                session,
                task_id=task_id,
                flow_revision_id=flow.active_flow_revision_id or "",
                current_node_key=state.current_node.node_key,
                current_assignment=state.current_assignment,
            )
            flow.status = FlowStatus.BLOCKED.value

    flow.updated_at = _now()
    await session.flush()
    if delivery_state is not None:
        _queue_dispatch_materialization(
            session,
            task_id=task_id,
            dispatch_id=dispatch.dispatch_id,
        )
    _queue_manifest_materialization(session, task_id=task_id)
    return BoundaryRead(
        accepted_boundary=payload.boundary,
        flow=await runtime_flow_read(session, task_id),
        latest_checkpoint_ref=checkpoint_ref,
    )
