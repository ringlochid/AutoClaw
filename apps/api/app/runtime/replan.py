from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.compiler.lower import persist_compiled_plan
from app.compiler.normalize import normalize_resolved_workflow
from app.compiler.parse import parse_policy_content, parse_role_content
from app.compiler.plan_hash import compute_plan_hash
from app.compiler.validate import validate_resolved_workflow
from app.core.enums import (
    FlowRevisionStatus,
    FlowStatus,
    NodeAttemptStatus,
    NodePlanRevisionStatus,
)
from app.core.errors import ConflictError, InvalidDefinitionError, NotFoundError
from app.db.models.runtime import (
    CompiledPlan,
    Flow,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodePlanRevision,
)
from app.runtime.control import (
    abort_attempt,
    end_node_session,
    ensure_current_attempt,
    ensure_flow_not_terminal,
    expire_pending_approvals,
    latest_attempt,
    lock_flow,
    supersede_projected_manifests,
)
from app.runtime.runner import _materialize_flow_graph
from app.runtime.state import set_flow_status, utcnow_naive
from app.schemas.compiler import (
    ResolvedSkillBinding,
    ResolvedWorkflowDefinition,
    ResolvedWorkflowEdge,
    ResolvedWorkflowNode,
)
from app.schemas.runtime import NodePlanPatchPayload, NodePlanRevisionCreate
from app.services.registry_service import get_published_policy_version, get_published_role_version


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


def _inherited_skill_bindings(
    flow_revision: FlowRevision,
    patch: NodePlanPatchPayload,
) -> list[dict[str, object]]:
    if patch.skill_bindings:
        return cast(list[dict[str, object]], patch.skill_bindings)

    compiled_plan = flow_revision.compiled_plan
    if compiled_plan.nodes and compiled_plan.nodes[0].skill_bindings:
        return cast(list[dict[str, object]], compiled_plan.nodes[0].skill_bindings)

    resolved_snapshot = compiled_plan.source_snapshot.get("resolved")
    if isinstance(resolved_snapshot, dict):
        skill_bindings = resolved_snapshot.get("skill_bindings")
        if isinstance(skill_bindings, list):
            return cast(list[dict[str, object]], skill_bindings)

    return []


async def _resolve_patch_payload(
    session: AsyncSession,
    *,
    flow_revision: FlowRevision,
    patch: NodePlanPatchPayload,
) -> ResolvedWorkflowDefinition:
    compiled_plan = flow_revision.compiled_plan
    inherited_skill_bindings = _inherited_skill_bindings(flow_revision, patch)

    resolved_nodes: list[ResolvedWorkflowNode] = []
    for node in patch.nodes:
        role_version = await get_published_role_version(session, node.role)
        role_seed = parse_role_content(role_version.content)

        effective_policy_key = node.policy or role_seed.default_policy
        if effective_policy_key is None:
            raise InvalidDefinitionError(f"No policy could be resolved for node '{node.id}'")

        policy_version = await get_published_policy_version(session, effective_policy_key)
        parse_policy_content(policy_version.content)

        resolved_nodes.append(
            ResolvedWorkflowNode(
                node_key=node.id,
                role_key=node.role,
                role_version_id=role_version.id,
                policy_key=effective_policy_key,
                policy_version_id=policy_version.id,
                mode=node.mode,
                allowed_modes=role_seed.allowed_modes,
                metadata=node.metadata,
            )
        )

    resolved_edges = [
        ResolvedWorkflowEdge(
            from_node=edge.from_node,
            to_node=edge.to_node,
            condition_expr=edge.when,
            edge_kind=edge.kind,
        )
        for edge in patch.edges
    ]

    return ResolvedWorkflowDefinition(
        workflow_key=cast(str, compiled_plan.source_snapshot.get("workflow_key", "runtime-replan")),
        workflow_version_id=compiled_plan.workflow_version_id,
        description="runtime replan",
        workflow_policy_key=None,
        nodes=resolved_nodes,
        edges=resolved_edges,
        skill_bindings=[
            ResolvedSkillBinding.model_validate(binding) for binding in inherited_skill_bindings
        ],
        source_snapshot={
            "replan": patch.model_dump(mode="json", by_alias=True),
            "base_flow_revision_id": str(flow_revision.id),
        },
    )


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
    ensure_current_attempt(
        flow,
        requesting_node,
        requesting_attempt,
        allowed_statuses={
            NodeAttemptStatus.BLOCKED,
            NodeAttemptStatus.FAILED,
            NodeAttemptStatus.SUCCEEDED,
        },
    )

    proposal = NodePlanRevision(
        flow_id=flow.id,
        requesting_flow_node_id=requesting_node.id,
        requesting_node_attempt_id=payload.requesting_node_attempt_id,
        base_flow_revision_id=active_revision.id,
        patch_payload=payload.patch.model_dump(mode="json", by_alias=True),
        reason=payload.reason,
        status=NodePlanRevisionStatus.PROPOSED,
    )
    session.add(proposal)
    await session.flush()

    try:
        proposal.status = NodePlanRevisionStatus.VALIDATING
        resolved_workflow = await _resolve_patch_payload(
            session,
            flow_revision=active_revision,
            patch=payload.patch,
        )
        validate_resolved_workflow(resolved_workflow)
        normalized_plan = normalize_resolved_workflow(resolved_workflow)
        plan_hash = compute_plan_hash(normalized_plan)
        compiled_plan = await persist_compiled_plan(session, normalized_plan, plan_hash)

        next_revision_no_value = await session.scalar(
            select(func.coalesce(func.max(FlowRevision.revision_no), 0) + 1).where(
                FlowRevision.flow_id == flow.id
            )
        )
        next_revision_no = int(next_revision_no_value or 1)
        candidate_revision = FlowRevision(
            flow_id=flow.id,
            revision_no=next_revision_no,
            compiled_plan_id=compiled_plan.id,
            parent_flow_revision_id=active_revision.id,
            status=FlowRevisionStatus.CANDIDATE,
            reason=payload.reason,
            source_patch_payload=payload.patch.model_dump(mode="json", by_alias=True),
        )
        session.add(candidate_revision)
        await session.flush()

        candidate_nodes = await _materialize_flow_graph(
            session,
            flow=flow,
            flow_revision=candidate_revision,
            compiled_plan=compiled_plan,
        )
        base_nodes_by_key = {node.node_key: node for node in active_revision.nodes}
        for candidate_node in candidate_nodes:
            base_node = base_nodes_by_key.get(candidate_node.node_key)
            if base_node is not None and base_node.state.value == "done":
                candidate_node.state = base_node.state

        proposal.status = NodePlanRevisionStatus.VALIDATED
        proposal.validated_at = utcnow_naive()
        proposal.candidate_flow_revision_id = candidate_revision.id

        for base_node in active_revision.nodes:
            current_attempt = latest_attempt(base_node)
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
        set_flow_status(flow, FlowStatus.PENDING)
        await session.flush()
        return proposal
    except Exception as exc:
        proposal.status = NodePlanRevisionStatus.REJECTED
        proposal.error_text = str(exc)
        await session.flush()
        raise
