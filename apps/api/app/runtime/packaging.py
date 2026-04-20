from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import load_settings
from app.db.models.runtime import (
    CompiledPlan,
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


async def _load_task_for_binding_snapshot(
    session: AsyncSession,
    task_id: UUID,
) -> Task | None:
    return cast(
        Task | None,
        await session.scalar(
            select(Task)
            .options(
                selectinload(Task.resource_bindings).selectinload(
                    TaskResourceBinding.workspace_root
                ),
                selectinload(Task.resource_bindings).selectinload(
                    TaskResourceBinding.context_space
                ),
                selectinload(Task.resource_bindings).selectinload(
                    TaskResourceBinding.manifest_root
                ),
            )
            .where(Task.id == task_id)
        ),
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


def _materialized_paths_snapshot(directories: dict[str, Any]) -> dict[str, str]:
    return {
        "workspace": str(directories["workspace"]),
        "context": str(directories["context"]),
        "manifests": str(directories["manifests"]),
    }


def _merge_task_compose_metadata(
    task_compose: TaskCompose | None,
    *,
    task_key: str | None,
    task: Task,
    directories: dict[str, Any],
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    existing_metadata = (
        dict(task_compose.metadata_) if task_compose is not None and task_compose.metadata_ else {}
    )
    provided_metadata = dict(metadata or {})

    merged = {
        **existing_metadata,
        "key": task_key,
        "title": task.title,
        "description": task.description,
        **provided_metadata,
    }

    existing_paths = existing_metadata.get("materialized_paths")
    provided_paths = provided_metadata.get("materialized_paths")
    materialized_paths: dict[str, str] = _materialized_paths_snapshot(directories)
    if isinstance(existing_paths, dict):
        materialized_paths = {
            **materialized_paths,
            **{key: str(value) for key, value in existing_paths.items()},
        }
    if isinstance(provided_paths, dict):
        materialized_paths = {
            **materialized_paths,
            **{key: str(value) for key, value in provided_paths.items()},
        }
    merged["materialized_paths"] = materialized_paths
    return merged


def _compose_context_refs(
    task_compose: TaskCompose | None,
    *,
    task_defaults: dict[str, Any] | None,
    context_refs_override: list[str] | list[dict[str, Any]] | None,
) -> list[str] | list[dict[str, Any]]:
    if context_refs_override is not None:
        return context_refs_override

    if task_defaults:
        context_defaults = task_defaults.get("context")
        if isinstance(context_defaults, dict):
            seed_from = context_defaults.get("seed_from")
            if isinstance(seed_from, list):
                return list(seed_from)

    if task_compose is not None:
        return cast(list[str] | list[dict[str, Any]], list(task_compose.context_refs or []))

    return []


def _compose_skill_dependencies(
    task_compose: TaskCompose | None,
    *,
    skill_dependencies: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if skill_dependencies is not None:
        return skill_dependencies
    if task_compose is not None:
        return cast(list[dict[str, Any]], list(task_compose.skill_dependencies or []))
    return []


async def _upsert_task_compose(
    session: AsyncSession,
    *,
    task: Task,
    workflow_version_id: UUID | None = None,
    compiled_plan_id: UUID | None = None,
    entrypoint: str | None = None,
    task_defaults: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    context_refs_override: list[str] | list[dict[str, Any]] | None = None,
    skill_dependencies: list[dict[str, Any]] | None = None,
) -> TaskCompose:
    task_compose = await session.scalar(select(TaskCompose).where(TaskCompose.task_id == task.id))
    task_key = None
    if isinstance(task.input_payload, dict):
        task_key = task.input_payload.get("_task_key")
    directories = ensure_task_dirs(task.id, load_settings().data_dir, task_key=task_key)
    task_for_snapshot = await _load_task_for_binding_snapshot(session, task.id)
    workspace_root_uri, context_root_uri, manifest_root_uri = _task_binding_snapshot(
        task_for_snapshot or task
    )

    payload = task.input_payload if isinstance(task.input_payload, dict) else {}
    values = dict(
        workflow_version_id=(
            workflow_version_id
            if workflow_version_id is not None
            else (task_compose.workflow_version_id if task_compose is not None else None)
        ),
        compiled_plan_id=(
            compiled_plan_id
            if compiled_plan_id is not None
            else (task_compose.compiled_plan_id if task_compose is not None else None)
        ),
        entrypoint=(
            entrypoint
            if entrypoint is not None
            else (task_compose.entrypoint if task_compose else None)
        ),
        status="ready",
        metadata_=_merge_task_compose_metadata(
            task_compose,
            task_key=task_key,
            task=task,
            directories=directories,
            metadata=metadata,
        ),
        input_payload=payload,
        context_refs=_compose_context_refs(
            task_compose,
            task_defaults=task_defaults,
            context_refs_override=context_refs_override,
        ),
        skill_dependencies=_compose_skill_dependencies(
            task_compose,
            skill_dependencies=skill_dependencies,
        ),
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
    metadata: dict[str, Any] | None = None,
    context_refs_override: list[str] | list[dict[str, Any]] | None = None,
    skill_dependencies: list[dict[str, Any]] | None = None,
) -> TaskCompose:
    return await _upsert_task_compose(
        session,
        task=task,
        task_defaults=task_defaults or {},
        metadata=metadata,
        context_refs_override=context_refs_override,
        skill_dependencies=skill_dependencies,
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
