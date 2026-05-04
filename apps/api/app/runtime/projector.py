from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptModel,
    AttemptProducedRefModel,
    DispatchContinuityStateModel,
    DispatchDeliveryStateModel,
    DispatchTurnModel,
    DispatchWatchdogStateModel,
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
    ProviderEventRecordModel,
    TaskModel,
    TaskResourceBindingModel,
)
from app.runtime.contracts import (
    AssignmentConsumeRef,
    AssignmentProjection,
    CheckpointHandoff,
    CheckpointKind,
    CheckpointOutcome,
    CheckpointProjection,
    EvidenceKind,
    EvidenceRef,
    ManifestCurrentContextProjection,
    ManifestDependencyProjection,
    ManifestFilesystemRootsProjection,
    ManifestNodeConsumeProjection,
    ManifestNodeCriteriaProjection,
    ManifestNodeProduceProjection,
    ManifestNodeProjection,
    ManifestProjection,
    ManifestTaskProjection,
    ManifestWorkflowProjection,
    NodeKind,
    NodeRuntimeFileKind,
    NodeRuntimeFileRef,
    PersistedPromptRecord,
    ProduceRequirement,
    PromptFamily,
    PromptRenderRequest,
    PromptSendMode,
    RenderedPromptBundle,
    ResolvedNodeContext,
    RuntimeContextRef,
    TaskRootPaths,
)
from app.runtime.render import render_prompt_bundle
from app.runtime.resources import (
    artifact_current_json_path,
    artifact_index_json_path,
    assignment_json_path,
    checkpoint_json_path,
    continuity_state_json_path,
    delivery_state_json_path,
    ensure_task_root_layout,
    prompt_markdown_path,
    provider_events_ndjson_path,
    transient_index_json_path,
    watchdog_state_json_path,
    write_assignment_projection,
    write_checkpoint_projection,
    write_json_file,
    write_manifest_projection,
    write_ndjson_file,
    write_prompt_artifact,
)


@dataclass(frozen=True)
class CurrentRuntimeState:
    task: TaskModel
    flow: FlowModel
    flow_revision: FlowRevisionModel
    current_node: FlowNodeModel
    current_assignment: AssignmentModel
    current_attempt: AttemptModel


async def _task_resource_bindings(session: AsyncSession, task_id: str) -> dict[str, str]:
    rows = await session.scalars(
        select(TaskResourceBindingModel).where(TaskResourceBindingModel.task_id == task_id)
    )
    return {row.binding_kind: row.path for row in rows}


def _json_mapping(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload or {})


def _json_list(payload: object) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], payload or [])


async def load_task_root_paths(session: AsyncSession, task_id: str) -> TaskRootPaths:
    task = await session.get(TaskModel, task_id)
    if task is None:
        raise ValueError(f"unknown task_id '{task_id}'")
    bindings = await _task_resource_bindings(session, task_id)
    task_root = Path(task.task_root_path)
    paths = TaskRootPaths(
        task_root=task_root,
        workspace_path=Path(bindings["workspace"]),
        context_path=Path(bindings["context"]),
        criteria_path=Path(bindings["criteria"]),
        wiki_path=Path(bindings["wiki"]),
        outputs_path=Path(bindings["outputs"]),
        artifacts_path=Path(bindings["artifacts"]),
        tmp_path=Path(bindings["tmp"]),
        transfers_path=Path(bindings["transfers"]),
        runtime_path=Path(bindings["runtime"]),
        attempts_path=Path(bindings["attempts"]),
        dispatch_path=Path(bindings["dispatch"]),
    )
    ensure_task_root_layout(paths)
    return paths


def _assignment_consume_ref_from_json(payload: dict[str, object]) -> AssignmentConsumeRef:
    kind = payload.get("kind")
    if kind == NodeRuntimeFileKind.CHECKPOINT.value:
        return NodeRuntimeFileRef.model_validate(payload)
    return EvidenceRef.model_validate(payload)


def _assignment_projection_from_model(model: AssignmentModel) -> AssignmentProjection:
    return AssignmentProjection(
        assignment_key=model.assignment_key,
        node_key=model.node_key,
        summary=model.summary,
        instruction=model.instruction,
        criteria=tuple(EvidenceRef.model_validate(item) for item in model.criteria_json),
        consumes=tuple(_assignment_consume_ref_from_json(item) for item in model.consumes_json),
        produces=tuple(ProduceRequirement.model_validate(item) for item in model.produces_json),
        transient_refs=tuple(
            EvidenceRef.model_validate(item) for item in model.transient_refs_json
        ),
        task_memory_search_hints=tuple(model.task_memory_search_hints_json),
    )


def _checkpoint_projection_from_model(model: AttemptCheckpointModel) -> CheckpointProjection:
    return CheckpointProjection(
        checkpoint_kind=CheckpointKind(model.checkpoint_kind),
        outcome=None if model.outcome is None else CheckpointOutcome(model.outcome),
        handoff=CheckpointHandoff(
            summary=model.summary,
            next_step=model.next_step,
            blockers=tuple(model.blockers_json),
            risks=tuple(model.risks_json),
        ),
        produced_artifacts=tuple(
            EvidenceRef.model_validate(item) for item in model.produced_artifacts_json
        ),
        transient_refs=tuple(
            EvidenceRef.model_validate(item) for item in model.transient_refs_json
        ),
        task_memory_search_hints=tuple(model.task_memory_search_hints_json),
    )


def _resolved_node_context(node: FlowNodeModel) -> ResolvedNodeContext:
    return ResolvedNodeContext(
        node_key=node.node_key,
        node_kind=NodeKind(node.structural_kind),
        node_description=node.description,
        role_key=node.role_key,
        role_revision_no=node.role_revision_no,
        role_description=node.role_description,
        role_instruction=node.role_instruction,
        policy_key=node.policy_key,
        policy_revision_no=node.policy_revision_no,
        policy_description=node.policy_description,
        policy_instruction=node.policy_instruction,
    )


async def current_runtime_state(session: AsyncSession, task_id: str) -> CurrentRuntimeState:
    task = await session.get(TaskModel, task_id)
    if task is None:
        raise ValueError(f"unknown task_id '{task_id}'")
    flow = await session.scalar(select(FlowModel).where(FlowModel.task_id == task_id))
    if flow is None or flow.active_flow_revision_id is None or flow.current_node_key is None:
        raise ValueError(f"task '{task_id}' has no active runtime flow")
    flow_revision = await session.get(FlowRevisionModel, flow.active_flow_revision_id)
    if flow_revision is None:
        raise ValueError(f"missing active flow revision '{flow.active_flow_revision_id}'")
    current_node = await session.scalar(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == flow_revision.flow_revision_id,
            FlowNodeModel.node_key == flow.current_node_key,
        )
    )
    if current_node is None or current_node.current_assignment_id is None:
        raise ValueError(f"missing current assignment for node '{flow.current_node_key}'")
    assignment = await session.get(AssignmentModel, current_node.current_assignment_id)
    if assignment is None or assignment.current_attempt_id is None:
        raise ValueError(
            f"missing current attempt for assignment '{current_node.current_assignment_id}'"
        )
    attempt = await session.get(AttemptModel, assignment.current_attempt_id)
    if attempt is None:
        raise ValueError(f"missing attempt '{assignment.current_attempt_id}'")
    return CurrentRuntimeState(
        task=task,
        flow=flow,
        flow_revision=flow_revision,
        current_node=current_node,
        current_assignment=assignment,
        current_attempt=attempt,
    )


async def _criteria_description_by_slot(
    session: AsyncSession,
    flow_revision_id: str,
) -> dict[str, str]:
    nodes = await session.scalars(
        select(FlowNodeModel).where(FlowNodeModel.flow_revision_id == flow_revision_id)
    )
    descriptions: dict[str, str] = {}
    for node in nodes:
        for criteria in node.criteria_json:
            slot = str(criteria["slot"])
            descriptions[slot] = str(criteria["description"])
    return descriptions


async def _child_checkpoint_refs(
    session: AsyncSession,
    task_id: str,
    paths: TaskRootPaths,
    current_node: FlowNodeModel,
    flow_revision_id: str,
) -> tuple[NodeRuntimeFileRef, ...]:
    refs: list[NodeRuntimeFileRef] = []
    children = await session.scalars(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == flow_revision_id,
            FlowNodeModel.parent_node_key == current_node.node_key,
        )
    )
    for child in children:
        if child.current_assignment_id is None:
            continue
        assignment = await session.get(AssignmentModel, child.current_assignment_id)
        if assignment is None or assignment.current_attempt_id is None:
            continue
        attempt = await session.get(AttemptModel, assignment.current_attempt_id)
        if attempt is None or attempt.latest_checkpoint_id is None:
            continue
        refs.append(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=checkpoint_json_path(
                    paths=paths,
                    attempt_id=attempt.attempt_id,
                ).with_suffix(".md"),
                description=f"Latest checkpoint for direct child node '{child.node_key}'.",
            )
        )
    return tuple(refs)


async def build_manifest_projection(session: AsyncSession, task_id: str) -> ManifestProjection:
    paths = await load_task_root_paths(session, task_id)
    state = await current_runtime_state(session, task_id)
    criteria_descriptions = await _criteria_description_by_slot(
        session,
        state.flow_revision.flow_revision_id,
    )
    edges = list(
        await session.scalars(
            select(FlowEdgeModel).where(
                FlowEdgeModel.flow_revision_id == state.flow_revision.flow_revision_id
            )
        )
    )
    dependency_descriptions = {
        (edge.consumer_node_key, edge.kind, edge.slot): edge.description for edge in edges
    }
    nodes = list(
        await session.scalars(
            select(FlowNodeModel)
            .where(FlowNodeModel.flow_revision_id == state.flow_revision.flow_revision_id)
            .order_by(FlowNodeModel.order_index.asc())
        )
    )
    assignment = _assignment_projection_from_model(state.current_assignment)
    current_relevant_paths: list[RuntimeContextRef] = [
        *assignment.criteria,
        *assignment.consumes,
        *assignment.transient_refs,
    ]
    current_relevant_paths.extend(
        await _child_checkpoint_refs(
            session,
            task_id,
            paths,
            state.current_node,
            state.flow_revision.flow_revision_id,
        )
    )
    latest_checkpoint_path: Path | None = None
    if state.current_attempt.latest_checkpoint_id is not None:
        latest_checkpoint_path = checkpoint_json_path(
            paths=paths,
            attempt_id=state.current_attempt.attempt_id,
        ).with_suffix(".md")
        current_relevant_paths.append(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=latest_checkpoint_path,
                description="Latest checkpoint for the current attempt.",
            )
        )
    node_tree: list[ManifestNodeProjection] = []
    for node in nodes:
        consumes: list[ManifestNodeConsumeProjection] = []
        consumes_json = _json_mapping(node.consumes_json)
        for selector in _json_list(consumes_json.get("artifacts", [])):
            consumes.append(
                ManifestNodeConsumeProjection(
                    kind=EvidenceKind.ARTIFACT,
                    slot=str(selector["slot"]),
                    description=dependency_descriptions[
                        (node.node_key, "artifact", str(selector["slot"]))
                    ],
                    required=bool(selector.get("required", True)),
                )
            )
        for selector in _json_list(consumes_json.get("criteria", [])):
            consumes.append(
                ManifestNodeConsumeProjection(
                    kind=EvidenceKind.CRITERIA,
                    slot=str(selector["slot"]),
                    description=criteria_descriptions[str(selector["slot"])],
                    required=bool(selector.get("required", True)),
                )
            )
        node_tree.append(
            ManifestNodeProjection(
                node_key=node.node_key,
                parent_node_key=node.parent_node_key,
                child_node_keys=tuple(node.child_node_keys_json),
                node_kind=NodeKind(node.structural_kind),
                role=node.role_key,
                description=node.description,
                consumes=tuple(consumes),
                produces=tuple(
                    ManifestNodeProduceProjection.model_validate(item)
                    for item in _json_list(_json_mapping(node.produces_json).get("artifacts", []))
                ),
                criteria=tuple(
                    ManifestNodeCriteriaProjection(
                        owner_node_key=node.node_key,
                        slot=str(item["slot"]),
                        description=str(item["description"]),
                        path=paths.criteria_path / f"{item['slot']}.md",
                    )
                    for item in node.criteria_json
                ),
                depends_on_node_keys=tuple(
                    sorted(
                        edge.provider_node_key
                        for edge in edges
                        if edge.consumer_node_key == node.node_key
                    )
                ),
                depended_on_by_node_keys=tuple(
                    sorted(
                        edge.consumer_node_key
                        for edge in edges
                        if edge.provider_node_key == node.node_key
                    )
                ),
            )
        )
    return ManifestProjection(
        active_flow_revision_id=state.flow.active_flow_revision_id or "",
        generated_at=datetime.now(tz=UTC),
        task=ManifestTaskProjection(
            task_id=state.task.task_id,
            task_key=state.task.task_key,
            title=state.task.title,
            summary=state.task.summary,
            instruction=state.task.instruction,
        ),
        workflow=ManifestWorkflowProjection(
            workflow_key=state.task.workflow_key or "",
            description=state.task.summary,
        ),
        filesystem_roots=ManifestFilesystemRootsProjection(
            workspace_path=paths.workspace_path,
            context_path=paths.context_path,
            outputs_path=paths.outputs_path,
            tmp_path=paths.tmp_path,
            runtime_path=paths.runtime_path,
        ),
        current_context=ManifestCurrentContextProjection(
            current_node_key=state.current_node.node_key,
            owner_node_key=state.current_node.node_key,
            active_attempt_id=state.current_attempt.attempt_id,
            active_assignment_path=assignment_json_path(
                paths=paths,
                attempt_id=state.current_attempt.attempt_id,
            ).with_suffix(".md"),
            latest_checkpoint_path=latest_checkpoint_path,
            current_relevant_paths=tuple(current_relevant_paths),
        ),
        node_tree=tuple(node_tree),
        dependency_index=tuple(
            ManifestDependencyProjection(
                provider_node_key=edge.provider_node_key,
                consumer_node_key=edge.consumer_node_key,
                kind=edge.kind,
                slot=edge.slot,
                description=edge.description,
            )
            for edge in edges
        ),
    )


def _criteria_markdown(criteria: dict[str, Any]) -> str:
    lines = [f"# {criteria['slot']}", "", str(criteria["description"]), ""]
    lines.extend(f"- {item}" for item in cast(list[str], criteria.get("criteria", [])))
    return "\n".join(lines).rstrip() + "\n"


async def materialize_attempt_files(session: AsyncSession, task_id: str, attempt_id: str) -> None:
    paths = await load_task_root_paths(session, task_id)
    attempt = await session.get(AttemptModel, attempt_id)
    if attempt is None:
        raise ValueError(f"unknown attempt_id '{attempt_id}'")
    assignment = await session.scalar(
        select(AssignmentModel).where(AssignmentModel.current_attempt_id == attempt_id)
    )
    if assignment is None:
        assignment = await session.get(AssignmentModel, attempt.assignment_id)
    if assignment is None:
        raise ValueError(f"missing assignment for attempt '{attempt_id}'")
    write_assignment_projection(
        paths=paths,
        attempt_id=attempt_id,
        assignment=_assignment_projection_from_model(assignment),
    )
    if attempt.latest_checkpoint_id is not None:
        checkpoint = await session.get(AttemptCheckpointModel, attempt.latest_checkpoint_id)
        if checkpoint is not None:
            write_checkpoint_projection(
                paths=paths,
                attempt_id=attempt_id,
                checkpoint=_checkpoint_projection_from_model(checkpoint),
            )
    produced_refs = list(
        await session.scalars(
            select(AttemptProducedRefModel)
            .where(AttemptProducedRefModel.attempt_id == attempt_id)
            .order_by(AttemptProducedRefModel.order_index.asc())
        )
    )
    write_json_file(
        artifact_index_json_path(paths=paths, attempt_id=attempt_id),
        [
            {
                "slot": produced.slot,
                "version": produced.version,
                "path": produced.path,
                "description": produced.description,
                "published_at": produced.published_at.isoformat(),
            }
            for produced in produced_refs
        ],
    )
    checkpoint_row = None
    if attempt.latest_checkpoint_id is not None:
        checkpoint_row = await session.get(AttemptCheckpointModel, attempt.latest_checkpoint_id)
    write_json_file(
        transient_index_json_path(paths=paths, attempt_id=attempt_id),
        [
            {
                "path": checkpoint_ref.path,
                "description": checkpoint_ref.description,
            }
            for checkpoint_ref in (
                _checkpoint_projection_from_model(checkpoint_row).transient_refs
                if checkpoint_row is not None
                else ()
            )
        ],
    )


async def materialize_manifest(session: AsyncSession, task_id: str) -> ManifestProjection:
    paths = await load_task_root_paths(session, task_id)
    state = await current_runtime_state(session, task_id)
    nodes = await session.scalars(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == state.flow_revision.flow_revision_id
        )
    )
    for node in nodes:
        for criteria in node.criteria_json:
            criteria_path = paths.criteria_path / f"{criteria['slot']}.md"
            criteria_path.parent.mkdir(parents=True, exist_ok=True)
            criteria_path.write_text(_criteria_markdown(criteria), encoding="utf-8")
    manifest = await build_manifest_projection(session, task_id)
    write_manifest_projection(paths=paths, manifest=manifest)
    return manifest


async def materialize_artifact_current_pointer(
    session: AsyncSession,
    task_id: str,
    owner_node_key: str,
    slot: str,
) -> None:
    pointer = await session.scalar(
        select(ArtifactCurrentPointerModel).where(
            ArtifactCurrentPointerModel.task_id == task_id,
            ArtifactCurrentPointerModel.owner_node_key == owner_node_key,
            ArtifactCurrentPointerModel.slot == slot,
        )
    )
    if pointer is None:
        return
    paths = await load_task_root_paths(session, task_id)
    write_json_file(
        artifact_current_json_path(paths=paths, owner_node_key=owner_node_key, slot=slot),
        {
            "owner_node_key": pointer.owner_node_key,
            "slot": pointer.slot,
            "current_version": pointer.current_version,
            "current_path": pointer.current_path,
            "description": pointer.description,
            "assignment_key": pointer.assignment_key,
            "attempt_id": pointer.attempt_id,
            "published_at": pointer.published_at.isoformat(),
            "supersedes_path": pointer.supersedes_path,
        },
    )


async def materialize_dispatch_files(session: AsyncSession, task_id: str, dispatch_id: str) -> None:
    paths = await load_task_root_paths(session, task_id)
    delivery_state = await session.get(DispatchDeliveryStateModel, dispatch_id)
    continuity_state = await session.get(DispatchContinuityStateModel, dispatch_id)
    watchdog_state = await session.get(DispatchWatchdogStateModel, dispatch_id)
    provider_events = list(
        await session.scalars(
            select(ProviderEventRecordModel)
            .where(ProviderEventRecordModel.dispatch_id == dispatch_id)
            .order_by(ProviderEventRecordModel.occurred_at.asc())
        )
    )
    if delivery_state is not None:
        write_json_file(
            delivery_state_json_path(paths=paths, dispatch_id=dispatch_id),
            {
                "dispatch_id": delivery_state.dispatch_id,
                "attempt_id": delivery_state.attempt_id,
                "assignment_key": delivery_state.assignment_key,
                "node_key": delivery_state.node_key,
                "transport_family": delivery_state.transport_family,
                "transport_state": delivery_state.transport_state,
                "controller_observation_state": delivery_state.controller_observation_state,
                "last_provider_event_kind": delivery_state.last_provider_event_kind,
                "provider_final_status": delivery_state.provider_final_status,
                "provider_error": delivery_state.provider_error,
                "send_mode": delivery_state.send_mode,
                "previous_dispatch_id": delivery_state.previous_dispatch_id,
                "superseded_by_dispatch_id": delivery_state.superseded_by_dispatch_id,
                "prepared_at": delivery_state.prepared_at.isoformat(),
                "accepted_at": (
                    delivery_state.accepted_at.isoformat()
                    if delivery_state.accepted_at is not None
                    else None
                ),
                "last_provider_signal_at": (
                    delivery_state.last_provider_signal_at.isoformat()
                    if delivery_state.last_provider_signal_at is not None
                    else None
                ),
                "last_controller_progress_at": (
                    delivery_state.last_controller_progress_at.isoformat()
                    if delivery_state.last_controller_progress_at is not None
                    else None
                ),
                "last_controller_terminal_at": (
                    delivery_state.last_controller_terminal_at.isoformat()
                    if delivery_state.last_controller_terminal_at is not None
                    else None
                ),
                "updated_at": delivery_state.updated_at.isoformat(),
            },
        )
    if continuity_state is not None:
        write_json_file(
            continuity_state_json_path(paths=paths, dispatch_id=dispatch_id),
            {
                "dispatch_id": continuity_state.dispatch_id,
                "attempt_id": continuity_state.attempt_id,
                "assignment_key": continuity_state.assignment_key,
                "node_key": continuity_state.node_key,
                "continuity_state": continuity_state.continuity_state,
                "previous_response_id": continuity_state.previous_response_id,
                "session_key_present": continuity_state.session_key_present,
                "invalidation_reason": continuity_state.invalidation_reason,
                "updated_at": continuity_state.updated_at.isoformat(),
            },
        )
    if watchdog_state is not None:
        write_json_file(
            watchdog_state_json_path(paths=paths, dispatch_id=dispatch_id),
            {
                "dispatch_id": watchdog_state.dispatch_id,
                "attempt_id": watchdog_state.attempt_id,
                "assignment_key": watchdog_state.assignment_key,
                "node_key": watchdog_state.node_key,
                "watchdog_state": watchdog_state.watchdog_state,
                "current_watchdog_kind": watchdog_state.current_watchdog_kind,
                "current_watchdog_reason": watchdog_state.current_watchdog_reason,
                "recovery_action": watchdog_state.recovery_action,
                "recovery_reason": watchdog_state.recovery_reason,
                "recovery_dispatch_id": watchdog_state.recovery_dispatch_id,
                "previous_dispatch_id": watchdog_state.previous_dispatch_id,
                "superseded_by_dispatch_id": watchdog_state.superseded_by_dispatch_id,
                "classified_at": watchdog_state.classified_at.isoformat(),
                "updated_at": watchdog_state.updated_at.isoformat(),
            },
        )
    write_ndjson_file(
        provider_events_ndjson_path(paths=paths, dispatch_id=dispatch_id),
        [row.event_payload_json for row in provider_events],
    )


async def render_dispatch_prompt(
    session: AsyncSession,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> tuple[RenderedPromptBundle, PersistedPromptRecord]:
    manifest = await materialize_manifest(session, task_id)
    attempt = await session.get(AttemptModel, dispatch.attempt_id)
    if attempt is None:
        raise ValueError(f"missing attempt '{dispatch.attempt_id}'")
    assignment = await session.get(AssignmentModel, dispatch.assignment_id)
    if assignment is None:
        raise ValueError(f"missing assignment '{dispatch.assignment_id}'")
    checkpoint = None
    if attempt.latest_checkpoint_id is not None:
        checkpoint_row = await session.get(AttemptCheckpointModel, attempt.latest_checkpoint_id)
        if checkpoint_row is not None:
            checkpoint = _checkpoint_projection_from_model(checkpoint_row)
    state = await current_runtime_state(session, task_id)
    bundle = render_prompt_bundle(
        PromptRenderRequest(
            prompt_family=PromptFamily(dispatch.prompt_name),
            send_mode=PromptSendMode(dispatch.send_mode),
            task_id=task_id,
            current_node=_resolved_node_context(state.current_node),
            manifest=manifest,
            assignment=_assignment_projection_from_model(assignment),
            latest_checkpoint=checkpoint,
        )
    )
    paths = await load_task_root_paths(session, task_id)
    record = PersistedPromptRecord(
        dispatch_id=dispatch.dispatch_id,
        node_key=dispatch.node_key,
        attempt_id=attempt.attempt_id,
        assignment_key=assignment.assignment_key,
        prompt_name=PromptFamily(dispatch.prompt_name),
        send_mode=PromptSendMode(dispatch.send_mode),
        rendered_markdown_path=prompt_markdown_path(paths=paths, dispatch_id=dispatch.dispatch_id),
        content_hash=bundle.content_hash,
        rendered_at=dispatch.rendered_at,
    )
    write_prompt_artifact(paths=paths, prompt_record=record, full_markdown=bundle.full_markdown)
    return bundle, record
