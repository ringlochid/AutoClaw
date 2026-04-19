from __future__ import annotations

from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import load_settings
from app.db.models.runtime import (
    CompiledPlan,
    Flow,
    NodeAttempt,
    Task,
    TaskCompose,
    TaskResourceBinding,
)
from app.paths import ensure_task_dirs


def _task_defaults_snapshot(compiled_plan: CompiledPlan) -> dict[str, Any]:
    resolved = compiled_plan.source_snapshot.get("resolved")
    if isinstance(resolved, dict):
        task_defaults = resolved.get("task_defaults")
        if isinstance(task_defaults, dict):
            return cast(dict[str, Any], task_defaults)
    return {}


async def _load_task_for_binding_snapshot(session: AsyncSession, task_id) -> Task | None:
    return await session.scalar(
        select(Task)
        .options(
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.workspace_root),
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.context_space),
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.manifest_root),
        )
        .where(Task.id == task_id)
    )


def _task_binding_snapshot(task: Task) -> tuple[str | None, str | None, str | None]:
    workspace_root_uri = None
    context_root_uri = None
    manifest_root_uri = None
    for binding in list(task.resource_bindings or []):
        if binding.workspace_root is not None and workspace_root_uri is None:
            workspace_root_uri = binding.workspace_root.storage_uri
        elif binding.context_space is not None and context_root_uri is None:
            context_root_uri = binding.context_space.storage_uri
        elif binding.manifest_root is not None and manifest_root_uri is None:
            manifest_root_uri = binding.manifest_root.storage_uri
    return workspace_root_uri, context_root_uri, manifest_root_uri


async def _upsert_task_compose(
    session: AsyncSession,
    *,
    task: Task,
    workflow_version_id=None,
    compiled_plan_id=None,
    entrypoint: str | None = None,
    task_defaults: dict[str, Any] | None = None,
) -> TaskCompose:
    task_compose = await session.scalar(select(TaskCompose).where(TaskCompose.task_id == task.id))
    directories = ensure_task_dirs(task.id, load_settings().data_dir)
    task_for_snapshot = await _load_task_for_binding_snapshot(session, task.id)
    workspace_root_uri, context_root_uri, manifest_root_uri = _task_binding_snapshot(
        task_for_snapshot or task
    )

    payload = task.input_payload if isinstance(task.input_payload, dict) else {}
    context_refs = []
    if task_defaults:
        context_defaults = task_defaults.get("context")
        if isinstance(context_defaults, dict):
            seed_from = context_defaults.get("seed_from")
            if isinstance(seed_from, list):
                context_refs = list(seed_from)

    values = dict(
        workflow_version_id=workflow_version_id,
        compiled_plan_id=compiled_plan_id,
        entrypoint=entrypoint,
        status="ready",
        metadata_={
            "title": task.title,
            "description": task.description,
            "materialized_paths": {
                "workspace": str(directories["workspace"]),
                "context": str(directories["context"]),
                "manifests": str(directories["manifests"]),
            },
        },
        input_payload=payload,
        context_refs=context_refs,
        skill_dependencies=[],
        workspace_root_uri=workspace_root_uri,
        context_root_uri=context_root_uri,
        manifest_root_uri=manifest_root_uri,
        materialization_root=f"task://{task.id}",
    )

    if task_compose is None:
        task_compose = TaskCompose(task_id=task.id, **values)
        session.add(task_compose)
    else:
        for key, value in values.items():
            setattr(task_compose, key, value)
    await session.flush()
    return task_compose


async def ensure_task_compose_for_task(
    session: AsyncSession,
    *,
    task: Task,
    task_defaults: dict[str, Any] | None = None,
) -> TaskCompose:
    return await _upsert_task_compose(
        session,
        task=task,
        task_defaults=task_defaults or {},
    )


async def ensure_task_compose_for_compiled_plan(
    session: AsyncSession,
    *,
    task: Task,
    compiled_plan: CompiledPlan,
) -> TaskCompose:
    entrypoint = None
    if compiled_plan.nodes:
        entrypoint = compiled_plan.nodes[0].node_key
    return await _upsert_task_compose(
        session,
        task=task,
        workflow_version_id=compiled_plan.workflow_version_id,
        compiled_plan_id=compiled_plan.id,
        entrypoint=entrypoint,
        task_defaults=_task_defaults_snapshot(compiled_plan),
    )


async def current_runtime_view(
    session: AsyncSession,
    *,
    flow: Flow,
    node_attempt: NodeAttempt,
):
    task_compose = await session.scalar(
        select(TaskCompose).where(TaskCompose.task_id == flow.task_id)
    )
    current_manifest = None
    if node_attempt.context_manifests:
        current_manifest = node_attempt.context_manifests[-1]
    current_session = flow.active_flow_revision.nodes[0].node_session if False else None
    return {
        "task_compose": task_compose,
        "current_manifest": current_manifest,
        "current_session": current_session,
    }
