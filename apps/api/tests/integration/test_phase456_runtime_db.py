from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import CheckpointStatus, NodePlanRevisionStatus, WaitReason, WorkflowMode
from app.db.models.runtime import CompiledPlan, Flow, FlowNode, FlowRevision, NodeAttempt
from app.runtime.checkpoints import record_checkpoint
from app.runtime.dispatcher import acknowledge_context_manifest
from app.runtime.replan import request_replan
from app.runtime.runner import continue_flow, get_flow_with_relations, start_flow_from_workflow
from app.runtime.watchdog import run_flow_watchdog
from app.schemas.registry import WorkflowDefaultsSeed
from app.schemas.runtime import (
    CheckpointWrite,
    FlowStartFromWorkflowCreate,
    NodePlanPatchEdge,
    NodePlanPatchNode,
    NodePlanPatchPayload,
    NodePlanRevisionCreate,
    TaskCreate,
)
from app.services.registry_service import bootstrap_registry


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _bootstrap(db_session: AsyncSession) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()


async def _start_flow(db_session: AsyncSession, workflow_key: str) -> UUID:
    flow, _revision, _flow_nodes = await start_flow_from_workflow(
        db_session,
        workflow_key=workflow_key,
        payload=FlowStartFromWorkflowCreate(
            task=TaskCreate(
                title=f"{workflow_key} flow",
                description="phase loop test",
                input_payload={"source": workflow_key},
            )
        ),
    )
    await db_session.flush()
    return flow.id


async def _start_node_execution(
    db_session: AsyncSession,
    flow_id: UUID,
    expected_node_key: str,
) -> tuple[Flow, FlowNode, NodeAttempt]:
    flow = await continue_flow(db_session, flow_id)
    assert flow.active_flow_revision is not None
    projected = next(
        manifest for manifest in flow.context_manifests if manifest.status.value == "projected"
    )
    flow_node = next(
        node for node in flow.active_flow_revision.nodes if node.id == projected.flow_node_id
    )
    assert flow_node.node_key == expected_node_key

    await acknowledge_context_manifest(db_session, projected.id)
    flow = await continue_flow(db_session, flow_id)
    assert flow.active_flow_revision is not None
    active_node = next(
        node for node in flow.active_flow_revision.nodes if node.id == projected.flow_node_id
    )
    attempt = active_node.attempts[-1]
    return flow, active_node, attempt


async def _green_current_node(
    db_session: AsyncSession,
    flow_id: UUID,
    expected_node_key: str,
) -> None:
    flow, flow_node, attempt = await _start_node_execution(db_session, flow_id, expected_node_key)
    await record_checkpoint(
        db_session,
        CheckpointWrite(
            flow_id=flow.id,
            flow_node_id=flow_node.id,
            node_attempt_id=attempt.id,
            sequence_no=1,
            status=CheckpointStatus.GREEN,
            summary=f"{expected_node_key} done",
            payload={"node": expected_node_key},
        ),
    )
    await db_session.flush()


async def test_watchdog_blocks_stalled_running_attempt_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    await _bootstrap(db_session)
    flow_id = await _start_flow(db_session, "default-bugfix")

    flow, flow_node, attempt = await _start_node_execution(db_session, flow_id, "root")
    attempt.started_at = _utcnow_naive() - timedelta(minutes=10)
    await db_session.flush()

    watched_flow, stalled_attempt_ids, checkpoints = await run_flow_watchdog(
        db_session,
        flow_id=flow.id,
        stale_after_seconds=60,
    )
    await db_session.commit()

    assert stalled_attempt_ids == [attempt.id]
    assert checkpoints[0].wait_reason == WaitReason.WATCHDOG
    assert watched_flow.status.value == "blocked"

    refreshed = await get_flow_with_relations(db_session, flow.id)
    assert refreshed is not None
    assert refreshed.active_flow_revision is not None
    refreshed_node = next(
        node for node in refreshed.active_flow_revision.nodes if node.id == flow_node.id
    )
    assert refreshed_node.state.value == "waiting"
    assert refreshed_node.attempts[-1].status.value == "blocked"


async def test_replan_adopts_new_revision_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    await _bootstrap(db_session)
    flow_id = await _start_flow(db_session, "default-bugfix")
    await _green_current_node(db_session, flow_id, "root")
    flow = await get_flow_with_relations(db_session, flow_id)
    assert flow is not None
    assert flow.active_flow_revision is not None
    root_node = next(node for node in flow.active_flow_revision.nodes if node.node_key == "root")
    root_attempt = root_node.attempts[-1]

    proposal = await request_replan(
        db_session,
        flow_id=flow.id,
        payload=NodePlanRevisionCreate(
            requesting_flow_node_id=root_node.id,
            requesting_node_attempt_id=root_attempt.id,
            reason="expand to hierarchy-safe review graph",
            patch=NodePlanPatchPayload(
                nodes=[
                    NodePlanPatchNode(
                        id="root",
                        role="planner-supervisor",
                        mode=WorkflowMode.PLAN,
                    ),
                    NodePlanPatchNode(
                        id="root.discovery",
                        role="main-loop-worker",
                        mode=WorkflowMode.PERSISTENT_EXECUTE,
                    ),
                    NodePlanPatchNode(
                        id="root.review",
                        role="reviewer",
                        mode=WorkflowMode.REVIEW,
                    ),
                    NodePlanPatchNode(
                        id="root.sync",
                        role="syncer",
                        mode=WorkflowMode.SYNC,
                    ),
                ],
                edges=[
                    NodePlanPatchEdge.model_validate({"from": "root", "to": "root.discovery"}),
                    NodePlanPatchEdge.model_validate(
                        {"from": "root.discovery", "to": "root.review"}
                    ),
                    NodePlanPatchEdge.model_validate({"from": "root.review", "to": "root.sync"}),
                ],
            ),
        ),
    )
    await db_session.commit()

    assert proposal.status == NodePlanRevisionStatus.ADOPTED
    assert proposal.candidate_flow_revision_id is not None

    refreshed = await get_flow_with_relations(db_session, flow.id)
    assert refreshed is not None
    assert refreshed.active_flow_revision is not None
    assert refreshed.active_flow_revision.revision_no == 2
    assert refreshed.status.value == "pending"


async def test_hierarchy_join_scheduling_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    await _bootstrap(db_session)
    flow_id = await _start_flow(db_session, "max-complexity-review")

    await _green_current_node(db_session, flow_id, "root")
    await _green_current_node(db_session, flow_id, "root.discovery")
    await _green_current_node(db_session, flow_id, "root.product")
    await _green_current_node(db_session, flow_id, "root.implementation_loop")
    await _green_current_node(db_session, flow_id, "root.implementation_loop.cycle")

    flow = await continue_flow(db_session, flow_id)
    assert flow.active_flow_revision is not None
    projected = next(
        manifest for manifest in flow.context_manifests if manifest.status.value == "projected"
    )
    review_node = next(
        node for node in flow.active_flow_revision.nodes if node.id == projected.flow_node_id
    )

    assert review_node.node_key == "root.review_and_governance"

    required_items = projected.manifest_payload["required_items"]
    checkpoint_items = [
        item
        for item in required_items
        if str(item.get("storage_uri", "")).startswith("checkpoint://")
    ]
    checkpoint_titles = {item["title"] for item in checkpoint_items}
    assert "checkpoint-summary:root.discovery" in checkpoint_titles
    assert "checkpoint-summary:root.product" in checkpoint_titles
    assert "checkpoint-summary:root.implementation_loop.cycle" in checkpoint_titles

    discovery_item = next(
        item for item in checkpoint_items if item["title"] == "checkpoint-summary:root.discovery"
    )
    assert discovery_item["inline_content"]["flow_node_key"] == "root.discovery"
    assert discovery_item["inline_content"]["flow_node_path"].endswith("root.discovery")
    assert discovery_item["inline_content"]["status"] == "green"
    assert discovery_item["inline_content"]["summary"] == "root.discovery done"
    assert discovery_item["inline_content"]["payload"] == {"node": "root.discovery"}

    await db_session.commit()


async def test_replan_inherits_existing_skill_bindings_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    await _bootstrap(db_session)
    flow_id = await _start_flow(db_session, "default-bugfix")
    await _green_current_node(db_session, flow_id, "root")
    flow = await get_flow_with_relations(db_session, flow_id)
    assert flow is not None
    assert flow.active_flow_revision is not None
    root_node = next(node for node in flow.active_flow_revision.nodes if node.node_key == "root")
    root_attempt = root_node.attempts[-1]

    base_revision = await db_session.scalar(
        select(FlowRevision)
        .options(selectinload(FlowRevision.compiled_plan).selectinload(CompiledPlan.nodes))
        .where(FlowRevision.id == flow.active_flow_revision_id)
    )
    assert base_revision is not None
    base_skill_bindings = base_revision.compiled_plan.nodes[0].skill_bindings
    assert base_skill_bindings

    proposal = await request_replan(
        db_session,
        flow_id=flow.id,
        payload=NodePlanRevisionCreate(
            requesting_flow_node_id=root_node.id,
            requesting_node_attempt_id=root_attempt.id,
            reason="preserve inherited workflow skill bindings",
            patch=NodePlanPatchPayload(
                nodes=[
                    NodePlanPatchNode(id="root", role="planner-supervisor", mode=WorkflowMode.PLAN),
                    NodePlanPatchNode(
                        id="root.discovery",
                        role="main-loop-worker",
                        mode=WorkflowMode.PERSISTENT_EXECUTE,
                    ),
                ],
                edges=[NodePlanPatchEdge.model_validate({"from": "root", "to": "root.discovery"})],
            ),
        ),
    )
    await db_session.flush()

    assert proposal.candidate_flow_revision_id is not None
    candidate_revision = await db_session.scalar(
        select(FlowRevision)
        .options(selectinload(FlowRevision.compiled_plan).selectinload(CompiledPlan.nodes))
        .where(FlowRevision.id == proposal.candidate_flow_revision_id)
    )
    assert candidate_revision is not None
    assert candidate_revision.compiled_plan.nodes
    assert candidate_revision.compiled_plan.nodes[0].skill_bindings == base_skill_bindings


async def test_replan_uses_effective_node_merge_contract_for_metadata_description_and_skills(
    db_session: AsyncSession,
) -> None:
    await _bootstrap(db_session)
    flow_id = await _start_flow(db_session, "default-bugfix")
    await _green_current_node(db_session, flow_id, "root")
    flow = await get_flow_with_relations(db_session, flow_id)
    assert flow is not None
    assert flow.active_flow_revision is not None
    root_node = next(node for node in flow.active_flow_revision.nodes if node.node_key == "root")
    root_attempt = root_node.attempts[-1]

    base_revision = await db_session.scalar(
        select(FlowRevision)
        .options(selectinload(FlowRevision.compiled_plan).selectinload(CompiledPlan.nodes))
        .where(FlowRevision.id == flow.active_flow_revision_id)
    )
    assert base_revision is not None
    base_skill_binding = dict(base_revision.compiled_plan.nodes[0].skill_bindings[0])
    base_skill_binding["state"] = "required"

    proposal = await request_replan(
        db_session,
        flow_id=flow.id,
        payload=NodePlanRevisionCreate(
            requesting_flow_node_id=root_node.id,
            requesting_node_attempt_id=root_attempt.id,
            reason="align replan with effective node merge semantics",
            patch=NodePlanPatchPayload(
                description="Replanned default bugfix",
                defaults=WorkflowDefaultsSeed(metadata={"operator_goal": "trim-loop"}),
                skill_bindings=[base_skill_binding],
                nodes=[
                    NodePlanPatchNode(
                        id="root",
                        role="planner-supervisor",
                        mode=WorkflowMode.PLAN,
                        description="Replanned root",
                        metadata={"node_flag": True},
                    ),
                    NodePlanPatchNode(
                        id="root.discovery",
                        role="main-loop-worker",
                        mode=WorkflowMode.PERSISTENT_EXECUTE,
                        metadata={"lane": "discovery"},
                    ),
                ],
                edges=[NodePlanPatchEdge.model_validate({"from": "root", "to": "root.discovery"})],
            ),
        ),
    )
    await db_session.flush()

    assert proposal.candidate_flow_revision_id is not None
    candidate_revision = await db_session.scalar(
        select(FlowRevision)
        .options(selectinload(FlowRevision.compiled_plan).selectinload(CompiledPlan.nodes))
        .where(FlowRevision.id == proposal.candidate_flow_revision_id)
    )
    assert candidate_revision is not None

    root_payload = candidate_revision.compiled_plan.nodes[0].effective_payload
    discovery_payload = candidate_revision.compiled_plan.nodes[1].effective_payload

    assert root_payload["description"] == "Replanned root"
    assert root_payload["metadata"] == {
        "replan_style": "balanced",
        "prefers_local_retry_first": True,
        "operator_goal": "trim-loop",
        "node_flag": True,
    }
    assert root_payload["provenance"]["description"]["layer"] == "node"
    assert root_payload["provenance"]["metadata"]["replan_style"]["layer"] == "role"
    assert root_payload["provenance"]["metadata"]["operator_goal"]["layer"] == "workflow"
    assert root_payload["skill_bindings"][0]["state"] == "required"
    assert discovery_payload["metadata"]["operator_goal"] == "trim-loop"
    assert discovery_payload["metadata"]["lane"] == "discovery"


async def test_max_complexity_workflow_runs_to_completion_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    await _bootstrap(db_session)
    flow_id = await _start_flow(db_session, "max-complexity-review")

    for node_key in [
        "root",
        "root.discovery",
        "root.product",
        "root.implementation_loop",
        "root.implementation_loop.cycle",
        "root.review_and_governance",
        "root.review_and_governance.security",
        "root.sync",
    ]:
        await _green_current_node(db_session, flow_id, node_key)

    flow = await get_flow_with_relations(db_session, flow_id)
    assert flow is not None
    assert flow.active_flow_revision is not None
    assert flow.status.value == "succeeded"
    assert all(node.state.value == "done" for node in flow.active_flow_revision.nodes)
    await db_session.commit()
