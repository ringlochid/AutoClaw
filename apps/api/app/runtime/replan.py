from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.compiler.lower import persist_compiled_plan
from app.compiler.normalize import normalize_resolved_workflow
from app.compiler.plan_hash import compute_plan_hash
from app.compiler.resolve import (
    merge_node_resources,
    merge_skill_refs,
    merge_task_defaults,
    merge_workflow_defaults,
    resolve_workflow_seed_content,
)
from app.compiler.validate import validate_resolved_workflow
from app.core.enums import FlowRevisionStatus, FlowStatus, NodeAttemptStatus, NodePlanRevisionStatus
from app.core.errors import ConflictError, InvalidDefinitionError, NotFoundError
from app.db.models.runtime import (
    CompiledPlan,
    Flow,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodePlanRevision,
    TaskCompose,
)
from app.runtime.callback_bindings import (
    extract_callback_binding,
    validate_attempt_execution_binding,
)
from app.runtime.control import (
    abort_attempt,
    end_node_session,
    ensure_flow_not_terminal,
    expire_pending_approvals,
    latest_attempt,
    lock_flow,
    supersede_projected_manifests,
)
from app.runtime.packaging import ensure_task_compose_for_compiled_plan
from app.runtime.resources import ensure_task_resources_for_compiled_plan
from app.runtime.runner import _materialize_flow_graph
from app.runtime.state import set_flow_status, utcnow_naive
from app.schemas.compiler import ResolvedWorkflowDefinition
from app.schemas.registry import (
    SkillReferenceSeed,
    WorkflowDefinitionSeed,
    WorkflowEdgeSeed,
    WorkflowNodeResourcesSeed,
    WorkflowNodeSeed,
)
from app.schemas.runtime import NodePlanPatchPayload, NodePlanRevisionCreate


async def list_flow_replans(session: AsyncSession, flow_id: UUID) -> list[NodePlanRevision]:
    flow_exists = await session.scalar(select(Flow.id).where(Flow.id == flow_id))
    if flow_exists is None:
        raise NotFoundError(f"No flow found: {flow_id}")

    result = await session.scalars(
        select(NodePlanRevision)
        .where(NodePlanRevision.flow_id == flow_id)
        .order_by(NodePlanRevision.created_at.asc())
    )
    return list(result.all())


def _binding_value(binding: object, key: str) -> object:
    if isinstance(binding, dict):
        return binding.get(key)
    return getattr(binding, key, None)


def _skill_ref_from_binding(binding: object) -> SkillReferenceSeed:
    provider = _binding_value(binding, "provider")
    key = _binding_value(binding, "key")
    if not isinstance(provider, str) or not isinstance(key, str):
        raise InvalidDefinitionError("Replan skill binding is missing provider/key")

    manifest_summary = _binding_value(binding, "manifest_summary")
    manifest_runtime_name = None
    if isinstance(manifest_summary, dict):
        manifest_runtime_name = manifest_summary.get("runtime_name")

    return SkillReferenceSeed.model_validate(
        {
            "provider": provider,
            "key": key,
            "runtime_name": _binding_value(binding, "runtime_name") or manifest_runtime_name,
            "version": (
                _binding_value(binding, "version_label")
                or _binding_value(binding, "version")
            ),
            "state": _binding_value(binding, "state"),
            "source_uri": _binding_value(binding, "source_ref"),
        }
    )


def _patch_skill_refs(patch: NodePlanPatchPayload) -> list[SkillReferenceSeed]:
    converted_bindings = [
        _skill_ref_from_binding(binding)
        for binding in cast(list[dict[str, object]], patch.skill_bindings)
    ]
    return merge_skill_refs(patch.skill_refs, converted_bindings)


def _base_node_resources(
    base_workflow: WorkflowDefinitionSeed,
    *,
    node_id: str,
) -> WorkflowNodeResourcesSeed:
    base_node = next((node for node in base_workflow.nodes if node.id == node_id), None)
    if base_node is None:
        return WorkflowNodeResourcesSeed()
    return base_node.resources


def _build_replan_workflow_seed(
    compiled_plan: CompiledPlan,
    patch: NodePlanPatchPayload,
) -> WorkflowDefinitionSeed:
    source_workflow = compiled_plan.source_snapshot.get("workflow")
    if not isinstance(source_workflow, dict):
        raise InvalidDefinitionError("Compiled plan is missing source workflow snapshot")

    base_workflow = WorkflowDefinitionSeed.model_validate(source_workflow)
    return WorkflowDefinitionSeed(
        id=base_workflow.id,
        description=patch.description or base_workflow.description,
        policy=patch.policy if patch.policy is not None else base_workflow.policy,
        defaults=merge_workflow_defaults(base_workflow.defaults, patch.defaults),
        task_defaults=merge_task_defaults(base_workflow.task_defaults, patch.task_defaults),
        nodes=[
            WorkflowNodeSeed(
                id=node.id,
                role=node.role,
                mode=node.mode,
                policy=node.policy,
                description=node.description,
                metadata=node.metadata,
                resources=merge_node_resources(
                    _base_node_resources(base_workflow, node_id=node.id),
                    node.resources,
                ),
                skill_refs=node.skill_refs,
            )
            for node in patch.nodes
        ],
        edges=[
            WorkflowEdgeSeed(
                **{
                    "from": edge.from_node,
                    "to": edge.to_node,
                    "when": edge.when,
                    "kind": edge.kind,
                }
            )
            for edge in patch.edges
        ],
        skill_refs=merge_skill_refs(base_workflow.skill_refs, _patch_skill_refs(patch)),
    )


async def _resolve_patch_payload(
    session: AsyncSession,
    *,
    flow_revision: FlowRevision,
    patch: NodePlanPatchPayload,
) -> ResolvedWorkflowDefinition:
    compiled_plan = flow_revision.compiled_plan
    workflow_seed = _build_replan_workflow_seed(compiled_plan, patch)
    return await resolve_workflow_seed_content(
        session,
        workflow_seed,
        workflow_version_id=compiled_plan.workflow_version_id,
        source_snapshot={
            "replan": patch.model_dump(mode="json", by_alias=True),
            "base_flow_revision_id": str(flow_revision.id),
            "base_compiled_plan_id": str(compiled_plan.id),
        },
    )


def _patch_changes_launch_binding(patch: NodePlanPatchPayload) -> bool:
    return any(
        [
            bool(patch.task_defaults),
            bool(patch.defaults),
            bool(patch.skill_refs),
            bool(patch.skill_bindings),
            any(bool(node.resources) for node in patch.nodes),
        ]
    )


def _replan_requires_new_task_compose(patch: NodePlanPatchPayload) -> bool:
    return _patch_changes_launch_binding(patch)


async def request_replan(
    session: AsyncSession,
    *,
    flow_id: UUID,
    payload: NodePlanRevisionCreate,
) -> NodePlanRevision:
    await lock_flow(session, flow_id)
    flow = cast(
        Flow | None,
        await session.scalar(
            select(Flow)
            .options(
                selectinload(Flow.task),
                selectinload(Flow.flow_revisions)
                .selectinload(FlowRevision.compiled_plan)
                .selectinload(CompiledPlan.nodes),
                selectinload(Flow.flow_revisions)
                .selectinload(FlowRevision.nodes)
                .selectinload(FlowNode.attempts)
                .selectinload(NodeAttempt.checkpoints),
                selectinload(Flow.flow_revisions)
                .selectinload(FlowRevision.nodes)
                .selectinload(FlowNode.attempts)
                .selectinload(NodeAttempt.context_manifests),
                selectinload(Flow.flow_revisions)
                .selectinload(FlowRevision.nodes)
                .selectinload(FlowNode.node_session),
                selectinload(Flow.approvals),
                selectinload(Flow.context_manifests),
                selectinload(Flow.node_plan_revisions),
            )
            .where(Flow.id == flow_id)
        ),
    )
    if flow is None:
        raise NotFoundError(f"No flow found: {flow_id}")
    ensure_flow_not_terminal(flow)
    if flow.active_flow_revision is None:
        raise ConflictError("Flow has no active revision")

    active_revision = flow.active_flow_revision
    requesting_node = next(
        (node for node in active_revision.nodes if node.id == payload.requesting_flow_node_id),
        None,
    )
    if requesting_node is None:
        raise NotFoundError(f"No requesting flow node found: {payload.requesting_flow_node_id}")

    requesting_attempt = next(
        (
            attempt
            for attempt in requesting_node.attempts
            if attempt.id == payload.requesting_node_attempt_id
        ),
        None,
    )
    if requesting_attempt is None:
        raise NotFoundError(
            f"No requesting node attempt found: {payload.requesting_node_attempt_id}"
        )
    callback_binding = extract_callback_binding(
        payload,
        required=False,
        operation="Replan callback",
    )
    has_internal_binding = callback_binding is not None

    validate_attempt_execution_binding(
        flow,
        requesting_node,
        requesting_attempt,
        callback_binding=callback_binding,
        allowed_attempt_statuses=(
            {
                NodeAttemptStatus.RUNNING,
                NodeAttemptStatus.BLOCKED,
                NodeAttemptStatus.FAILED,
                NodeAttemptStatus.SUCCEEDED,
            }
            if has_internal_binding
            else {
                NodeAttemptStatus.BLOCKED,
                NodeAttemptStatus.FAILED,
                NodeAttemptStatus.SUCCEEDED,
            }
        ),
    )

    base_revision_id = active_revision.id
    existing_candidate_count = await session.scalar(
        select(func.count(NodePlanRevision.id)).where(
            NodePlanRevision.flow_id == flow_id,
            NodePlanRevision.base_flow_revision_id == base_revision_id,
            NodePlanRevision.status.in_(
                [NodePlanRevisionStatus.PROPOSED, NodePlanRevisionStatus.VALIDATING]
            ),
        )
    )
    if existing_candidate_count:
        raise ConflictError("Flow already has a pending replan candidate")

    proposal = NodePlanRevision(
        flow_id=flow.id,
        requesting_flow_node_id=requesting_node.id,
        requesting_node_attempt_id=requesting_attempt.id,
        base_flow_revision_id=base_revision_id,
        patch_payload=payload.patch.model_dump(mode="json", by_alias=True),
        reason=payload.reason,
        status=NodePlanRevisionStatus.VALIDATING,
    )
    flow.node_plan_revisions.append(proposal)
    await session.flush()

    try:
        resolved_workflow = await _resolve_patch_payload(
            session,
            flow_revision=active_revision,
            patch=payload.patch,
        )
        validate_resolved_workflow(resolved_workflow)
        normalized = normalize_resolved_workflow(resolved_workflow)
        plan_hash = compute_plan_hash(normalized)
        compiled_plan = await persist_compiled_plan(
            session,
            normalized,
            plan_hash,
        )

        await ensure_task_resources_for_compiled_plan(
            session,
            task=flow.task,
            compiled_plan=compiled_plan,
            allow_create=False,
        )

        candidate_revision = FlowRevision(
            flow_id=flow.id,
            revision_no=active_revision.revision_no + 1,
            compiled_plan_id=compiled_plan.id,
            parent_flow_revision_id=active_revision.id,
            status=FlowRevisionStatus.CANDIDATE,
            reason=payload.reason,
            source_patch_payload=payload.patch.model_dump(mode="json", by_alias=True),
        )
        flow.flow_revisions.append(candidate_revision)
        await session.flush()

        await _materialize_flow_graph(
            session,
            flow=flow,
            flow_revision=candidate_revision,
            compiled_plan=compiled_plan,
        )
        proposal.candidate_flow_revision_id = candidate_revision.id
        proposal.validated_at = utcnow_naive()
        proposal.status = NodePlanRevisionStatus.VALIDATED
        await session.flush()

        for base_node in active_revision.nodes:
            current_attempt = latest_attempt(base_node)
            if current_attempt is None:
                continue
            if current_attempt.status in {
                NodeAttemptStatus.RUNNING,
                NodeAttemptStatus.BLOCKED,
                NodeAttemptStatus.PENDING,
            }:
                abort_attempt(current_attempt)
                end_node_session(base_node.node_session)

        expire_pending_approvals(flow, reason="superseded-by-replan")
        supersede_projected_manifests(flow)

        active_revision.status = FlowRevisionStatus.RETIRED
        candidate_revision.status = FlowRevisionStatus.ACTIVE
        candidate_revision.adopted_from_node_plan_revision_id = proposal.id
        candidate_revision.adopted_at = utcnow_naive()
        flow.active_flow_revision_id = candidate_revision.id
        flow.active_flow_revision = candidate_revision

        proposal.status = NodePlanRevisionStatus.ADOPTED
        proposal.adopted_at = utcnow_naive()
        remint_task_compose = _replan_requires_new_task_compose(payload.patch)
        set_flow_status(flow, FlowStatus.PENDING)
        if remint_task_compose:
            current_task_compose = await session.scalar(
                select(TaskCompose).where(TaskCompose.task_id == flow.task_id)
            )
            if current_task_compose is not None:
                current_task_compose.superseded_at = utcnow_naive()
            await ensure_task_compose_for_compiled_plan(
                session,
                task=flow.task,
                compiled_plan=compiled_plan,
            )
        await session.flush()
        return proposal
    except Exception as exc:
        proposal.status = NodePlanRevisionStatus.REJECTED
        proposal.error_text = str(exc)
        await session.flush()
        raise
