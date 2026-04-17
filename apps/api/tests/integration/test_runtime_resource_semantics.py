from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import DefinitionVersionStatus, TaskResourceBindingRole, WorkflowMode
from app.core.errors import InvalidDefinitionError
from app.db.models.registry import WorkflowDefinition, WorkflowVersion
from app.db.models.runtime import CompiledPlan, FlowRevision, Task, TaskResourceBinding
from app.runtime.replan import request_replan
from app.runtime.runner import continue_flow, get_flow_with_relations, start_flow_from_workflow
from app.schemas.runtime import (
    FlowStartFromWorkflowCreate,
    NodePlanPatchEdge,
    NodePlanPatchNode,
    NodePlanPatchPayload,
    NodePlanRevisionCreate,
    TaskCreate,
)
from app.services.registry_service import bootstrap_registry


async def _insert_workflow_version(
    db_session: AsyncSession,
    *,
    key: str,
    content: dict,
) -> None:
    definition = WorkflowDefinition(key=key, description=content.get("description"))
    db_session.add(definition)
    await db_session.flush()

    db_session.add(
        WorkflowVersion(
            workflow_definition_id=definition.id,
            version=1,
            status=DefinitionVersionStatus.PUBLISHED,
            description=content.get("description"),
            content=content,
            published_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    await db_session.commit()


def _resourceful_workflow_content(*, missing_task_defaults: bool = False) -> dict:
    workflow = {
        "id": "resourceful-workflow",
        "description": "workflow with explicit task resources",
        "nodes": [
            {
                "id": "root",
                "role": "planner-supervisor",
                "mode": "plan",
                "resources": {
                    "workspace": {
                        "mounts": [{"ref": "task.primary_workspace", "access": "read_only"}]
                    },
                    "context": {"refs": [{"ref": "task.primary_context"}]},
                },
            },
            {
                "id": "loop",
                "role": "main-loop-worker",
                "mode": "persistent_execute",
                "resources": {
                    "workspace": {
                        "mounts": [{"ref": "task.primary_workspace", "access": "read_write"}]
                    },
                    "context": {"refs": [{"ref": "task.primary_context"}]},
                },
            },
        ],
        "edges": [{"from": "root", "to": "loop"}],
    }
    if not missing_task_defaults:
        workflow["task_defaults"] = {
            "workspace": {"mode": "ensure_task_primary"},
            "context": {
                "mode": "ensure_task_primary",
                "seed_from": ["task_input", "workspace_docs"],
            },
            "manifests": {"mode": "ensure_task_root"},
        }
    return workflow


async def test_start_flow_materializes_task_resources_and_projects_manifest_bindings(
    db_session: AsyncSession,
) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()
    await _insert_workflow_version(
        db_session,
        key="resourceful-workflow",
        content=_resourceful_workflow_content(),
    )

    flow, _revision, _flow_nodes = await start_flow_from_workflow(
        db_session,
        workflow_key="resourceful-workflow",
        payload=FlowStartFromWorkflowCreate(
            task=TaskCreate(
                title="resource bootstrap",
                description="runtime resource bootstrap",
                input_payload={"ticket": "A-1"},
            )
        ),
    )
    await db_session.commit()

    task = await db_session.scalar(
        select(Task)
        .options(
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.workspace_root),
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.context_space),
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.manifest_root),
        )
        .where(Task.id == flow.task_id)
    )
    assert task is not None

    roles = {binding.binding_role for binding in task.resource_bindings}
    assert roles == {
        TaskResourceBindingRole.PRIMARY_WORKSPACE,
        TaskResourceBindingRole.PRIMARY_CONTEXT,
        TaskResourceBindingRole.MANIFEST_ROOT,
    }

    workspace_binding = next(
        binding
        for binding in task.resource_bindings
        if binding.binding_role == TaskResourceBindingRole.PRIMARY_WORKSPACE
    )
    context_binding = next(
        binding
        for binding in task.resource_bindings
        if binding.binding_role == TaskResourceBindingRole.PRIMARY_CONTEXT
    )
    manifest_binding = next(
        binding
        for binding in task.resource_bindings
        if binding.binding_role == TaskResourceBindingRole.MANIFEST_ROOT
    )

    assert workspace_binding.workspace_root is not None
    assert workspace_binding.workspace_root.key == f"task.{task.id}.workspace"
    assert context_binding.context_space is not None
    assert context_binding.context_space.key == f"task.{task.id}.context"
    assert manifest_binding.manifest_root is not None
    assert manifest_binding.manifest_root.storage_uri == f"task://{task.id}/manifests"

    await continue_flow(db_session, flow.id)
    refreshed_flow = await get_flow_with_relations(db_session, flow.id)
    assert refreshed_flow is not None

    projected_manifest = next(
        manifest
        for manifest in refreshed_flow.context_manifests
        if manifest.status.value == "projected"
    )
    assert projected_manifest.manifest_root_id == manifest_binding.manifest_root_id
    assert projected_manifest.manifest_payload["task_defaults"]["context"]["seed_from"] == [
        "task_input",
        "workspace_docs",
    ]

    resource_mount = projected_manifest.manifest_payload["resources"]["workspace"]["mounts"][0]
    assert resource_mount["ref"] == "task.primary_workspace"
    assert resource_mount["access"] == "read_only"
    assert resource_mount["key"] == f"task.{task.id}.workspace"

    required_items = projected_manifest.manifest_payload["required_items"]
    task_input = next(item for item in required_items if item["title"] == "task-input")
    assert task_input["inline_content"] == {"ticket": "A-1"}


async def test_start_flow_rejects_unbound_task_resource_refs(
    db_session: AsyncSession,
) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()
    await _insert_workflow_version(
        db_session,
        key="resourceful-workflow",
        content=_resourceful_workflow_content(missing_task_defaults=True),
    )

    with pytest.raises(InvalidDefinitionError) as exc_info:
        await start_flow_from_workflow(
            db_session,
            workflow_key="resourceful-workflow",
            payload=FlowStartFromWorkflowCreate(
                task=TaskCreate(
                    title="missing bindings",
                    description="missing runtime bindings",
                    input_payload={},
                )
            ),
        )

    assert "task.primary_workspace" in str(exc_info.value)


async def test_replan_preserves_task_resource_semantics_from_base_workflow(
    db_session: AsyncSession,
) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()
    await _insert_workflow_version(
        db_session,
        key="resourceful-workflow",
        content=_resourceful_workflow_content(),
    )

    flow, _revision, _flow_nodes = await start_flow_from_workflow(
        db_session,
        workflow_key="resourceful-workflow",
        payload=FlowStartFromWorkflowCreate(
            task=TaskCreate(
                title="resource replan",
                description="resource replan",
                input_payload={"ticket": "A-2"},
            )
        ),
    )
    await continue_flow(db_session, flow.id)

    refreshed_flow = await get_flow_with_relations(db_session, flow.id)
    assert refreshed_flow is not None
    assert refreshed_flow.active_flow_revision is not None

    root_node = next(
        node for node in refreshed_flow.active_flow_revision.nodes if node.node_key == "root"
    )
    root_attempt = root_node.attempts[-1]

    proposal = await request_replan(
        db_session,
        flow_id=flow.id,
        payload=NodePlanRevisionCreate(
            requesting_flow_node_id=root_node.id,
            requesting_node_attempt_id=root_attempt.id,
            reason="preserve task resources on replan",
            patch=NodePlanPatchPayload(
                nodes=[
                    NodePlanPatchNode(
                        id="root",
                        role="planner-supervisor",
                        mode=WorkflowMode.PLAN,
                    ),
                    NodePlanPatchNode(
                        id="loop",
                        role="main-loop-worker",
                        mode=WorkflowMode.PERSISTENT_EXECUTE,
                    ),
                ],
                edges=[NodePlanPatchEdge.model_validate({"from": "root", "to": "loop"})],
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
    loop_payload = candidate_revision.compiled_plan.nodes[1].effective_payload

    assert root_payload["task_defaults"]["workspace"]["mode"] == "ensure_task_primary"
    assert root_payload["task_defaults"]["manifests"]["mode"] == "ensure_task_root"
    assert root_payload["resources"]["workspace"]["mounts"][0]["ref"] == "task.primary_workspace"
    assert loop_payload["resources"]["workspace"]["mounts"][0]["access"] == "read_write"
