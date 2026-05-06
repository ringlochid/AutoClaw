from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ArtifactCurrentPointerModel,
    AssignmentCriteriaRefModel,
    AssignmentModel,
    AttemptConsumedRefModel,
    AttemptModel,
    DispatchTurnModel,
    FlowNodeModel,
)
from app.runtime.contracts import (
    EvidenceKind,
    EvidenceRef,
    NodeKind,
    NodeRuntimeFileRef,
    ParentRootToolName,
)
from app.runtime.control.flows import runtime_flow_read
from app.runtime.control.release import (
    _ensure_release_blocked_preconditions,
    _ensure_release_green_preconditions,
    _flow_node_by_key,
)
from app.runtime.control.support import (
    _count_for_node,
    _ensure_no_staged_child_assignment,
    _ensure_no_terminal_release_basis,
    _int_or_none,
    _json_list,
    _json_mapping,
    _now,
    _queue_attempt_materialization,
    _queue_file_copy,
    _queue_manifest_materialization,
)
from app.runtime.ids import (
    assignment_criteria_ref_id,
    assignment_id,
    assignment_key_for_task,
    attempt_consumed_ref_id,
    attempt_id_for_task,
)
from app.runtime.projection import (
    current_runtime_state,
    load_task_root_paths,
)
from app.runtime.replan import (
    add_child_to_current_flow,
    remove_child_from_current_flow,
    update_child_in_current_flow,
)
from app.runtime.resources import planned_transient_surface_path
from app.schemas.runtime import (
    AssignChildSuccess,
    AssignmentFileRef,
    CheckpointFileRef,
    ParentToolCall,
    ParentToolSuccess,
    WorkflowManifestRef,
)
from app.schemas.runtime.parent_tools import (
    AddChildSuccess,
    AddChildToolCall,
    AssignChildToolCall,
    ReleaseBlockedSuccess,
    ReleaseBlockedToolCall,
    ReleaseGreenSuccess,
    ReleaseGreenToolCall,
    RemoveChildSuccess,
    RemoveChildToolCall,
    UpdateChildSuccess,
    UpdateChildToolCall,
)


async def _criteria_ref(
    task_id: str,
    slot: str,
    description: str,
    session: AsyncSession,
    *,
    version: int | None = None,
    path: Path | None = None,
) -> EvidenceRef:
    resolved_path = path
    if resolved_path is None:
        task_paths = await load_task_root_paths(session, task_id)
        resolved_path = task_paths.criteria_path / f"{slot}.md"
    return EvidenceRef(
        kind=EvidenceKind.CRITERIA,
        slot=slot,
        path=resolved_path,
        description=description,
    )


def _dedupe_criteria_refs(criteria_refs: list[EvidenceRef]) -> list[EvidenceRef]:
    deduped: list[EvidenceRef] = []
    seen_slots: set[str] = set()
    for ref in criteria_refs:
        if ref.slot is None:
            deduped.append(ref)
            continue
        if ref.slot in seen_slots:
            continue
        seen_slots.add(ref.slot)
        deduped.append(ref)
    return deduped


async def _criteria_snapshot_by_slot(
    session: AsyncSession,
    flow_revision_id: str,
) -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}
    nodes = await session.scalars(
        select(FlowNodeModel).where(FlowNodeModel.flow_revision_id == flow_revision_id)
    )
    for node in nodes:
        for criteria in node.criteria_json:
            snapshots[str(criteria["slot"])] = dict(criteria)
    return snapshots


async def call_parent_tool(
    session: AsyncSession,
    task_id: str,
    tool_name: ParentRootToolName,
    payload: ParentToolCall,
) -> ParentToolSuccess:
    typed_call = payload.as_variant()
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
    _ensure_no_terminal_release_basis(dispatch, action_name=tool_name.value)
    if tool_name == ParentRootToolName.ASSIGN_CHILD:
        if not isinstance(typed_call, AssignChildToolCall):
            raise ValueError("assign_child requires AssignChildPayload")
        assign_payload = typed_call.payload
        _ensure_no_staged_child_assignment(dispatch, action_name="assign_child")
        child_node = await _flow_node_by_key(
            session,
            flow.active_flow_revision_id or "",
            assign_payload.child_node_key,
        )
        if child_node.parent_node_key != state.current_node.node_key:
            raise ValueError("assign_child target must be a direct child")
        attempt_seq = await _count_for_node(session, AttemptModel, task_id, child_node.node_key)
        assignment_key = assignment_key_for_task(task_id, child_node.node_key, attempt_seq)
        attempt_id = attempt_id_for_task(task_id, child_node.node_key, attempt_seq)
        criteria_snapshots = await _criteria_snapshot_by_slot(
            session,
            flow.active_flow_revision_id or "",
        )
        criteria_refs: list[EvidenceRef] = []
        for criteria in child_node.criteria_json:
            criteria_refs.append(
                await _criteria_ref(
                    task_id,
                    str(criteria["slot"]),
                    str(criteria["description"]),
                    session,
                    version=_int_or_none(criteria.get("version")),
                    path=Path(str(criteria["path"])) if criteria.get("path") is not None else None,
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
            slot = str(selector["slot"])
            criteria_snapshot = criteria_snapshots.get(slot)
            if criteria_snapshot is None:
                raise ValueError(f"missing criteria provider for slot '{slot}'")
            criteria_ref = await _criteria_ref(
                task_id,
                slot,
                str(criteria_snapshot["description"]),
                session,
                version=_int_or_none(criteria_snapshot.get("version")),
                path=(
                    Path(str(criteria_snapshot["path"]))
                    if criteria_snapshot.get("path") is not None
                    else None
                ),
            )
            criteria_refs.append(criteria_ref)
        if assign_payload.supplemental_durable_context is not None:
            for criteria_slot in assign_payload.supplemental_durable_context.criteria_slots:
                criteria_snapshot = criteria_snapshots.get(criteria_slot.slot)
                if criteria_snapshot is None:
                    raise ValueError(
                        f"missing supplemental criteria for slot '{criteria_slot.slot}'"
                    )
                criteria_refs.append(
                    await _criteria_ref(
                        task_id,
                        criteria_slot.slot,
                        str(criteria_snapshot["description"]),
                        session,
                        version=_int_or_none(criteria_snapshot.get("version")),
                        path=(
                            Path(str(criteria_snapshot["path"]))
                            if criteria_snapshot.get("path") is not None
                            else None
                        ),
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
        criteria_refs = _dedupe_criteria_refs(criteria_refs)
        paths = await load_task_root_paths(session, task_id)
        transient_refs = tuple(
            EvidenceRef(
                kind=EvidenceKind.TRANSIENT,
                path=planned_transient_surface_path(
                    paths=paths,
                    source_path=surface.path,
                    owner_node_key=child_node.node_key,
                ),
                description=surface.description,
            )
            for surface in assign_payload.transient_surfaces
        )
        for surface, transient_ref in zip(
            assign_payload.transient_surfaces,
            transient_refs,
            strict=True,
        ):
            _queue_file_copy(
                session,
                source_path=surface.path,
                destination=transient_ref.path,
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
                    version=ref.version,
                    order_index=index,
                )
            )
        session.add(
            AttemptModel(
                attempt_id=attempt_id,
                assignment_id=assignment.assignment_id,
                assignment_key=assignment.assignment_key,
                flow_node_id=assignment.flow_node_id,
                task_id=task_id,
                node_key=child_node.node_key,
                status="pending",
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
        dispatch.staged_continuation_kind = "child_assignment"
        await session.flush()
        _queue_attempt_materialization(
            session,
            task_id=task_id,
            attempt_id=attempt_id,
        )
        _queue_manifest_materialization(session, task_id=task_id)
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
        if not isinstance(typed_call, AddChildToolCall):
            raise ValueError("add_child requires AddChildPayload")
        add_payload = typed_call.payload
        _ensure_no_staged_child_assignment(dispatch, action_name="add_child")
        target_node_key = await add_child_to_current_flow(
            session, task_id, state, add_payload.child
        )
        _queue_manifest_materialization(session, task_id=task_id)
        return AddChildSuccess(
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
        if not isinstance(typed_call, UpdateChildToolCall):
            raise ValueError("update_child requires UpdateChildPayload")
        update_payload = typed_call.payload
        _ensure_no_staged_child_assignment(dispatch, action_name="update_child")
        await update_child_in_current_flow(
            session, task_id, state, update_payload.child_node_key, update_payload.patch
        )
        _queue_manifest_materialization(session, task_id=task_id)
        return UpdateChildSuccess(
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
        if not isinstance(typed_call, RemoveChildToolCall):
            raise ValueError("remove_child requires RemoveChildPayload")
        remove_payload = typed_call.payload
        _ensure_no_staged_child_assignment(dispatch, action_name="remove_child")
        await remove_child_from_current_flow(session, task_id, state, remove_payload.child_node_key)
        _queue_manifest_materialization(session, task_id=task_id)
        return RemoveChildSuccess(
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
        if not isinstance(typed_call, ReleaseGreenToolCall):
            raise ValueError("release_green requires ReleaseGreenPayload")
        _ensure_no_staged_child_assignment(dispatch, action_name="release_green")
        await _ensure_release_green_preconditions(
            session,
            task_id=task_id,
            flow_revision_id=flow.active_flow_revision_id or "",
            current_node_key=state.current_node.node_key,
            current_assignment=state.current_assignment,
        )
        dispatch.release_precondition_kind = "release_green"
        dispatch.release_precondition_flow_revision_id = flow.active_flow_revision_id
        dispatch.release_precondition_assignment_id = state.current_assignment.assignment_id
        dispatch.release_precondition_recorded_at = _now()
        await session.flush()
        return ReleaseGreenSuccess(
            tool_name="release_green",
            summary="Current assignment is marked green-release-ready.",
            target_node_key=state.current_node.node_key,
            flow=await runtime_flow_read(session, task_id),
        )
    if not isinstance(typed_call, ReleaseBlockedToolCall):
        raise ValueError("release_blocked requires ReleaseBlockedPayload")
    if state.current_node.structural_kind != NodeKind.ROOT.value:
        raise ValueError("release_blocked is root-only")
    _ensure_no_staged_child_assignment(dispatch, action_name="release_blocked")
    await _ensure_release_blocked_preconditions(
        session,
        task_id=task_id,
        flow_revision_id=flow.active_flow_revision_id or "",
        current_node_key=state.current_node.node_key,
        current_assignment=state.current_assignment,
    )
    dispatch.release_precondition_kind = "release_blocked"
    dispatch.release_precondition_flow_revision_id = flow.active_flow_revision_id
    dispatch.release_precondition_assignment_id = state.current_assignment.assignment_id
    dispatch.release_precondition_recorded_at = _now()
    await session.flush()
    return ReleaseBlockedSuccess(
        tool_name="release_blocked",
        summary="Current root assignment is marked blocked-release-ready.",
        target_node_key=state.current_node.node_key,
        flow=await runtime_flow_read(session, task_id),
    )
