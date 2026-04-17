from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ResourceScope,
    TaskResourceBindingMode,
    TaskResourceBindingRole,
    WorkspaceRootKind,
    WorkspaceRootMode,
)
from app.db.models.runtime import (
    ContextSpace,
    ManifestRoot,
    Task,
    TaskResourceBinding,
    WorkspaceRoot,
)
from app.runtime.runner import start_flow_from_workflow
from app.schemas.runtime import FlowStartFromWorkflowCreate, TaskCreate
from app.services.registry_service import bootstrap_registry


async def _bootstrap_registry(db_session: AsyncSession) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()


async def test_task_resource_models_persist_expected_bindings_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    task = Task(title="resource task", description="resource model smoke", input_payload={})
    db_session.add(task)
    await db_session.flush()

    workspace_root = WorkspaceRoot(
        scope=ResourceScope.TASK,
        key=f"task.{task.id}.workspace",
        title="Primary workspace",
        storage_uri=f"file:///tmp/tasks/{task.id}/workspace",
        kind=WorkspaceRootKind.REPO,
        mode=WorkspaceRootMode.CHECKOUT,
        content_hash="",
    )
    context_space = ContextSpace(
        scope=ResourceScope.TASK,
        key=f"task.{task.id}.context",
        title="Primary context",
        storage_uri=f"file:///tmp/tasks/{task.id}/context",
        content_hash="",
    )
    manifest_root = ManifestRoot(
        task_id=task.id,
        key="primary",
        storage_uri=f"file:///tmp/tasks/{task.id}/manifests",
    )
    db_session.add_all([workspace_root, context_space, manifest_root])
    await db_session.flush()

    db_session.add_all(
        [
            TaskResourceBinding(
                task_id=task.id,
                binding_role=TaskResourceBindingRole.PRIMARY_WORKSPACE,
                workspace_root_id=workspace_root.id,
                mode=TaskResourceBindingMode.ENSURE_TASK_PRIMARY,
                read_only=False,
                required=True,
            ),
            TaskResourceBinding(
                task_id=task.id,
                binding_role=TaskResourceBindingRole.PRIMARY_CONTEXT,
                context_space_id=context_space.id,
                mode=TaskResourceBindingMode.SEED_FROM,
                required=True,
                metadata_={"seed_from": ["task_input"]},
            ),
            TaskResourceBinding(
                task_id=task.id,
                binding_role=TaskResourceBindingRole.MANIFEST_ROOT,
                manifest_root_id=manifest_root.id,
                mode=TaskResourceBindingMode.ENSURE_TASK_ROOT,
                required=True,
            ),
        ]
    )
    await db_session.commit()

    persisted_task = await db_session.scalar(
        select(Task)
        .options(
            selectinload(Task.manifest_roots),
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.workspace_root),
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.context_space),
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.manifest_root),
        )
        .where(Task.id == task.id)
    )
    assert persisted_task is not None
    assert len(persisted_task.manifest_roots) == 1
    assert len(persisted_task.resource_bindings) == 3

    binding_by_role = {
        binding.binding_role.value: binding for binding in persisted_task.resource_bindings
    }
    assert binding_by_role["primary_workspace"].workspace_root is not None
    assert binding_by_role["primary_workspace"].workspace_root.key == f"task.{task.id}.workspace"
    assert binding_by_role["primary_context"].context_space is not None
    assert binding_by_role["primary_context"].metadata_["seed_from"] == ["task_input"]
    assert binding_by_role["manifest_root"].manifest_root is not None
    assert binding_by_role["manifest_root"].manifest_root.storage_uri.endswith("/manifests")


async def test_task_resource_binding_rejects_multiple_targets_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    task = Task(title="bad binding task", input_payload={})
    workspace_root = WorkspaceRoot(
        scope=ResourceScope.TASK,
        key="bad-binding.workspace",
        title="workspace",
        storage_uri="file:///tmp/workspace",
        kind=WorkspaceRootKind.REPO,
        mode=WorkspaceRootMode.CHECKOUT,
        content_hash="",
    )
    context_space = ContextSpace(
        scope=ResourceScope.TASK,
        key="bad-binding.context",
        title="context",
        storage_uri="file:///tmp/context",
        content_hash="",
    )
    db_session.add_all([task, workspace_root, context_space])
    await db_session.flush()

    db_session.add(
        TaskResourceBinding(
            task_id=task.id,
            binding_role=TaskResourceBindingRole.REFERENCE_WORKSPACE,
            workspace_root_id=workspace_root.id,
            context_space_id=context_space.id,
            mode=TaskResourceBindingMode.USE_EXISTING,
        )
    )

    try:
        await db_session.commit()
    except IntegrityError:
        await db_session.rollback()
    else:
        raise AssertionError("expected task_resource_bindings target-exclusivity check to fail")


async def test_task_resource_binding_rejects_duplicate_primary_workspace_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    task = Task(title="duplicate primary task", input_payload={})
    workspace_a = WorkspaceRoot(
        scope=ResourceScope.TASK,
        key="dup-primary.workspace.a",
        title="workspace a",
        storage_uri="file:///tmp/workspace-a",
        kind=WorkspaceRootKind.REPO,
        mode=WorkspaceRootMode.CHECKOUT,
        content_hash="",
    )
    workspace_b = WorkspaceRoot(
        scope=ResourceScope.TASK,
        key="dup-primary.workspace.b",
        title="workspace b",
        storage_uri="file:///tmp/workspace-b",
        kind=WorkspaceRootKind.REPO,
        mode=WorkspaceRootMode.CHECKOUT,
        content_hash="",
    )
    db_session.add_all([task, workspace_a, workspace_b])
    await db_session.flush()

    db_session.add_all(
        [
            TaskResourceBinding(
                task_id=task.id,
                binding_role=TaskResourceBindingRole.PRIMARY_WORKSPACE,
                workspace_root_id=workspace_a.id,
                mode=TaskResourceBindingMode.ENSURE_TASK_PRIMARY,
            ),
            TaskResourceBinding(
                task_id=task.id,
                binding_role=TaskResourceBindingRole.PRIMARY_WORKSPACE,
                workspace_root_id=workspace_b.id,
                mode=TaskResourceBindingMode.ENSURE_TASK_PRIMARY,
            ),
        ]
    )

    try:
        await db_session.commit()
    except IntegrityError:
        await db_session.rollback()
    else:
        raise AssertionError("expected only one primary_workspace binding per task")


async def test_flow_nodes_materialize_logical_node_keys_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    await _bootstrap_registry(db_session)

    _flow, _revision, flow_nodes = await start_flow_from_workflow(
        db_session,
        workflow_key="default-bugfix",
        payload=FlowStartFromWorkflowCreate(
            task=TaskCreate(
                title="logical-node-key flow",
                description="ensure flow-node lineage field is populated",
                input_payload={"source": "test"},
            )
        ),
    )
    await db_session.commit()

    assert flow_nodes
    assert all(node.logical_node_key == node.node_key for node in flow_nodes)
