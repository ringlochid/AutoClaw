from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload

from app.db.models import (
    AssignmentModel,
    AttemptCheckpointModel,
    AttemptConsumedRefModel,
    AttemptModel,
    CompiledPlanModel,
    DispatchTurnModel,
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
    TaskModel,
    TaskResourceBindingModel,
    WorkflowRevisionModel,
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
    ProduceRequirement,
    ResolvedNodeContext,
    RuntimeContextRef,
    TaskRootPaths,
)
from app.runtime.resources import (
    assignment_json_path,
    checkpoint_json_path,
    criteria_file_path,
    ensure_task_root_layout,
    localize_manifest_projection,
)


@dataclass(frozen=True)
class CurrentRuntimeState:
    task: TaskModel
    flow: FlowModel
    flow_revision: FlowRevisionModel
    current_node: FlowNodeModel
    current_assignment: AssignmentModel
    current_attempt: AttemptModel


_REQUIRED_TASK_ROOT_BINDINGS = frozenset(
    {
        "workspace",
        "context",
        "criteria",
        "wiki",
        "outputs",
        "artifacts",
        "tmp",
        "transfers",
        "runtime",
        "attempts",
        "dispatch",
    }
)


def _json_mapping(payload: object) -> dict[str, Any]:
    return cast(dict[str, Any], payload or {})


def _json_list(payload: object) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], payload or [])


def _int_or_none(value: object) -> int | None:
    return int(value) if isinstance(value, int | str) else None


def _sorted_unique(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _flow_node_parent_key_by_id(nodes: list[FlowNodeModel]) -> dict[str, str | None]:
    nodes_by_id = {node.flow_node_id: node for node in nodes}
    parent_key_by_id: dict[str, str | None] = {}
    for node in nodes:
        if node.parent_flow_node_id is None:
            parent_key_by_id[node.flow_node_id] = None
            continue
        parent = nodes_by_id.get(node.parent_flow_node_id)
        if parent is None:
            raise ValueError(
                "missing relational parent flow node "
                f"'{node.parent_flow_node_id}' for node '{node.node_key}'"
            )
        parent_key_by_id[node.flow_node_id] = parent.node_key
    return parent_key_by_id


def _child_node_keys_by_parent_id(nodes: list[FlowNodeModel]) -> dict[str, tuple[str, ...]]:
    children_by_parent_id: dict[str, list[FlowNodeModel]] = {}
    for node in nodes:
        if node.parent_flow_node_id is None:
            continue
        children_by_parent_id.setdefault(node.parent_flow_node_id, []).append(node)
    return {
        parent_flow_node_id: tuple(
            child.node_key
            for child in sorted(children, key=lambda child: (child.order_index, child.node_key))
        )
        for parent_flow_node_id, children in children_by_parent_id.items()
    }


async def _task_with_root_bindings(
    session: AsyncSession,
    task_id: str,
) -> tuple[TaskModel, dict[str, str]]:
    rows = list(
        (
            await session.execute(
                select(TaskModel, TaskResourceBindingModel)
                .options(raiseload("*"))
                .outerjoin(
                    TaskResourceBindingModel,
                    TaskResourceBindingModel.task_id == TaskModel.task_id,
                )
                .where(TaskModel.task_id == task_id)
                .order_by(TaskResourceBindingModel.binding_kind.asc())
            )
        ).all()
    )
    if not rows:
        raise ValueError(f"unknown task_id '{task_id}'")
    task = rows[0][0]
    bindings = {binding.binding_kind: binding.path for _, binding in rows if binding is not None}
    missing = _REQUIRED_TASK_ROOT_BINDINGS.difference(bindings)
    if missing:
        raise ValueError(
            f"task '{task_id}' is missing task root bindings: {', '.join(sorted(missing))}"
        )
    return task, bindings


async def load_task_root_paths(session: AsyncSession, task_id: str) -> TaskRootPaths:
    task, bindings = await _task_with_root_bindings(session, task_id)
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


def _runtime_context_ref_from_attempt_consumed_model(
    model: AttemptConsumedRefModel,
) -> RuntimeContextRef:
    if model.ref_kind == NodeRuntimeFileKind.CHECKPOINT.value:
        return NodeRuntimeFileRef(
            kind=NodeRuntimeFileKind.CHECKPOINT,
            path=Path(model.path),
            description=model.description,
        )
    return EvidenceRef(
        kind=EvidenceKind(model.ref_kind),
        slot=model.slot,
        version=model.version,
        path=Path(model.path),
        description=model.description,
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


async def _joined_current_runtime_state(
    session: AsyncSession,
    task_id: str,
) -> CurrentRuntimeState | None:
    row = cast(
        tuple[
            TaskModel,
            FlowModel,
            FlowRevisionModel,
            FlowNodeModel,
            AssignmentModel,
            AttemptModel,
        ]
        | None,
        (
            await session.execute(
                select(
                    TaskModel,
                    FlowModel,
                    FlowRevisionModel,
                    FlowNodeModel,
                    AssignmentModel,
                    AttemptModel,
                )
                .options(raiseload("*"))
                .join(FlowModel, FlowModel.task_id == TaskModel.task_id)
                .join(
                    FlowRevisionModel,
                    FlowRevisionModel.flow_revision_id == FlowModel.active_flow_revision_id,
                )
                .join(
                    FlowNodeModel,
                    and_(
                        FlowNodeModel.flow_revision_id == FlowRevisionModel.flow_revision_id,
                        FlowNodeModel.node_key == FlowModel.current_node_key,
                    ),
                )
                .join(
                    AssignmentModel,
                    AssignmentModel.assignment_id == FlowNodeModel.current_assignment_id,
                )
                .join(
                    AttemptModel,
                    AttemptModel.attempt_id == AssignmentModel.current_attempt_id,
                )
                .where(TaskModel.task_id == task_id)
            )
        ).one_or_none(),
    )
    if row is None:
        return None
    task, flow, flow_revision, current_node, assignment, attempt = row
    return CurrentRuntimeState(
        task=task,
        flow=flow,
        flow_revision=flow_revision,
        current_node=current_node,
        current_assignment=assignment,
        current_attempt=attempt,
    )


async def current_runtime_state(session: AsyncSession, task_id: str) -> CurrentRuntimeState:
    state = await _joined_current_runtime_state(session, task_id)
    if state is not None and state.flow.current_open_dispatch_id is None:
        return state
    if state is not None and state.flow.current_open_dispatch_id is not None:
        dispatch = await session.get(DispatchTurnModel, state.flow.current_open_dispatch_id)
        if dispatch is None:
            raise ValueError(f"missing dispatch '{state.flow.current_open_dispatch_id}'")
        return await dispatch_runtime_state(
            session,
            task_id=task_id,
            dispatch=dispatch,
        )
    task = await session.get(TaskModel, task_id)
    if task is None:
        raise ValueError(f"unknown task_id '{task_id}'")
    flow = await session.scalar(
        select(FlowModel).options(raiseload("*")).where(FlowModel.task_id == task_id)
    )
    if flow is None:
        raise ValueError(f"task '{task_id}' has no active runtime flow")
    if flow.current_open_dispatch_id is not None:
        dispatch = await session.get(DispatchTurnModel, flow.current_open_dispatch_id)
        if dispatch is None:
            raise ValueError(f"missing dispatch '{flow.current_open_dispatch_id}'")
        return await dispatch_runtime_state(
            session,
            task_id=task_id,
            dispatch=dispatch,
        )
    if flow.active_flow_revision_id is None or flow.current_node_key is None:
        raise ValueError(f"task '{task_id}' has no active runtime flow")
    flow_revision = await session.get(FlowRevisionModel, flow.active_flow_revision_id)
    if flow_revision is None:
        raise ValueError(f"missing active flow revision '{flow.active_flow_revision_id}'")
    current_node = await session.scalar(
        select(FlowNodeModel)
        .options(raiseload("*"))
        .where(
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


async def _joined_dispatch_runtime_state(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> CurrentRuntimeState | None:
    if (
        dispatch.flow_revision_id is None
        or dispatch.assignment_id is None
        or dispatch.attempt_id is None
    ):
        return None
    node_join = (
        FlowNodeModel.flow_node_id == dispatch.flow_node_id
        if dispatch.flow_node_id is not None
        else and_(
            FlowNodeModel.flow_revision_id == dispatch.flow_revision_id,
            FlowNodeModel.node_key == dispatch.node_key,
        )
    )
    row = cast(
        tuple[
            TaskModel,
            FlowModel,
            FlowRevisionModel,
            FlowNodeModel,
            AssignmentModel,
            AttemptModel,
        ]
        | None,
        (
            await session.execute(
                select(
                    TaskModel,
                    FlowModel,
                    FlowRevisionModel,
                    FlowNodeModel,
                    AssignmentModel,
                    AttemptModel,
                )
                .options(raiseload("*"))
                .join(FlowModel, FlowModel.task_id == TaskModel.task_id)
                .join(
                    FlowRevisionModel,
                    FlowRevisionModel.flow_revision_id == dispatch.flow_revision_id,
                )
                .join(FlowNodeModel, node_join)
                .join(
                    AssignmentModel,
                    AssignmentModel.assignment_id == dispatch.assignment_id,
                )
                .join(
                    AttemptModel,
                    AttemptModel.attempt_id == dispatch.attempt_id,
                )
                .where(
                    TaskModel.task_id == task_id,
                    FlowModel.flow_id == dispatch.flow_id,
                    FlowNodeModel.flow_revision_id == dispatch.flow_revision_id,
                )
            )
        ).one_or_none(),
    )
    if row is None:
        return None
    task, flow, flow_revision, current_node, assignment, attempt = row
    return CurrentRuntimeState(
        task=task,
        flow=flow,
        flow_revision=flow_revision,
        current_node=current_node,
        current_assignment=assignment,
        current_attempt=attempt,
    )


async def dispatch_runtime_state(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> CurrentRuntimeState:
    state = await _joined_dispatch_runtime_state(
        session,
        task_id=task_id,
        dispatch=dispatch,
    )
    if state is not None:
        return state
    task = await session.get(TaskModel, task_id)
    if task is None:
        raise ValueError(f"unknown task_id '{task_id}'")
    flow = await session.scalar(
        select(FlowModel).options(raiseload("*")).where(FlowModel.task_id == task_id)
    )
    if flow is None:
        raise ValueError(f"task '{task_id}' has no runtime flow")
    if dispatch.flow_revision_id is None:
        raise ValueError(f"dispatch '{dispatch.dispatch_id}' has no flow revision")
    flow_revision = await session.get(FlowRevisionModel, dispatch.flow_revision_id)
    if flow_revision is None:
        raise ValueError(f"missing flow revision '{dispatch.flow_revision_id}'")
    if dispatch.flow_node_id is not None:
        current_node = await session.get(FlowNodeModel, dispatch.flow_node_id)
    else:
        current_node = await session.scalar(
            select(FlowNodeModel)
            .options(raiseload("*"))
            .where(
                FlowNodeModel.flow_revision_id == dispatch.flow_revision_id,
                FlowNodeModel.node_key == dispatch.node_key,
            )
        )
    if current_node is None:
        raise ValueError(f"missing flow node for dispatch '{dispatch.dispatch_id}'")
    if dispatch.assignment_id is None:
        raise ValueError(f"dispatch '{dispatch.dispatch_id}' has no assignment")
    assignment = await session.get(AssignmentModel, dispatch.assignment_id)
    if assignment is None:
        raise ValueError(f"missing assignment '{dispatch.assignment_id}'")
    if dispatch.attempt_id is None:
        raise ValueError(f"dispatch '{dispatch.dispatch_id}' has no attempt")
    attempt = await session.get(AttemptModel, dispatch.attempt_id)
    if attempt is None:
        raise ValueError(f"missing attempt '{dispatch.attempt_id}'")
    return CurrentRuntimeState(
        task=task,
        flow=flow,
        flow_revision=flow_revision,
        current_node=current_node,
        current_assignment=assignment,
        current_attempt=attempt,
    )


def _criteria_description_by_slot(
    nodes: list[FlowNodeModel],
) -> dict[str, str]:
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
    recorded_at_cutoff: datetime | None = None,
) -> tuple[NodeRuntimeFileRef, ...]:
    refs: list[NodeRuntimeFileRef] = []
    children = list(
        await session.scalars(
            select(FlowNodeModel)
            .options(raiseload("*"))
            .where(
                FlowNodeModel.flow_revision_id == flow_revision_id,
                FlowNodeModel.parent_flow_node_id == current_node.flow_node_id,
            )
            .order_by(FlowNodeModel.order_index.asc())
        )
    )
    if not children:
        return ()
    child_attempt_ids: dict[str, str] = {}
    if recorded_at_cutoff is None:
        child_attempt_ids.update(
            {
                child.node_key: attempt.attempt_id
                for child, _, attempt in cast(
                    list[tuple[FlowNodeModel, AssignmentModel | None, AttemptModel | None]],
                    (
                        await session.execute(
                            select(FlowNodeModel, AssignmentModel, AttemptModel)
                            .options(raiseload("*"))
                            .outerjoin(
                                AssignmentModel,
                                AssignmentModel.assignment_id
                                == FlowNodeModel.current_assignment_id,
                            )
                            .outerjoin(
                                AttemptModel,
                                AttemptModel.attempt_id == AssignmentModel.current_attempt_id,
                            )
                            .where(
                                FlowNodeModel.flow_revision_id == flow_revision_id,
                                FlowNodeModel.parent_flow_node_id == current_node.flow_node_id,
                            )
                            .order_by(FlowNodeModel.order_index.asc())
                        )
                    ).all(),
                )
                if attempt is not None and attempt.latest_checkpoint_id is not None
            }
        )
    else:
        child_node_keys = [child.node_key for child in children]
        for node_key, checkpoint_attempt_id in cast(
            list[tuple[str, str]],
            (
                await session.execute(
                    select(AttemptModel.node_key, AttemptCheckpointModel.attempt_id)
                    .join(
                        AttemptModel,
                        AttemptModel.attempt_id == AttemptCheckpointModel.attempt_id,
                    )
                    .where(
                        AttemptModel.task_id == task_id,
                        AttemptModel.node_key.in_(child_node_keys),
                        AttemptCheckpointModel.recorded_at <= recorded_at_cutoff,
                    )
                    .order_by(
                        AttemptModel.node_key.asc(),
                        AttemptCheckpointModel.recorded_at.desc(),
                        AttemptCheckpointModel.checkpoint_id.desc(),
                    )
                )
            ).all(),
        ):
            child_attempt_ids.setdefault(node_key, checkpoint_attempt_id)
    for child in children:
        attempt_id: str | None = child_attempt_ids.get(child.node_key)
        if attempt_id is None:
            continue
        refs.append(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=checkpoint_json_path(
                    paths=paths,
                    attempt_id=attempt_id,
                ).with_suffix(".md"),
                description=f"Latest checkpoint for direct child node '{child.node_key}'.",
            )
        )
    return tuple(refs)


async def _latest_checkpoint_for_attempt_before_cutoff(
    session: AsyncSession,
    *,
    attempt_id: str,
    recorded_at_cutoff: datetime | None,
) -> AttemptCheckpointModel | None:
    if recorded_at_cutoff is None:
        return cast(
            AttemptCheckpointModel | None,
            await session.scalar(
                select(AttemptCheckpointModel)
                .options(raiseload("*"))
                .where(AttemptCheckpointModel.attempt_id == attempt_id)
                .order_by(AttemptCheckpointModel.recorded_at.desc())
            ),
        )
    return cast(
        AttemptCheckpointModel | None,
        await session.scalar(
            select(AttemptCheckpointModel)
            .options(raiseload("*"))
            .where(
                AttemptCheckpointModel.attempt_id == attempt_id,
                AttemptCheckpointModel.recorded_at <= recorded_at_cutoff,
            )
            .order_by(AttemptCheckpointModel.recorded_at.desc())
        ),
    )


def _checkpoint_attempt_id_from_path(path: Path) -> str | None:
    if path.name not in {"latest-checkpoint.md", "latest-checkpoint.json"}:
        return None
    attempt_id = path.parent.name
    return attempt_id or None


def _checkpoint_refs(
    current_relevant_paths: tuple[RuntimeContextRef, ...],
) -> tuple[NodeRuntimeFileRef, ...]:
    return tuple(
        ref
        for ref in current_relevant_paths
        if isinstance(ref, NodeRuntimeFileRef) and ref.kind == NodeRuntimeFileKind.CHECKPOINT
    )


async def _latest_relevant_checkpoint_candidate(
    session: AsyncSession,
    *,
    current_relevant_paths: tuple[RuntimeContextRef, ...],
    latest_checkpoint_path: Path | None,
    recorded_at_cutoff: datetime | None,
) -> tuple[Path, AttemptCheckpointModel] | None:
    relevant_candidates: list[tuple[AttemptCheckpointModel, Path]] = []
    for checkpoint_ref in _checkpoint_refs(current_relevant_paths):
        if latest_checkpoint_path is not None and checkpoint_ref.path == latest_checkpoint_path:
            continue
        attempt_id = _checkpoint_attempt_id_from_path(checkpoint_ref.path)
        if attempt_id is None:
            continue
        checkpoint_row = await _latest_checkpoint_for_attempt_before_cutoff(
            session,
            attempt_id=attempt_id,
            recorded_at_cutoff=recorded_at_cutoff,
        )
        if checkpoint_row is None:
            continue
        relevant_candidates.append((checkpoint_row, checkpoint_ref.path))
    if not relevant_candidates:
        return None
    checkpoint_row, checkpoint_path = sorted(
        relevant_candidates,
        key=lambda candidate: (
            -candidate[0].recorded_at.timestamp(),
            str(candidate[1]),
        ),
    )[0]
    return checkpoint_path, checkpoint_row


async def _workflow_description(
    session: AsyncSession,
    *,
    flow: FlowModel,
    task: TaskModel,
    fallback_description: str,
) -> str:
    if task.workflow_key:
        compiled_plan = await session.scalar(
            select(CompiledPlanModel)
            .options(raiseload("*"))
            .where(CompiledPlanModel.compiled_plan_id == flow.compiled_plan_id)
        )
        if compiled_plan is None:
            raise ValueError(
                f"missing compiled plan '{flow.compiled_plan_id}' for task '{task.task_id}'"
            )
        workflow_revision = await session.scalar(
            select(WorkflowRevisionModel).where(
                WorkflowRevisionModel.workflow_key == task.workflow_key,
                WorkflowRevisionModel.revision_no == compiled_plan.definition_revision_no,
            )
        )
        if workflow_revision is None:
            raise ValueError(
                "missing pinned workflow revision "
                f"'{task.workflow_key}@{compiled_plan.definition_revision_no}'"
            )
        description = workflow_revision.content_json.get("description")
        if isinstance(description, str) and description.strip():
            return description
    return fallback_description


async def _build_manifest_projection_for_state(
    session: AsyncSession,
    *,
    task_id: str,
    state: CurrentRuntimeState,
    current_relevant_cutoff: datetime | None = None,
) -> ManifestProjection:
    paths = await load_task_root_paths(session, task_id)
    nodes = list(
        await session.scalars(
            select(FlowNodeModel)
            .options(raiseload("*"))
            .where(FlowNodeModel.flow_revision_id == state.flow_revision.flow_revision_id)
            .order_by(FlowNodeModel.order_index.asc())
        )
    )
    parent_node_key_by_id = _flow_node_parent_key_by_id(nodes)
    child_node_keys_by_parent_id = _child_node_keys_by_parent_id(nodes)
    criteria_descriptions = _criteria_description_by_slot(nodes)
    edges = list(
        await session.scalars(
            select(FlowEdgeModel)
            .options(raiseload("*"))
            .where(FlowEdgeModel.flow_revision_id == state.flow_revision.flow_revision_id)
        )
    )
    dependency_descriptions = {
        (edge.consumer_node_key, edge.kind, edge.slot): edge.description for edge in edges
    }
    assignment = _assignment_projection_from_model(state.current_assignment)
    attempt_consumed_refs = list(
        await session.scalars(
            select(AttemptConsumedRefModel)
            .options(raiseload("*"))
            .where(AttemptConsumedRefModel.attempt_id == state.current_attempt.attempt_id)
            .order_by(AttemptConsumedRefModel.order_index.asc())
        )
    )
    workflow_description = await _workflow_description(
        session,
        flow=state.flow,
        task=state.task,
        fallback_description=state.task.summary,
    )
    current_relevant_paths: list[RuntimeContextRef] = [
        *(
            _runtime_context_ref_from_attempt_consumed_model(model)
            for model in attempt_consumed_refs
        ),
        *assignment.transient_refs,
    ]
    current_relevant_paths.extend(
        await _child_checkpoint_refs(
            session,
            task_id,
            paths,
            state.current_node,
            state.flow_revision.flow_revision_id,
            current_relevant_cutoff,
        )
    )
    latest_checkpoint_path: Path | None = None
    latest_checkpoint = await _latest_checkpoint_for_attempt_before_cutoff(
        session,
        attempt_id=state.current_attempt.attempt_id,
        recorded_at_cutoff=current_relevant_cutoff,
    )
    if latest_checkpoint is not None:
        latest_checkpoint_path = checkpoint_json_path(
            paths=paths,
            attempt_id=latest_checkpoint.attempt_id,
        ).with_suffix(".md")
        current_relevant_paths.append(
            NodeRuntimeFileRef(
                kind=NodeRuntimeFileKind.CHECKPOINT,
                path=latest_checkpoint_path,
                description="Latest durable checkpoint for the current attempt.",
            )
        )
    latest_relevant_checkpoint = await _latest_relevant_checkpoint_candidate(
        session,
        current_relevant_paths=tuple(current_relevant_paths),
        latest_checkpoint_path=latest_checkpoint_path,
        recorded_at_cutoff=current_relevant_cutoff,
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
                parent_node_key=parent_node_key_by_id[node.flow_node_id],
                child_node_keys=child_node_keys_by_parent_id.get(node.flow_node_id, ()),
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
                        path=(
                            Path(str(item["path"]))
                            if item.get("path") is not None
                            else criteria_file_path(
                                paths=paths,
                                slot=str(item["slot"]),
                                version=_int_or_none(item.get("version")),
                            )
                        ),
                    )
                    for item in node.criteria_json
                ),
                depends_on_node_keys=_sorted_unique(
                    [
                        edge.provider_node_key
                        for edge in edges
                        if edge.consumer_node_key == node.node_key
                    ]
                ),
                depended_on_by_node_keys=_sorted_unique(
                    [
                        edge.consumer_node_key
                        for edge in edges
                        if edge.provider_node_key == node.node_key
                    ]
                ),
            )
        )
    manifest = ManifestProjection(
        active_flow_revision_id=state.flow_revision.flow_revision_id,
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
            description=workflow_description,
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
            latest_relevant_checkpoint_path=(
                latest_relevant_checkpoint[0] if latest_relevant_checkpoint is not None else None
            ),
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
    return localize_manifest_projection(paths=paths, manifest=manifest)


async def build_manifest_projection(session: AsyncSession, task_id: str) -> ManifestProjection:
    state = await current_runtime_state(session, task_id)
    return await _build_manifest_projection_for_state(
        session,
        task_id=task_id,
        state=state,
    )


async def build_dispatch_manifest_projection(
    session: AsyncSession,
    *,
    task_id: str,
    dispatch: DispatchTurnModel,
) -> ManifestProjection:
    state = await dispatch_runtime_state(
        session,
        task_id=task_id,
        dispatch=dispatch,
    )
    return await _build_manifest_projection_for_state(
        session,
        task_id=task_id,
        state=state,
        current_relevant_cutoff=dispatch.rendered_at,
    )


def _criteria_markdown(criteria: dict[str, Any]) -> str:
    lines = [f"# {criteria['slot']}", "", str(criteria["description"]), ""]
    lines.extend(f"- {item}" for item in cast(list[str], criteria.get("criteria", [])))
    return "\n".join(lines).rstrip() + "\n"
