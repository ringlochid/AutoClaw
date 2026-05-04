from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path
from secrets import token_urlsafe
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ArtifactCurrentPointerModel,
    ArtifactPublicationModel,
    AssignmentCriteriaRefModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptConsumedRefModel,
    AttemptModel,
    AttemptProducedRefModel,
    DispatchCallbackBindingModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowModel,
    FlowNodeModel,
    TaskModel,
)
from app.runtime.contracts import (
    CheckpointKind,
    CheckpointOutcome,
    DispatchDeliveryStatus,
    EgressBoundary,
    EvidenceKind,
    EvidenceRef,
    FlowStatus,
    NodeKind,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    ParentRootToolName,
    PromptFamily,
    PromptSendMode,
)
from app.runtime.ids import (
    artifact_current_pointer_id,
    artifact_publication_id,
    assignment_criteria_ref_id,
    assignment_id,
    attempt_consumed_ref_id,
    dispatch_callback_binding_id,
)
from app.runtime.ids import (
    attempt_id as runtime_attempt_id,
)
from app.runtime.ids import (
    checkpoint_id as runtime_checkpoint_id,
)
from app.runtime.ids import (
    dispatch_id as runtime_dispatch_id,
)
from app.runtime.projector import (
    build_manifest_projection,
    current_runtime_state,
    load_task_root_paths,
    materialize_artifact_current_pointer,
    materialize_attempt_files,
    materialize_dispatch_files,
    materialize_manifest,
    render_dispatch_prompt,
)
from app.runtime.replan import (
    add_child_to_current_flow,
    remove_child_from_current_flow,
    update_child_in_current_flow,
)
from app.runtime.resources import localize_transient_surface
from app.schemas.runtime import (
    AddChildPayload,
    AssignChildPayload,
    AssignChildSuccess,
    AssignmentFileRef,
    BoundaryHistoryEntry,
    BoundaryRead,
    BoundaryWrite,
    CheckpointFileRef,
    CheckpointHistoryEntry,
    CheckpointRead,
    CheckpointWrite,
    DispatchHistoryEntry,
    DocRef,
    ObservabilityFileRef,
    OperatorFlowSnapshotResponse,
    OperatorFlowTraceResponse,
    ParentToolCall,
    ParentToolMutationSuccess,
    ParentToolSuccess,
    ReleaseBlockedPayload,
    ReleaseGreenPayload,
    RemoveChildPayload,
    RuntimeFlowPauseResponse,
    RuntimeFlowRead,
    RuntimeFlowSummary,
    RuntimeFlowSummaryListResponse,
    TopActionableItem,
    UpdateChildPayload,
    WorkflowManifestRef,
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _json_mapping(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload or {})


def _json_list(payload: object) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], payload or [])


def _coerce_source_path(path: Path) -> Path:
    return path.expanduser().resolve()


def _is_path_current(path: str | Path) -> bool:
    return Path(path).expanduser().resolve().exists()


async def _count_for_node(
    session: AsyncSession,
    model: type[AttemptModel] | type[DispatchTurnModel],
    task_id: str,
    node_key: str,
) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(model)
        .where(
            model.task_id == task_id,
            model.node_key == node_key,
        )
    )
    return int(count or 0) + 1


async def _flow_by_task(session: AsyncSession, task_id: str) -> FlowModel:
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    if flow is None:
        raise ValueError(f"unknown task_id '{task_id}'")
    return flow


async def _live_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> DispatchCallbackBindingModel | None:
    result = await session.execute(
        select(DispatchCallbackBindingModel).where(
            DispatchCallbackBindingModel.task_id == task_id,
            DispatchCallbackBindingModel.dispatch_id == dispatch_id,
            DispatchCallbackBindingModel.binding_status == "live",
            DispatchCallbackBindingModel.revoked_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def validate_callback_session_key(
    session: AsyncSession,
    *,
    task_id: str,
    session_key: str,
) -> None:
    binding = await session.scalar(
        select(DispatchCallbackBindingModel).where(
            DispatchCallbackBindingModel.task_id == task_id,
            DispatchCallbackBindingModel.session_key == session_key,
            DispatchCallbackBindingModel.binding_status == "live",
            DispatchCallbackBindingModel.revoked_at.is_(None),
        )
    )
    if binding is None:
        raise ValueError("invalid callback session key")
    flow = await _flow_by_task(session, task_id)
    if flow.current_open_dispatch_id != binding.dispatch_id:
        raise ValueError("stale callback session key")


async def _revoke_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
) -> None:
    binding = await _live_callback_binding(session, task_id=task_id, dispatch_id=dispatch_id)
    if binding is None:
        return
    binding.binding_status = "revoked"
    binding.revoked_at = _now()
    await session.flush()


async def _create_callback_binding(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch_id: str,
    attempt_id: str,
    assignment_id: str,
) -> None:
    session.add(
        DispatchCallbackBindingModel(
            dispatch_callback_binding_id=dispatch_callback_binding_id(dispatch_id),
            dispatch_id=dispatch_id,
            attempt_id=attempt_id,
            assignment_id=assignment_id,
            task_id=task_id,
            session_key=token_urlsafe(24),
            binding_status="live",
        )
    )
    await session.flush()


def _ensure_no_staged_child_assignment(
    dispatch: DispatchTurnModel,
    *,
    action_name: str,
) -> None:
    if dispatch.staged_child_assignment_id is not None:
        raise ValueError(f"{action_name} is illegal after staging a child assignment")


async def _current_artifact_pointer_matches(
    session: AsyncSession,
    *,
    task_id: str,
    ref: dict[str, Any],
) -> bool:
    if ref.get("kind") != EvidenceKind.ARTIFACT.value:
        return _is_path_current(str(ref["path"]))
    pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.slot == ref.get("slot"),
            ArtifactCurrentPointerModel.current_path == str(ref["path"]),
            ArtifactCurrentPointerModel.current_version == ref.get("version"),
        )
    )
    return pointer is not None


async def _direct_child_assignments(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    parent_node_key: str,
) -> list[AssignmentModel]:
    children = list(
        await session.scalars(
            select(FlowNodeModel).where(
                FlowNodeModel.flow_revision_id == flow_revision_id,
                FlowNodeModel.parent_node_key == parent_node_key,
            )
        )
    )
    assignments: list[AssignmentModel] = []
    for child in children:
        if child.current_assignment_id is None:
            raise ValueError(f"child node '{child.node_key}' has no current assignment")
        assignment = await session.get(AssignmentModel, child.current_assignment_id)
        if assignment is None:
            raise ValueError(f"missing child assignment '{child.current_assignment_id}'")
        assignments.append(assignment)
    return assignments


async def _ensure_release_green_preconditions(
    session: AsyncSession,
    *,
    task_id: str,
    flow_revision_id: str,
    current_node_key: str,
    current_assignment: AssignmentModel,
) -> None:
    for ref in [*current_assignment.criteria_json, *current_assignment.consumes_json]:
        if not await _current_artifact_pointer_matches(session, task_id=task_id, ref=ref):
            raise ValueError("release_green requires current surfaced evidence")
    child_assignments = await _direct_child_assignments(
        session,
        flow_revision_id=flow_revision_id,
        parent_node_key=current_node_key,
    )
    for child_assignment in child_assignments:
        if child_assignment.current_attempt_id is None:
            raise ValueError(
                f"child assignment '{child_assignment.assignment_key}' has no current attempt"
            )
        attempt = await session.get(AttemptModel, child_assignment.current_attempt_id)
        if attempt is None:
            raise ValueError(f"missing child attempt '{child_assignment.current_attempt_id}'")
        if (
            attempt.latest_checkpoint_id is None
            or attempt.terminal_outcome != EgressBoundary.GREEN.value
        ):
            raise ValueError(
                f"child assignment '{child_assignment.assignment_key}' is not terminal-green"
            )
        for requirement in child_assignment.produces_json:
            pointer = await session.scalar(
                select(ArtifactCurrentPointerModel).where(
                    ArtifactCurrentPointerModel.task_id == task_id,
                    ArtifactCurrentPointerModel.slot == requirement["slot"],
                    ArtifactCurrentPointerModel.assignment_key == child_assignment.assignment_key,
                )
            )
            if pointer is None:
                raise ValueError(
                    "missing current artifact for child assignment "
                    f"'{child_assignment.assignment_key}'"
                )


async def _ensure_release_blocked_preconditions(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    current_node_key: str,
) -> None:
    child_assignments = await _direct_child_assignments(
        session,
        flow_revision_id=flow_revision_id,
        parent_node_key=current_node_key,
    )
    if not child_assignments:
        raise ValueError("release_blocked requires direct child work")
    blocked_found = False
    for assignment in child_assignments:
        if assignment.current_attempt_id is None:
            raise ValueError(
                f"child assignment '{assignment.assignment_key}' has no current attempt"
            )
        attempt = await session.get(AttemptModel, assignment.current_attempt_id)
        if attempt is None:
            raise ValueError(f"missing child attempt '{assignment.current_attempt_id}'")
        if attempt.latest_checkpoint_id is None or attempt.terminal_outcome is None:
            raise ValueError(f"child assignment '{assignment.assignment_key}' is not terminal")
        blocked_found = blocked_found or attempt.terminal_outcome == EgressBoundary.BLOCKED.value
    if not blocked_found:
        raise ValueError("release_blocked requires a blocked child basis")


async def _open_dispatch_for_attempt(
    session: AsyncSession,
    *,
    task_id: str,
    node: FlowNodeModel,
    assignment: AssignmentModel,
    attempt: AttemptModel,
    send_mode: PromptSendMode,
    previous_dispatch_id: str | None,
) -> DispatchTurnModel:
    flow = await _flow_by_task(session, task_id)
    dispatch_id = runtime_dispatch_id(
        node.node_key,
        await _count_for_node(session, DispatchTurnModel, task_id, node.node_key),
    )
    dispatch = DispatchTurnModel(
        dispatch_id=dispatch_id,
        flow_id=flow.flow_id,
        task_id=task_id,
        node_key=node.node_key,
        assignment_id=assignment.assignment_id,
        assignment_key=assignment.assignment_key,
        attempt_id=attempt.attempt_id,
        prompt_name=(
            PromptFamily.WORKER_DISPATCH.value
            if node.structural_kind == NodeKind.WORKER.value
            else PromptFamily.PARENT_ROOT_DISPATCH.value
        ),
        send_mode=send_mode.value,
        delivery_status=DispatchDeliveryStatus.ACCEPTED.value,
        control_state="live",
        prompt_path="",
        content_hash="",
        previous_dispatch_id=previous_dispatch_id,
        rendered_at=_now(),
        opened_at=_now(),
    )
    session.add(dispatch)
    session.add(
        DispatchDeliveryStateModel(
            dispatch_id=dispatch.dispatch_id,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
            assignment_key=assignment.assignment_key,
            node_key=node.node_key,
            transport_family="phase3_local_runtime",
            transport_state="accepted",
            controller_observation_state="live",
            send_mode=send_mode.value,
            previous_dispatch_id=previous_dispatch_id,
            accepted_at=dispatch.rendered_at,
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
    flow.current_open_dispatch_id = dispatch.dispatch_id
    flow.current_node_key = node.node_key
    flow.status = FlowStatus.RUNNING.value
    flow.updated_at = _now()
    await session.flush()
    await _create_callback_binding(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
        attempt_id=attempt.attempt_id,
        assignment_id=assignment.assignment_id,
    )
    _bundle, prompt_record = await render_dispatch_prompt(session, task_id, dispatch)
    dispatch.prompt_path = str(prompt_record.rendered_markdown_path)
    dispatch.content_hash = prompt_record.content_hash
    await session.flush()
    await materialize_dispatch_files(session, task_id, dispatch.dispatch_id)
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


async def runtime_flow_read(session: AsyncSession, task_id: str) -> RuntimeFlowRead:
    state = await current_runtime_state(session, task_id)
    manifest = await build_manifest_projection(session, task_id)
    return RuntimeFlowRead(
        task_id=state.task.task_id,
        task_title=state.task.title,
        task_summary=state.task.summary,
        workflow_key=state.task.workflow_key,
        status=FlowStatus(state.flow.status),
        active_flow_revision_id=state.flow.active_flow_revision_id or "",
        workflow_manifest_ref=WorkflowManifestRef(
            path=manifest.filesystem_roots.runtime_path / "workflow-manifest.md",
            description="Whole-workflow visible contract for the current task.",
        ),
        current_node_key=state.flow.current_node_key,
        active_attempt_id=state.current_attempt.attempt_id,
        updated_at=state.flow.updated_at,
    )


async def list_runtime_flows(
    session: AsyncSession,
    *,
    q: str | None = None,
    status: str = "any",
    limit: int = 50,
    sort: str = "updated_at_desc",
) -> RuntimeFlowSummaryListResponse:
    query = select(FlowModel, TaskModel).join(TaskModel, TaskModel.task_id == FlowModel.task_id)
    rows = list((await session.execute(query)).all())
    items: list[RuntimeFlowSummary] = []
    for flow, task in rows:
        if status != "any" and flow.status != status:
            continue
        if (
            q is not None
            and q.lower()
            not in " ".join(
                [
                    task.task_id,
                    task.title,
                    task.summary,
                    task.workflow_key or "",
                    flow.current_node_key or "",
                ]
            ).lower()
        ):
            continue
        manifest = await build_manifest_projection(session, task.task_id)
        attempt_id = None
        if flow.current_node_key is not None:
            node = await _flow_node_by_key(
                session,
                flow.active_flow_revision_id or "",
                flow.current_node_key,
            )
            if node.current_assignment_id is not None:
                assignment = await session.get(AssignmentModel, node.current_assignment_id)
                if assignment is not None:
                    attempt_id = assignment.current_attempt_id
        items.append(
            RuntimeFlowSummary(
                task_id=task.task_id,
                task_title=task.title,
                task_summary=task.summary,
                workflow_key=task.workflow_key,
                status=FlowStatus(flow.status),
                active_flow_revision_id=flow.active_flow_revision_id or "",
                workflow_manifest_ref=WorkflowManifestRef(
                    path=manifest.filesystem_roots.runtime_path / "workflow-manifest.md",
                    description="Whole-workflow visible contract for the current task.",
                ),
                current_node_key=flow.current_node_key,
                active_attempt_id=attempt_id,
                updated_at=flow.updated_at,
            )
        )
    if sort == "updated_at_asc":
        items.sort(key=lambda item: item.updated_at)
    elif sort == "task_title_asc":
        items.sort(key=lambda item: item.task_title.lower())
    elif sort == "task_title_desc":
        items.sort(key=lambda item: item.task_title.lower(), reverse=True)
    else:
        items.sort(key=lambda item: item.updated_at, reverse=True)
    return RuntimeFlowSummaryListResponse(items=tuple(items[:limit]), next_cursor=None)


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
    for claim in checkpoint_write.produced_artifacts:
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
        description = str(
            next(
                requirement["description"]
                for requirement in state.current_assignment.produces_json
                if requirement["slot"] == claim.slot
            )
        )
        destination_dir = paths.artifacts_path / state.current_node.node_key / claim.slot
        suffix = source_path.suffix
        destination = destination_dir / f"{claim.slot}.v{version:02d}{suffix}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
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
        session.add(
            ArtifactPublicationModel(
                artifact_publication_id=artifact_publication_id(
                    state.current_attempt.attempt_id,
                    claim.slot,
                    version,
                ),
                task_id=task_id,
                owner_node_key=state.current_node.node_key,
                slot=claim.slot,
                version=version,
                path=str(destination),
                description=description,
                assignment_key=state.current_assignment.assignment_key,
                attempt_id=state.current_attempt.attempt_id,
                supersedes_path=previous_pointer.current_path if previous_pointer else None,
            )
        )
        pointer = previous_pointer or ArtifactCurrentPointerModel(
            artifact_current_pointer_id=artifact_current_pointer_id(
                task_id,
                state.current_node.node_key,
                claim.slot,
            ),
            task_id=task_id,
            owner_node_key=state.current_node.node_key,
            slot=claim.slot,
            current_version=version,
            current_path=str(destination),
            description=description,
            assignment_key=state.current_assignment.assignment_key,
            attempt_id=state.current_attempt.attempt_id,
            published_at=_now(),
            supersedes_path=previous_pointer.current_path if previous_pointer else None,
        )
        if previous_pointer is None:
            session.add(pointer)
        else:
            pointer.current_version = version
            pointer.current_path = str(destination)
            pointer.description = str(description)
            pointer.assignment_key = state.current_assignment.assignment_key
            pointer.attempt_id = state.current_attempt.attempt_id
            pointer.published_at = _now()
            pointer.supersedes_path = previous_pointer.current_path
    transient_refs = tuple(
        EvidenceRef(
            kind=EvidenceKind.TRANSIENT,
            path=localize_transient_surface(
                paths=paths,
                source_path=surface.path,
                owner_node_key=state.current_node.node_key,
            ),
            description=surface.description,
        )
        for surface in checkpoint_write.transient_surfaces
    )
    checkpoint_id = runtime_checkpoint_id(state.current_attempt.attempt_id, checkpoint_seq)
    session.add(
        AttemptCheckpointModel(
            checkpoint_id=checkpoint_id,
            attempt_id=state.current_attempt.attempt_id,
            checkpoint_kind=checkpoint_write.checkpoint_kind.value,
            outcome=(
                checkpoint_write.outcome.value if checkpoint_write.outcome is not None else None
            ),
            summary=checkpoint_write.handoff.summary,
            next_step=checkpoint_write.handoff.next_step,
            blockers_json=list(checkpoint_write.handoff.blockers),
            risks_json=list(checkpoint_write.handoff.risks),
            produced_artifacts_json=[ref.model_dump(mode="json") for ref in produced_refs],
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
                slot=ref.slot or f"artifact-{index}",
                version=ref.version or index,
                path=str(ref.path),
                description=ref.description,
                published_at=_now(),
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
    await materialize_attempt_files(session, task_id, state.current_attempt.attempt_id)
    await materialize_manifest(session, task_id)
    for ref in produced_refs:
        if ref.slot is not None:
            await materialize_artifact_current_pointer(
                session,
                task_id,
                state.current_node.node_key,
                ref.slot,
            )
    if delivery_state is not None:
        await materialize_dispatch_files(session, task_id, dispatch.dispatch_id)
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
    latest_checkpoint = None
    if state.current_attempt.latest_checkpoint_id is not None:
        latest_checkpoint = await session.get(
            AttemptCheckpointModel, state.current_attempt.latest_checkpoint_id
        )
        if latest_checkpoint is not None:
            paths = await load_task_root_paths(session, task_id)
            checkpoint_ref = CheckpointFileRef(
                path=paths.attempts_path
                / state.current_attempt.attempt_id
                / "latest-checkpoint.md",
                description="Latest checkpoint for the current attempt.",
            )
    if payload.boundary == EgressBoundary.YIELD:
        if dispatch.staged_child_assignment_id is None:
            raise ValueError("yield requires exactly one staged child assignment")
    elif latest_checkpoint is None:
        raise ValueError("terminal boundaries require a terminal checkpoint")
    elif latest_checkpoint.outcome != payload.boundary.value:
        raise ValueError("boundary does not match latest terminal checkpoint outcome")

    dispatch.accepted_boundary = payload.boundary.value
    dispatch.closed_at = _now()
    flow.current_open_dispatch_id = None
    await _revoke_callback_binding(
        session,
        task_id=task_id,
        dispatch_id=dispatch.dispatch_id,
    )
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch.dispatch_id)
    dispatch.delivery_status = DispatchDeliveryStatus.PROVIDER_COMPLETED.value
    if delivery_state is not None:
        delivery_state.transport_state = DispatchDeliveryStatus.PROVIDER_COMPLETED.value
        delivery_state.controller_observation_state = "boundary_accepted_waiting_terminal"
        delivery_state.last_controller_terminal_at = _now()
        delivery_state.updated_at = _now()

    if payload.boundary in {EgressBoundary.GREEN, EgressBoundary.RETRY, EgressBoundary.BLOCKED}:
        state.current_attempt.terminal_outcome = payload.boundary.value
        state.current_attempt.closed_at = _now()

    if state.current_node.structural_kind == NodeKind.WORKER.value:
        if payload.boundary == EgressBoundary.RETRY:
            retry_attempt_id = runtime_attempt_id(
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
            consumes_json = list(state.current_assignment.consumes_json)
            if retry_checkpoint_ref is not None:
                consumes_json.insert(0, retry_checkpoint_ref.model_dump(mode="json"))
            state.current_assignment.consumes_json = consumes_json
            state.current_assignment.current_attempt_id = retry_attempt_id
            retry_attempt = AttemptModel(
                attempt_id=retry_attempt_id,
                assignment_id=state.current_assignment.assignment_id,
                task_id=task_id,
                node_key=state.current_node.node_key,
            )
            session.add(retry_attempt)
            await session.flush()
            for index, ref in enumerate(
                [*state.current_assignment.criteria_json, *state.current_assignment.consumes_json],
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
            await materialize_attempt_files(session, task_id, retry_attempt_id)
            await materialize_manifest(session, task_id)
            await _open_dispatch_for_attempt(
                session,
                task_id=task_id,
                node=state.current_node,
                assignment=state.current_assignment,
                attempt=retry_attempt,
                send_mode=PromptSendMode.FULL_PROMPT,
                previous_dispatch_id=dispatch.dispatch_id,
            )
        elif state.current_node.parent_node_key is not None:
            await _redispatch_parent(
                session,
                task_id=task_id,
                parent_node_key=state.current_node.parent_node_key,
                previous_dispatch_id=dispatch.dispatch_id,
            )
        else:
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
            child = await _flow_node_by_key(
                session,
                flow.active_flow_revision_id or "",
                assignment.node_key,
            )
            attempt = await session.get(AttemptModel, assignment.current_attempt_id)
            if attempt is None:
                raise ValueError(f"missing child attempt '{assignment.current_attempt_id}'")
            await _open_dispatch_for_attempt(
                session,
                task_id=task_id,
                node=child,
                assignment=assignment,
                attempt=attempt,
                send_mode=PromptSendMode.FULL_PROMPT,
                previous_dispatch_id=dispatch.dispatch_id,
            )
        elif payload.boundary == EgressBoundary.GREEN:
            if not state.current_assignment.release_green_ready:
                raise ValueError("green requires release_green first")
            if state.current_node.parent_node_key is not None:
                await _redispatch_parent(
                    session,
                    task_id=task_id,
                    parent_node_key=state.current_node.parent_node_key,
                    previous_dispatch_id=dispatch.dispatch_id,
                )
            else:
                flow.status = FlowStatus.SUCCEEDED.value
        else:
            if (
                state.current_node.structural_kind != NodeKind.ROOT.value
                or not state.current_assignment.release_blocked_ready
            ):
                raise ValueError("blocked requires root release_blocked first")
            flow.status = FlowStatus.BLOCKED.value

    flow.updated_at = _now()
    await session.flush()
    if delivery_state is not None:
        await materialize_dispatch_files(session, task_id, dispatch.dispatch_id)
    await materialize_manifest(session, task_id)
    return BoundaryRead(
        accepted_boundary=payload.boundary,
        flow=await runtime_flow_read(session, task_id),
        latest_checkpoint_ref=checkpoint_ref,
    )


async def _criteria_ref(
    task_id: str,
    slot: str,
    description: str,
    session: AsyncSession,
) -> EvidenceRef:
    paths = await load_task_root_paths(session, task_id)
    return EvidenceRef(
        kind=EvidenceKind.CRITERIA,
        slot=slot,
        path=paths.criteria_path / f"{slot}.md",
        description=description,
    )


async def call_parent_tool(
    session: AsyncSession,
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
) -> ParentToolSuccess:
    state = await current_runtime_state(session, task_id)
    if state.current_node.structural_kind == NodeKind.WORKER.value:
        raise ValueError("worker nodes cannot call parent/root tools")
    if payload.expected_structural_revision_id is not None and (
        payload.expected_structural_revision_id != state.flow.active_flow_revision_id
    ):
        raise ValueError("stale structural revision")
    flow = state.flow
    dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id or "")
    if dispatch is None:
        raise ValueError("no current open dispatch")
    if tool_name == ParentRootToolName.ASSIGN_CHILD:
        assign_payload = payload.payload
        if not isinstance(assign_payload, AssignChildPayload):
            raise ValueError("assign_child requires AssignChildPayload")
        _ensure_no_staged_child_assignment(dispatch, action_name="assign_child")
        child_node = await _flow_node_by_key(
            session,
            flow.active_flow_revision_id or "",
            assign_payload.child_node_key,
        )
        if child_node.parent_node_key != state.current_node.node_key:
            raise ValueError("assign_child target must be a direct child")
        attempt_seq = await _count_for_node(session, AttemptModel, task_id, child_node.node_key)
        assignment_key = f"{child_node.node_key}.assign-{attempt_seq:02d}"
        attempt_id = runtime_attempt_id(child_node.node_key, attempt_seq)
        criteria_refs: list[EvidenceRef] = []
        for criteria in child_node.criteria_json:
            criteria_refs.append(
                await _criteria_ref(
                    task_id,
                    str(criteria["slot"]),
                    str(criteria["description"]),
                    session,
                )
            )
        consumes: list[EvidenceRef | NodeRuntimeFileRef] = []
        consumes_json = _json_mapping(child_node.consumes_json)
        for selector in _json_list(consumes_json.get("artifacts", [])):
            pointer = await session.scalar(
                select(ArtifactCurrentPointerModel).where(
                    ArtifactCurrentPointerModel.task_id == task_id,
                    ArtifactCurrentPointerModel.slot == selector["slot"],
                )
            )
            if pointer is None and bool(selector.get("required", True)):
                raise ValueError(f"missing current artifact for slot '{selector['slot']}'")
            if pointer is not None:
                consumes.append(
                    EvidenceRef(
                        kind=EvidenceKind.ARTIFACT,
                        slot=pointer.slot,
                        version=pointer.current_version,
                        path=Path(pointer.current_path),
                        description=pointer.description,
                    )
                )
        for selector in _json_list(consumes_json.get("criteria", [])):
            criteria_ref = await _criteria_ref(
                task_id,
                str(selector["slot"]),
                str(selector["slot"]),
                session,
            )
            consumes.append(criteria_ref)
        if assign_payload.supplemental_durable_context is not None:
            for criteria_slot in assign_payload.supplemental_durable_context.criteria_slots:
                consumes.append(
                    await _criteria_ref(
                        task_id,
                        criteria_slot.slot,
                        criteria_slot.slot,
                        session,
                    )
                )
            for artifact_slot in assign_payload.supplemental_durable_context.artifact_slots:
                pointer_result = await session.execute(
                    select(ArtifactCurrentPointerModel).where(
                        ArtifactCurrentPointerModel.task_id == task_id,
                        ArtifactCurrentPointerModel.slot == artifact_slot.slot,
                    )
                )
                pointer = pointer_result.scalar_one_or_none()
                if pointer is None:
                    raise ValueError(
                        f"missing supplemental artifact for slot '{artifact_slot.slot}'"
                    )
                consumes.append(
                    EvidenceRef(
                        kind=EvidenceKind.ARTIFACT,
                        slot=pointer.slot,
                        version=pointer.current_version,
                        path=Path(pointer.current_path),
                        description=pointer.description,
                    )
                )
        paths = await load_task_root_paths(session, task_id)
        transient_refs = tuple(
            EvidenceRef(
                kind=EvidenceKind.TRANSIENT,
                path=localize_transient_surface(
                    paths=paths,
                    source_path=surface.path,
                    owner_node_key=child_node.node_key,
                ),
                description=surface.description,
            )
            for surface in assign_payload.transient_surfaces
        )
        assignment = AssignmentModel(
            assignment_id=assignment_id(assignment_key),
            task_id=task_id,
            flow_node_id=child_node.flow_node_id,
            assignment_key=assignment_key,
            node_key=child_node.node_key,
            summary=assign_payload.assignment_intent.summary,
            instruction=assign_payload.assignment_intent.instruction,
            criteria_json=[ref.model_dump(mode="json") for ref in criteria_refs],
            consumes_json=[ref.model_dump(mode="json") for ref in consumes],
            produces_json=list(_json_mapping(child_node.produces_json).get("artifacts", [])),
            transient_refs_json=[ref.model_dump(mode="json") for ref in transient_refs],
            task_memory_search_hints_json=list(assign_payload.task_memory_search_hints),
            current_attempt_id=attempt_id,
            created_by_dispatch_id=dispatch.dispatch_id,
        )
        child_node.current_assignment_id = assignment.assignment_id
        session.add(assignment)
        await session.flush()
        for index, ref in enumerate(criteria_refs, start=1):
            session.add(
                AssignmentCriteriaRefModel(
                    assignment_criteria_ref_id=assignment_criteria_ref_id(
                        assignment.assignment_id,
                        ref.slot or f"criteria-{index}",
                    ),
                    assignment_id=assignment.assignment_id,
                    slot=ref.slot or f"criteria-{index}",
                    path=str(ref.path),
                    description=ref.description,
                    order_index=index,
                )
            )
        session.add(
            AttemptModel(
                attempt_id=attempt_id,
                assignment_id=assignment.assignment_id,
                task_id=task_id,
                node_key=child_node.node_key,
            )
        )
        await session.flush()
        consumed_refs: list[EvidenceRef | NodeRuntimeFileRef] = [*criteria_refs, *consumes]
        for index, runtime_ref in enumerate(consumed_refs, start=1):
            session.add(
                AttemptConsumedRefModel(
                    attempt_consumed_ref_id=attempt_consumed_ref_id(attempt_id, index),
                    attempt_id=attempt_id,
                    ref_kind=runtime_ref.kind.value,
                    slot=getattr(runtime_ref, "slot", None),
                    version=getattr(runtime_ref, "version", None),
                    path=str(runtime_ref.path),
                    description=runtime_ref.description,
                    order_index=index,
                )
            )
        dispatch.staged_child_assignment_id = assignment.assignment_id
        await session.flush()
        await materialize_attempt_files(session, task_id, attempt_id)
        await materialize_manifest(session, task_id)
        return AssignChildSuccess(
            summary=f"Staged child assignment for '{child_node.node_key}'.",
            target_node_key=child_node.node_key,
            target_assignment_key=assignment.assignment_key,
            target_attempt_id=attempt_id,
            child_assignment_ref=AssignmentFileRef(
                path=paths.attempts_path / attempt_id / "assignment.md",
                description=f"Current assignment for child node '{child_node.node_key}'.",
            ),
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=WorkflowManifestRef(
                path=paths.runtime_path / "workflow-manifest.md",
                description="Whole-workflow visible contract for the current task.",
            ),
            latest_checkpoint_ref=(
                CheckpointFileRef(
                    path=paths.attempts_path
                    / state.current_attempt.attempt_id
                    / "latest-checkpoint.md",
                    description="Latest checkpoint for the current attempt.",
                )
                if state.current_attempt.latest_checkpoint_id is not None
                else None
            ),
        )

    if tool_name == ParentRootToolName.ADD_CHILD:
        add_payload = payload.payload
        if not isinstance(add_payload, AddChildPayload):
            raise ValueError("add_child requires AddChildPayload")
        _ensure_no_staged_child_assignment(dispatch, action_name="add_child")
        target_node_key = await add_child_to_current_flow(
            session, task_id, state, add_payload.child
        )
        await materialize_manifest(session, task_id)
        return ParentToolMutationSuccess(
            tool_name="add_child",
            summary=f"Added child node '{target_node_key}'.",
            target_node_key=target_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=WorkflowManifestRef(
                path=(await load_task_root_paths(session, task_id)).runtime_path
                / "workflow-manifest.md",
                description="Whole-workflow visible contract for the current task.",
            ),
        )
    if tool_name == ParentRootToolName.UPDATE_CHILD:
        update_payload = payload.payload
        if not isinstance(update_payload, UpdateChildPayload):
            raise ValueError("update_child requires UpdateChildPayload")
        _ensure_no_staged_child_assignment(dispatch, action_name="update_child")
        await update_child_in_current_flow(
            session, task_id, state, update_payload.child_node_key, update_payload.patch
        )
        await materialize_manifest(session, task_id)
        return ParentToolMutationSuccess(
            tool_name="update_child",
            summary=f"Updated child node '{update_payload.child_node_key}'.",
            target_node_key=update_payload.child_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=WorkflowManifestRef(
                path=(await load_task_root_paths(session, task_id)).runtime_path
                / "workflow-manifest.md",
                description="Whole-workflow visible contract for the current task.",
            ),
        )
    if tool_name == ParentRootToolName.REMOVE_CHILD:
        remove_payload = payload.payload
        if not isinstance(remove_payload, RemoveChildPayload):
            raise ValueError("remove_child requires RemoveChildPayload")
        _ensure_no_staged_child_assignment(dispatch, action_name="remove_child")
        await remove_child_from_current_flow(session, task_id, state, remove_payload.child_node_key)
        await materialize_manifest(session, task_id)
        return ParentToolMutationSuccess(
            tool_name="remove_child",
            summary=f"Removed child node '{remove_payload.child_node_key}'.",
            target_node_key=remove_payload.child_node_key,
            flow=await runtime_flow_read(session, task_id),
            workflow_manifest_ref=WorkflowManifestRef(
                path=(await load_task_root_paths(session, task_id)).runtime_path
                / "workflow-manifest.md",
                description="Whole-workflow visible contract for the current task.",
            ),
        )
    if tool_name == ParentRootToolName.RELEASE_GREEN:
        release_payload = payload.payload
        if not isinstance(release_payload, ReleaseGreenPayload):
            raise ValueError("release_green requires ReleaseGreenPayload")
        _ensure_no_staged_child_assignment(dispatch, action_name="release_green")
        await _ensure_release_green_preconditions(
            session,
            task_id=task_id,
            flow_revision_id=flow.active_flow_revision_id or "",
            current_node_key=state.current_node.node_key,
            current_assignment=state.current_assignment,
        )
        state.current_assignment.release_green_ready = True
        await session.flush()
        return ParentToolMutationSuccess(
            tool_name="release_green",
            summary="Current assignment is marked green-release-ready.",
            target_node_key=state.current_node.node_key,
            flow=await runtime_flow_read(session, task_id),
        )
    release_payload = payload.payload
    if not isinstance(release_payload, ReleaseBlockedPayload):
        raise ValueError("release_blocked requires ReleaseBlockedPayload")
    if state.current_node.structural_kind != NodeKind.ROOT.value:
        raise ValueError("release_blocked is root-only")
    _ensure_no_staged_child_assignment(dispatch, action_name="release_blocked")
    await _ensure_release_blocked_preconditions(
        session,
        flow_revision_id=flow.active_flow_revision_id or "",
        current_node_key=state.current_node.node_key,
    )
    state.current_assignment.release_blocked_ready = True
    await session.flush()
    return ParentToolMutationSuccess(
        tool_name="release_blocked",
        summary="Current root assignment is marked blocked-release-ready.",
        target_node_key=state.current_node.node_key,
        flow=await runtime_flow_read(session, task_id),
    )


async def continue_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowRead:
    flow = await _flow_by_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise ValueError("stale active flow revision")
    if flow.status in {
        FlowStatus.BLOCKED.value,
        FlowStatus.CANCELLED.value,
        FlowStatus.SUCCEEDED.value,
    }:
        return await runtime_flow_read(session, task_id)
    if flow.status == FlowStatus.PAUSED.value:
        flow.status = FlowStatus.RUNNING.value
        flow.updated_at = _now()
        await session.flush()
    if flow.current_open_dispatch_id is None and flow.current_node_key is not None:
        node = await _flow_node_by_key(
            session,
            flow.active_flow_revision_id or "",
            flow.current_node_key,
        )
        if node.current_assignment_id is not None:
            assignment = await session.get(AssignmentModel, node.current_assignment_id)
            if assignment is not None and assignment.current_attempt_id is not None:
                attempt = await session.get(AttemptModel, assignment.current_attempt_id)
                if attempt is not None:
                    await _open_dispatch_for_attempt(
                        session,
                        task_id=task_id,
                        node=node,
                        assignment=assignment,
                        attempt=attempt,
                        send_mode=PromptSendMode.FULL_PROMPT,
                        previous_dispatch_id=None,
                    )
    await session.flush()
    return await runtime_flow_read(session, task_id)


async def pause_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowPauseResponse:
    flow = await _flow_by_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise ValueError("stale active flow revision")
    flow.status = FlowStatus.PAUSED.value
    flow.updated_at = _now()
    await session.flush()
    return RuntimeFlowPauseResponse(flow=await runtime_flow_read(session, task_id))


async def cancel_runtime_flow(
    session: AsyncSession,
    task_id: str,
    *,
    expected_active_flow_revision_id: str,
) -> RuntimeFlowRead:
    flow = await _flow_by_task(session, task_id)
    if flow.active_flow_revision_id != expected_active_flow_revision_id:
        raise ValueError("stale active flow revision")
    flow.status = FlowStatus.CANCELLED.value
    if flow.current_open_dispatch_id is not None:
        await _revoke_callback_binding(
            session,
            task_id=task_id,
            dispatch_id=flow.current_open_dispatch_id,
        )
        flow.current_open_dispatch_id = None
    flow.updated_at = _now()
    await session.flush()
    return await runtime_flow_read(session, task_id)


async def operator_snapshot(session: AsyncSession, task_id: str) -> OperatorFlowSnapshotResponse:
    flow = await runtime_flow_read(session, task_id)
    paths = await load_task_root_paths(session, task_id)
    current_paths = (
        WorkflowManifestRef(
            path=paths.runtime_path / "workflow-manifest.md",
            description="Whole-workflow visible contract for the current task.",
        ),
    )
    return OperatorFlowSnapshotResponse(
        flow=flow,
        top_actionable_items=(
            TopActionableItem(
                summary=f"Current runtime status is '{flow.status.value}'.",
                node_key=flow.current_node_key,
                current_paths=current_paths,
                suggested_action=(
                    "continue" if flow.status in {FlowStatus.PAUSED, FlowStatus.BLOCKED} else None
                ),
            ),
        ),
        current_paths=current_paths,
    )


async def operator_trace(
    session: AsyncSession,
    task_id: str,
    *,
    scope: str = "current",
    q: str | None = None,
    limit: int = 50,
    sort: str = "occurred_at_desc",
) -> OperatorFlowTraceResponse:
    flow = await _flow_by_task(session, task_id)
    dispatches = list(
        await session.scalars(
            select(DispatchTurnModel)
            .where(DispatchTurnModel.task_id == task_id)
            .order_by(DispatchTurnModel.rendered_at.asc())
        )
    )
    checkpoints = list(
        await session.scalars(
            select(AttemptCheckpointModel)
            .join(AttemptModel, AttemptModel.attempt_id == AttemptCheckpointModel.attempt_id)
            .where(AttemptModel.task_id == task_id)
            .order_by(AttemptCheckpointModel.recorded_at.asc())
        )
    )
    if scope == "current" and flow.current_node_key is not None:
        dispatches = [
            dispatch for dispatch in dispatches if dispatch.node_key == flow.current_node_key
        ]
        checkpoints = [
            checkpoint
            for checkpoint in checkpoints
            if checkpoint.attempt_id.startswith(f"attempt.{flow.current_node_key}.")
        ]
    boundary_history = tuple(
        BoundaryHistoryEntry(
            node_key=dispatch.node_key,
            boundary=EgressBoundary(dispatch.accepted_boundary),
            occurred_at=dispatch.closed_at or dispatch.rendered_at,
        )
        for dispatch in dispatches
        if dispatch.accepted_boundary is not None
    )
    if q is not None:
        query = q.lower()
        dispatches = [
            dispatch
            for dispatch in dispatches
            if query in dispatch.node_key.lower()
            or query in (dispatch.assignment_key or "").lower()
            or query in dispatch.send_mode.lower()
            or query in dispatch.delivery_status.lower()
        ]
        checkpoints = [
            checkpoint
            for checkpoint in checkpoints
            if query in checkpoint.summary.lower() or query in checkpoint.attempt_id.lower()
        ]
        boundary_history = tuple(
            entry
            for entry in boundary_history
            if query in entry.node_key.lower() or query in entry.boundary.value.lower()
        )
    reverse = sort != "occurred_at_asc"
    dispatches.sort(key=lambda dispatch: dispatch.rendered_at, reverse=reverse)
    checkpoints.sort(key=lambda checkpoint: checkpoint.recorded_at, reverse=reverse)
    boundary_items = sorted(
        boundary_history,
        key=lambda entry: entry.occurred_at,
        reverse=reverse,
    )[:limit]
    paths = await load_task_root_paths(session, task_id)
    current_paths = (
        WorkflowManifestRef(
            path=paths.runtime_path / "workflow-manifest.md",
            description="Whole-workflow visible contract for the current task.",
        ),
        DocRef(
            kind="doc",
            path=paths.dispatch_path,
            description="Dispatch observability directory for task-scoped inspection.",
        ),
    )
    return OperatorFlowTraceResponse(
        task_id=task_id,
        scope="whole" if scope == "whole" else "current",
        dispatch_history=tuple(
            DispatchHistoryEntry(
                attempt_id=dispatch.attempt_id or "",
                assignment_key=dispatch.assignment_key,
                node_key=dispatch.node_key,
                send_mode=PromptSendMode(dispatch.send_mode),
                delivery_status=DispatchDeliveryStatus(dispatch.delivery_status),
                rendered_at=dispatch.rendered_at,
            )
            for dispatch in dispatches[:limit]
        ),
        checkpoint_history=tuple(
            CheckpointHistoryEntry(
                checkpoint_id=checkpoint.checkpoint_id,
                attempt_id=checkpoint.attempt_id,
                checkpoint_kind=CheckpointKind(checkpoint.checkpoint_kind),
                outcome=CheckpointOutcome(checkpoint.outcome) if checkpoint.outcome else None,
                summary=checkpoint.summary,
                recorded_at=checkpoint.recorded_at,
            )
            for checkpoint in checkpoints[:limit]
        ),
        boundary_history=tuple(boundary_items),
        current_paths=current_paths,
        next_cursor=None,
    )


async def observability_ref(
    session: AsyncSession,
    task_id: str,
    filename: str,
    description: str,
) -> ObservabilityFileRef:
    flow = await _flow_by_task(session, task_id)
    dispatch_id = flow.current_open_dispatch_id
    if dispatch_id is None:
        dispatch_id = await session.scalar(
            select(DispatchTurnModel.dispatch_id)
            .where(DispatchTurnModel.task_id == task_id)
            .order_by(DispatchTurnModel.rendered_at.desc())
        )
    if dispatch_id is None:
        raise ValueError("task has no dispatch history")
    paths = await load_task_root_paths(session, task_id)
    await materialize_dispatch_files(session, task_id, dispatch_id)
    return ObservabilityFileRef(
        path=paths.dispatch_path / dispatch_id / filename,
        description=description,
    )
