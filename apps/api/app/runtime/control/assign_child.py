from __future__ import annotations

from pathlib import Path
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ArtifactCurrentPointerModel,
    AssignmentCriteriaRefModel,
    AssignmentModel,
    AttemptConsumedRefModel,
    AttemptModel,
    DispatchTurnModel,
    FlowEdgeModel,
    FlowNodeModel,
)
from app.runtime.contracts import EvidenceKind, EvidenceRef, NodeRuntimeFileRef, TaskRootPaths
from app.runtime.control.flows import runtime_flow_read
from app.runtime.control.release import _flow_node_by_key
from app.runtime.control.support import (
    _consume_assignment_budget,
    _count_for_node,
    _ensure_no_staged_child_assignment,
    _is_path_current,
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
from app.runtime.projection import CurrentRuntimeState, load_task_root_paths
from app.runtime.resources import planned_transient_surface_path
from app.schemas.runtime import (
    AssignChildSuccess,
    AssignmentFileRef,
    CheckpointFileRef,
    WorkflowManifestRef,
)
from app.schemas.runtime.parent_tools import AssignChildToolCall


async def _criteria_ref(
    task_id: str,
    slot: str,
    description: str,
    session: AsyncSession,
    *,
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
) -> tuple[dict[str, dict[str, object]], dict[str, str]]:
    snapshots: dict[str, dict[str, object]] = {}
    artifact_producer_node_keys: dict[str, str] = {}
    nodes = await session.scalars(
        select(FlowNodeModel).where(FlowNodeModel.flow_revision_id == flow_revision_id)
    )
    for node in nodes:
        for criteria in node.criteria_json:
            snapshots[str(criteria["slot"])] = dict(criteria)
        for artifact in _json_list(_json_mapping(node.produces_json).get("artifacts", [])):
            artifact_producer_node_keys[str(artifact["slot"])] = node.node_key
    return snapshots, artifact_producer_node_keys


async def _artifact_provider_node_key_by_slot(
    session: AsyncSession,
    *,
    flow_revision_id: str,
    consumer_node_key: str,
) -> dict[str, str]:
    return {
        edge.slot: edge.provider_node_key
        for edge in await session.scalars(
            select(FlowEdgeModel).where(
                FlowEdgeModel.flow_revision_id == flow_revision_id,
                FlowEdgeModel.consumer_node_key == consumer_node_key,
                FlowEdgeModel.kind == EvidenceKind.ARTIFACT.value,
            )
        )
    }


def _ensure_surface_exists(path: Path, *, missing_message: str) -> None:
    if not _is_path_current(path):
        raise ValueError(missing_message)


def _artifact_ref_from_pointer(
    pointer: ArtifactCurrentPointerModel,
    *,
    missing_message: str,
) -> EvidenceRef:
    artifact_ref = EvidenceRef(
        kind=EvidenceKind.ARTIFACT,
        slot=pointer.slot,
        version=pointer.current_version,
        path=Path(pointer.current_path),
        description=pointer.description,
    )
    _ensure_surface_exists(artifact_ref.path, missing_message=missing_message)
    return artifact_ref


async def _criteria_ref_from_snapshot(
    task_id: str,
    slot: str,
    description: str,
    session: AsyncSession,
    *,
    snapshot: dict[str, object],
    missing_message: str,
) -> EvidenceRef:
    criteria_ref = await _criteria_ref(
        task_id,
        slot,
        description,
        session,
        path=Path(str(snapshot["path"])) if snapshot.get("path") is not None else None,
    )
    _ensure_surface_exists(criteria_ref.path, missing_message=missing_message)
    return criteria_ref


async def _load_superseded_child_assignment(
    session: AsyncSession,
    *,
    child_node: FlowNodeModel,
) -> AssignmentModel | None:
    current_assignment_id = child_node.current_assignment_id
    if current_assignment_id is None:
        return None
    current_assignment = await session.get(AssignmentModel, current_assignment_id)
    if current_assignment is None:
        raise ValueError(f"missing current assignment '{current_assignment_id}'")
    current_attempt_id = current_assignment.current_attempt_id
    if current_attempt_id is None:
        raise ValueError(
            f"assign_child cannot overwrite incomplete child assignment "
            f"'{current_assignment.assignment_key}'"
        )
    current_attempt = await session.get(AttemptModel, current_attempt_id)
    if current_attempt is None:
        raise ValueError(f"missing attempt '{current_attempt_id}'")
    if current_attempt.closed_at is None or current_attempt.status in {"pending", "running"}:
        raise ValueError(
            f"assign_child cannot overwrite open child assignment "
            f"'{current_assignment.assignment_key}'"
        )
    return current_assignment


async def _current_artifact_pointer(
    session: AsyncSession,
    *,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> ArtifactCurrentPointerModel | None:
    return cast(
        ArtifactCurrentPointerModel | None,
        await session.scalar(
            select(ArtifactCurrentPointerModel).where(
                ArtifactCurrentPointerModel.task_id == task_id,
                ArtifactCurrentPointerModel.owner_node_key == owner_node_key,
                ArtifactCurrentPointerModel.slot == slot,
            )
        ),
    )


async def _current_artifact_ref(
    session: AsyncSession,
    *,
    task_id: str,
    owner_node_key: str,
    slot: str,
    required: bool,
    missing_publication_message: str,
    missing_surface_message: str,
) -> EvidenceRef | None:
    pointer = await _current_artifact_pointer(
        session,
        task_id=task_id,
        owner_node_key=owner_node_key,
        slot=slot,
    )
    if pointer is None:
        if required:
            raise ValueError(missing_publication_message)
        return None
    return _artifact_ref_from_pointer(pointer, missing_message=missing_surface_message)


async def _resolve_assign_child_dependency_refs(
    session: AsyncSession,
    *,
    task_id: str,
    child_node: FlowNodeModel,
    flow_revision_id: str,
    typed_call: AssignChildToolCall,
) -> tuple[list[EvidenceRef], list[EvidenceRef | NodeRuntimeFileRef]]:
    criteria_snapshots, artifact_producer_node_keys = await _criteria_snapshot_by_slot(
        session,
        flow_revision_id,
    )
    artifact_provider_node_keys = await _artifact_provider_node_key_by_slot(
        session,
        flow_revision_id=flow_revision_id,
        consumer_node_key=child_node.node_key,
    )
    criteria_refs: list[EvidenceRef] = []
    for criteria in child_node.criteria_json:
        criteria_snapshot = dict(criteria)
        slot = str(criteria_snapshot["slot"])
        criteria_refs.append(
            await _criteria_ref_from_snapshot(
                task_id,
                slot,
                str(criteria_snapshot["description"]),
                session,
                snapshot=criteria_snapshot,
                missing_message=f"missing criteria provider for slot '{slot}'",
            )
        )

    consumes: list[EvidenceRef | NodeRuntimeFileRef] = []
    consumes_json = _json_mapping(child_node.consumes_json)
    for selector in _json_list(consumes_json.get("artifacts", [])):
        slot = str(selector["slot"])
        provider_node_key = artifact_provider_node_keys.get(slot)
        if provider_node_key is None:
            raise ValueError(f"missing artifact provider for slot '{slot}'")
        artifact_ref = await _current_artifact_ref(
            session,
            task_id=task_id,
            owner_node_key=provider_node_key,
            slot=slot,
            required=bool(selector.get("required", True)),
            missing_publication_message=f"missing required publication for slot '{slot}'",
            missing_surface_message=f"missing current artifact for slot '{slot}'",
        )
        if artifact_ref is not None:
            consumes.append(artifact_ref)

    for selector in _json_list(consumes_json.get("criteria", [])):
        slot = str(selector["slot"])
        criteria_snapshot_for_slot = criteria_snapshots.get(slot)
        if criteria_snapshot_for_slot is None:
            raise ValueError(f"missing criteria provider for slot '{slot}'")
        criteria_refs.append(
            await _criteria_ref_from_snapshot(
                task_id,
                slot,
                str(criteria_snapshot_for_slot["description"]),
                session,
                snapshot=criteria_snapshot_for_slot,
                missing_message=f"missing criteria provider for slot '{slot}'",
            )
        )

    supplemental_context = typed_call.payload.supplemental_durable_context
    if supplemental_context is None:
        return _dedupe_criteria_refs(criteria_refs), consumes

    for criteria_slot in supplemental_context.criteria_slots:
        supplemental_criteria_snapshot = criteria_snapshots.get(criteria_slot.slot)
        if supplemental_criteria_snapshot is None:
            raise ValueError(f"missing supplemental criteria for slot '{criteria_slot.slot}'")
        criteria_refs.append(
            await _criteria_ref_from_snapshot(
                task_id,
                criteria_slot.slot,
                str(supplemental_criteria_snapshot["description"]),
                session,
                snapshot=supplemental_criteria_snapshot,
                missing_message=f"missing supplemental criteria for slot '{criteria_slot.slot}'",
            )
        )

    for artifact_slot in supplemental_context.artifact_slots:
        provider_node_key = artifact_producer_node_keys.get(artifact_slot.slot)
        if provider_node_key is None:
            raise ValueError(
                f"missing supplemental artifact provider for slot '{artifact_slot.slot}'"
            )
        artifact_ref = await _current_artifact_ref(
            session,
            task_id=task_id,
            owner_node_key=provider_node_key,
            slot=artifact_slot.slot,
            required=True,
            missing_publication_message=(
                f"missing required publication for slot '{artifact_slot.slot}'"
            ),
            missing_surface_message=(
                f"missing supplemental artifact for slot '{artifact_slot.slot}'"
            ),
        )
        if artifact_ref is not None:
            consumes.append(artifact_ref)
    return _dedupe_criteria_refs(criteria_refs), consumes


def _planned_transient_refs(
    *,
    child_node: FlowNodeModel,
    typed_call: AssignChildToolCall,
    task_root_paths: TaskRootPaths,
) -> tuple[EvidenceRef, ...]:
    return tuple(
        EvidenceRef(
            kind=EvidenceKind.TRANSIENT,
            path=planned_transient_surface_path(
                paths=task_root_paths,
                source_path=surface.path,
                owner_node_key=child_node.node_key,
            ),
            description=surface.description,
        )
        for surface in typed_call.payload.transient_surfaces
    )


def _queue_transient_surface_copies(
    session: AsyncSession,
    *,
    typed_call: AssignChildToolCall,
    transient_refs: tuple[EvidenceRef, ...],
) -> None:
    for surface, transient_ref in zip(
        typed_call.payload.transient_surfaces,
        transient_refs,
        strict=True,
    ):
        _queue_file_copy(
            session,
            source_path=surface.path,
            destination=transient_ref.path,
        )


async def _persist_assignment_criteria_refs(
    session: AsyncSession,
    *,
    assignment_id_value: str,
    criteria_refs: list[EvidenceRef],
) -> None:
    for index, ref in enumerate(criteria_refs, start=1):
        session.add(
            AssignmentCriteriaRefModel(
                assignment_criteria_ref_id=assignment_criteria_ref_id(
                    assignment_id_value,
                    ref.slot or f"criteria-{index}",
                ),
                assignment_id=assignment_id_value,
                slot=ref.slot or f"criteria-{index}",
                path=str(ref.path),
                description=ref.description,
                version=ref.version,
                order_index=index,
            )
        )


async def _persist_attempt_consumed_refs(
    session: AsyncSession,
    *,
    attempt_id_value: str,
    consumed_refs: list[EvidenceRef | NodeRuntimeFileRef],
) -> None:
    for index, runtime_ref in enumerate(consumed_refs, start=1):
        session.add(
            AttemptConsumedRefModel(
                attempt_consumed_ref_id=attempt_consumed_ref_id(attempt_id_value, index),
                attempt_id=attempt_id_value,
                ref_kind=runtime_ref.kind.value,
                slot=getattr(runtime_ref, "slot", None),
                version=getattr(runtime_ref, "version", None),
                path=str(runtime_ref.path),
                description=runtime_ref.description,
                order_index=index,
            )
        )


def _latest_checkpoint_ref(
    *,
    state: CurrentRuntimeState,
    task_root_paths: TaskRootPaths,
) -> CheckpointFileRef | None:
    if state.current_attempt.latest_checkpoint_id is None:
        return None
    return CheckpointFileRef(
        path=(
            task_root_paths.attempts_path
            / state.current_attempt.attempt_id
            / "latest-checkpoint.md"
        ),
        description="Latest checkpoint for the current attempt.",
    )


async def _call_assign_child(
    session: AsyncSession,
    task_id: str,
    *,
    state: CurrentRuntimeState,
    dispatch: DispatchTurnModel,
    typed_call: AssignChildToolCall,
) -> AssignChildSuccess:
    assign_payload = typed_call.payload
    _ensure_no_staged_child_assignment(dispatch, action_name="assign_child")
    active_flow_revision_id = state.flow.active_flow_revision_id
    if active_flow_revision_id is None:
        raise ValueError("missing active flow revision")

    child_node = await _flow_node_by_key(
        session,
        active_flow_revision_id,
        assign_payload.child_node_key,
    )
    if child_node.parent_flow_node_id != state.current_node.flow_node_id:
        raise ValueError("assign_child target must be a direct child")

    await _consume_assignment_budget(
        session,
        budget_family="child_assignment",
        limit_field="child_assignment_limit",
        policy_key=state.current_node.policy_key,
        policy_revision_no=state.current_node.policy_revision_no,
        flow_id=state.flow.flow_id,
        flow_node_id=state.current_node.flow_node_id,
        assignment_id=state.current_assignment.assignment_id,
        attempt_id=state.current_assignment.current_attempt_id,
    )
    superseded_assignment = await _load_superseded_child_assignment(session, child_node=child_node)
    attempt_seq = await _count_for_node(session, AttemptModel, task_id, child_node.node_key)
    assignment_key = assignment_key_for_task(task_id, child_node.node_key, attempt_seq)
    attempt_id = attempt_id_for_task(task_id, child_node.node_key, attempt_seq)
    criteria_refs, consumes = await _resolve_assign_child_dependency_refs(
        session,
        task_id=task_id,
        child_node=child_node,
        flow_revision_id=active_flow_revision_id,
        typed_call=typed_call,
    )
    paths = await load_task_root_paths(session, task_id)
    transient_refs = _planned_transient_refs(
        child_node=child_node,
        typed_call=typed_call,
        task_root_paths=paths,
    )
    _queue_transient_surface_copies(session, typed_call=typed_call, transient_refs=transient_refs)

    assignment = AssignmentModel(
        assignment_id=assignment_id(assignment_key),
        task_id=task_id,
        flow_id=state.flow.flow_id,
        flow_revision_id=active_flow_revision_id,
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
    if superseded_assignment is not None and superseded_assignment.superseded_at is None:
        superseded_assignment.superseded_at = _now()
    child_node.current_assignment_id = assignment.assignment_id
    session.add(assignment)
    await session.flush()
    await _persist_assignment_criteria_refs(
        session,
        assignment_id_value=assignment.assignment_id,
        criteria_refs=criteria_refs,
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
    await _persist_attempt_consumed_refs(
        session,
        attempt_id_value=attempt_id,
        consumed_refs=[*criteria_refs, *consumes],
    )
    dispatch.staged_child_assignment_id = assignment.assignment_id
    dispatch.staged_continuation_kind = "child_assignment"
    await session.flush()
    _queue_attempt_materialization(session, task_id=task_id, attempt_id=attempt_id)
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
        latest_checkpoint_ref=_latest_checkpoint_ref(state=state, task_root_paths=paths),
    )


__all__ = ["_call_assign_child"]
