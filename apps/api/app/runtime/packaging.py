from __future__ import annotations

import hashlib
import json
from typing import Any, cast

from sqlalchemy import inspect as sa_inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import load_settings
from app.core.enums import NodeAttemptStatus
from app.db.models.runtime import (
    CompiledPlan,
    CompiledPlanNode,
    ContextManifest,
    Flow,
    FlowNode,
    FlowRevision,
    NodeAttempt,
    NodeSession,
    RuntimeContainer,
    RuntimeImage,
    Task,
    TaskCompose,
    TaskImage,
    TaskResourceBinding,
)
from app.paths import ensure_task_dirs
from app.runtime.state import utcnow_naive


def _stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _task_defaults_snapshot(compiled_plan: CompiledPlan) -> dict[str, Any]:
    resolved = compiled_plan.source_snapshot.get("resolved")
    if isinstance(resolved, dict):
        task_defaults = resolved.get("task_defaults")
        if isinstance(task_defaults, dict):
            return cast(dict[str, Any], task_defaults)
    return {}


def _task_binding_snapshot(task: Task) -> list[dict[str, Any]]:
    bindings = []
    for binding in list(task.resource_bindings or []):
        target = None
        if binding.workspace_root is not None:
            target = {
                "kind": "workspace_root",
                "id": str(binding.workspace_root.id),
                "key": binding.workspace_root.key,
                "storage_uri": binding.workspace_root.storage_uri,
                "metadata": binding.workspace_root.metadata_,
            }
        elif binding.context_space is not None:
            target = {
                "kind": "context_space",
                "id": str(binding.context_space.id),
                "key": binding.context_space.key,
                "storage_uri": binding.context_space.storage_uri,
                "metadata": binding.context_space.metadata_,
            }
        elif binding.manifest_root is not None:
            target = {
                "kind": "manifest_root",
                "id": str(binding.manifest_root.id),
                "key": binding.manifest_root.key,
                "storage_uri": binding.manifest_root.storage_uri,
                "metadata": binding.manifest_root.metadata_,
            }
        bindings.append(
            {
                "binding_role": binding.binding_role.value,
                "mode": binding.mode.value,
                "read_only": binding.read_only,
                "required": binding.required,
                "metadata": binding.metadata_,
                "target": target,
            }
        )
    return bindings


async def ensure_task_compose_for_compiled_plan(
    session: AsyncSession,
    *,
    task: Task,
    compiled_plan: CompiledPlan,
) -> TaskCompose:
    directories = ensure_task_dirs(task.id, load_settings().data_dir)
    task_image_spec = {
        "workflow_version_id": str(compiled_plan.workflow_version_id),
        "compiler_version": compiled_plan.compiler_version,
        "task_defaults": _task_defaults_snapshot(compiled_plan),
    }
    task_image_hash = _stable_hash(task_image_spec)
    task_image = await session.scalar(select(TaskImage).where(TaskImage.image_hash == task_image_hash))
    if task_image is None:
        task_image = TaskImage(
            image_hash=task_image_hash,
            source_task_id=task.id,
            spec_payload=task_image_spec,
        )
        session.add(task_image)
        await session.flush()

    task_for_snapshot = await session.scalar(
        select(Task)
        .options(
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.workspace_root),
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.context_space),
            selectinload(Task.resource_bindings).selectinload(TaskResourceBinding.manifest_root),
        )
        .where(Task.id == task.id)
    )
    compose_payload = {
        "task_defaults": _task_defaults_snapshot(compiled_plan),
        "resource_bindings": _task_binding_snapshot(task_for_snapshot or task),
        "materialized_paths": {
            "workspace": str(directories["workspace"]),
            "context": str(directories["context"]),
            "manifests": str(directories["manifests"]),
        },
    }
    task_compose = await session.scalar(select(TaskCompose).where(TaskCompose.task_id == task.id))
    if task_compose is None:
        task_compose = TaskCompose(
            task_id=task.id,
            task_image_id=task_image.id,
            status="ready",
            materialization_root=f"task://{task.id}",
            compose_payload=compose_payload,
        )
        session.add(task_compose)
    else:
        task_compose.task_image_id = task_image.id
        task_compose.status = "ready"
        task_compose.materialization_root = f"task://{task.id}"
        task_compose.compose_payload = compose_payload
    await session.flush()
    return task_compose


def _runtime_image_spec(compiled_node: CompiledPlanNode | None, flow_node: FlowNode) -> dict[str, Any]:
    effective_payload = compiled_node.effective_payload if compiled_node is not None else {}
    return {
        "compiled_plan_node_id": str(compiled_node.id) if compiled_node is not None else None,
        "mode": flow_node.status_payload.get("mode"),
        "node_key": flow_node.node_key,
        "node_path": flow_node.node_path,
        "skill_bindings": compiled_node.skill_bindings if compiled_node is not None else [],
        "effective_payload": effective_payload,
    }


def _container_status(node_attempt: NodeAttempt, manifest: ContextManifest | None) -> str:
    if node_attempt.status == NodeAttemptStatus.BLOCKED and manifest is not None:
        if manifest.status.value == "projected":
            return "bootstrap_blocked"
        if manifest.status.value == "acked":
            return "blocked"
    return node_attempt.status.value


def _bootstrap_state(manifest: ContextManifest | None) -> str:
    if manifest is None:
        return "none"
    return manifest.status.value


async def _compiled_plan_for_attempt(
    session: AsyncSession,
    *,
    flow: Flow,
    node_attempt: NodeAttempt,
) -> CompiledPlan | None:
    if node_attempt.flow_revision_id is not None:
        return await session.scalar(
            select(CompiledPlan)
            .join(FlowRevision, FlowRevision.compiled_plan_id == CompiledPlan.id)
            .where(FlowRevision.id == node_attempt.flow_revision_id)
        )
    flow_inspection = sa_inspect(flow)
    if "seed_compiled_plan" in flow_inspection.unloaded:
        return await session.scalar(select(CompiledPlan).where(CompiledPlan.id == flow.seed_compiled_plan_id))
    return flow.seed_compiled_plan


async def upsert_runtime_container(
    session: AsyncSession,
    *,
    flow: Flow,
    flow_node: FlowNode,
    node_attempt: NodeAttempt,
    node_session: NodeSession | None,
    manifest: ContextManifest | None = None,
    task_compose_plan: CompiledPlan | None = None,
) -> RuntimeContainer:
    flow_node_inspection = sa_inspect(flow_node)
    if "source_compiled_plan_node" in flow_node_inspection.unloaded:
        compiled_node = None
        if flow_node.source_compiled_plan_node_id is not None:
            compiled_node = await session.scalar(
                select(CompiledPlanNode).where(
                    CompiledPlanNode.id == flow_node.source_compiled_plan_node_id
                )
            )
    else:
        compiled_node = flow_node.source_compiled_plan_node

    runtime_image_spec = _runtime_image_spec(compiled_node, flow_node)
    runtime_image_hash = _stable_hash(runtime_image_spec)
    runtime_image = await session.scalar(
        select(RuntimeImage).where(RuntimeImage.image_hash == runtime_image_hash)
    )
    if runtime_image is None:
        runtime_image = RuntimeImage(
            image_hash=runtime_image_hash,
            compiled_plan_node_id=(compiled_node.id if compiled_node is not None else None),
            spec_payload=runtime_image_spec,
        )
        session.add(runtime_image)
        await session.flush()

    task_compose: TaskCompose | None = None
    compiled_plan_for_task_compose = task_compose_plan or await _compiled_plan_for_attempt(
        session,
        flow=flow,
        node_attempt=node_attempt,
    )
    if compiled_plan_for_task_compose is not None:
        task_compose = await ensure_task_compose_for_compiled_plan(
            session,
            task=flow.task,
            compiled_plan=compiled_plan_for_task_compose,
        )

    container = await session.scalar(
        select(RuntimeContainer).where(RuntimeContainer.flow_node_id == flow_node.id)
    )
    now = utcnow_naive()
    container_payload = {
        "node_key": flow_node.node_key,
        "node_path": flow_node.node_path,
        "mode": flow_node.status_payload.get("mode"),
        "manifest_id": str(manifest.id) if manifest is not None else None,
        "manifest_hash": manifest.manifest_hash if manifest is not None else None,
    }

    if container is None:
        container = RuntimeContainer(
            task_id=flow.task_id,
            task_compose_id=(task_compose.id if task_compose is not None else None),
            runtime_image_id=runtime_image.id,
            flow_id=flow.id,
            flow_node_id=flow_node.id,
            node_session_id=(node_session.id if node_session is not None else None),
            current_node_attempt_id=node_attempt.id,
            current_context_manifest_id=(manifest.id if manifest is not None else None),
            backend_kind="openclaw_session",
            backend_handle=(node_session.provider_session_key if node_session is not None else None),
            status=_container_status(node_attempt, manifest),
            bootstrap_state=_bootstrap_state(manifest),
            container_payload=container_payload,
            started_at=node_attempt.started_at,
            last_seen_at=now,
            ended_at=node_attempt.finished_at,
        )
        session.add(container)
    else:
        container.task_compose_id = task_compose.id if task_compose is not None else None
        container.runtime_image_id = runtime_image.id
        container.node_session_id = node_session.id if node_session is not None else None
        container.current_node_attempt_id = node_attempt.id
        if manifest is not None:
            container.current_context_manifest_id = manifest.id
        container.backend_kind = "openclaw_session"
        container.backend_handle = node_session.provider_session_key if node_session is not None else None
        container.status = _container_status(node_attempt, manifest)
        container.bootstrap_state = _bootstrap_state(manifest)
        container.container_payload = container_payload
        container.last_seen_at = now
        if node_attempt.status in {
            NodeAttemptStatus.SUCCEEDED,
            NodeAttemptStatus.FAILED,
            NodeAttemptStatus.CANCELLED,
            NodeAttemptStatus.ABORTED,
        }:
            container.ended_at = node_attempt.finished_at or now
        else:
            container.ended_at = None
    await session.flush()
    return container
