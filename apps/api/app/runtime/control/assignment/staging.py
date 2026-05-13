from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import (
    ArtifactCurrentPointerModel,
    FlowEdgeModel,
    FlowNodeModel,
)
from app.runtime.contracts import EvidenceKind, EvidenceRef, NodeRuntimeFileRef
from app.runtime.control.assignment.supersession import load_superseded_child_assignment
from app.runtime.control.failures import (
    missing_required_publication_error,
    semantic_missing_resource_error,
)
from app.runtime.effects.validation import current_surfaced_ref_failure
from app.runtime.task_root.reads import read_task_root_paths
from app.schemas.runtime.parent_tools import AssignChildToolCall


def _json_mapping(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload or {})


def _json_list(payload: object) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], payload or [])


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
        task_paths = await read_task_root_paths(session, task_id)
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
        select(FlowNodeModel)
        .options(raiseload("*"))
        .where(FlowNodeModel.flow_revision_id == flow_revision_id)
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
            select(FlowEdgeModel)
            .options(raiseload("*"))
            .where(
                FlowEdgeModel.flow_revision_id == flow_revision_id,
                FlowEdgeModel.consumer_node_key == consumer_node_key,
                FlowEdgeModel.kind == EvidenceKind.ARTIFACT.value,
            )
        )
    }


async def _ensure_current_ref_surface(
    session: AsyncSession,
    *,
    task_id: str,
    ref: EvidenceRef | NodeRuntimeFileRef,
    missing_message: str,
) -> None:
    failure = await current_surfaced_ref_failure(
        session,
        task_id=task_id,
        ref=ref.model_dump(mode="json"),
    )
    if failure is not None:
        raise semantic_missing_resource_error(missing_message)


async def _artifact_ref_from_pointer(
    session: AsyncSession,
    *,
    task_id: str,
    pointer: ArtifactCurrentPointerModel,
    missing_message: str,
) -> EvidenceRef:
    artifact_ref = EvidenceRef(
        kind=EvidenceKind.ARTIFACT,
        slot=pointer.slot,
        version=pointer.current_version,
        path=Path(pointer.current_path),
        description=pointer.description,
    )
    await _ensure_current_ref_surface(
        session,
        task_id=task_id,
        ref=artifact_ref,
        missing_message=missing_message,
    )
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
    await _ensure_current_ref_surface(
        session,
        task_id=task_id,
        ref=criteria_ref,
        missing_message=missing_message,
    )
    return criteria_ref


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
            select(ArtifactCurrentPointerModel)
            .options(raiseload("*"))
            .where(
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
            raise missing_required_publication_error(missing_publication_message)
        return None
    return await _artifact_ref_from_pointer(
        session,
        task_id=task_id,
        pointer=pointer,
        missing_message=missing_surface_message,
    )


async def resolve_assign_child_dependency_refs(
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
    criteria_refs, consumes = await _base_dependency_refs(
        session,
        task_id=task_id,
        child_node=child_node,
        criteria_snapshots=criteria_snapshots,
        artifact_provider_node_keys=artifact_provider_node_keys,
    )
    supplemental_context = typed_call.payload.supplemental_durable_context
    if supplemental_context is None:
        return _dedupe_criteria_refs(criteria_refs), consumes
    await _supplemental_dependency_refs(
        session,
        task_id=task_id,
        supplemental_context=supplemental_context,
        criteria_snapshots=criteria_snapshots,
        artifact_producer_node_keys=artifact_producer_node_keys,
        criteria_refs=criteria_refs,
        consumes=consumes,
    )
    return _dedupe_criteria_refs(criteria_refs), consumes


async def _base_dependency_refs(
    session: AsyncSession,
    *,
    task_id: str,
    child_node: FlowNodeModel,
    criteria_snapshots: dict[str, dict[str, object]],
    artifact_provider_node_keys: dict[str, str],
) -> tuple[list[EvidenceRef], list[EvidenceRef | NodeRuntimeFileRef]]:
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
            raise semantic_missing_resource_error(f"missing artifact provider for slot '{slot}'")
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
            raise semantic_missing_resource_error(f"missing criteria provider for slot '{slot}'")
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
    return criteria_refs, consumes


async def _supplemental_dependency_refs(
    session: AsyncSession,
    *,
    task_id: str,
    supplemental_context: Any,
    criteria_snapshots: dict[str, dict[str, object]],
    artifact_producer_node_keys: dict[str, str],
    criteria_refs: list[EvidenceRef],
    consumes: list[EvidenceRef | NodeRuntimeFileRef],
) -> None:
    for criteria_slot in supplemental_context.criteria_slots:
        supplemental_criteria_snapshot = criteria_snapshots.get(criteria_slot.slot)
        if supplemental_criteria_snapshot is None:
            raise semantic_missing_resource_error(
                f"missing supplemental criteria for slot '{criteria_slot.slot}'"
            )
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
            raise semantic_missing_resource_error(
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


__all__ = [
    "load_superseded_child_assignment",
    "resolve_assign_child_dependency_refs",
]
