from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import load_settings
from app.core.enums import TaskResourceBindingRole, TaskStatus
from app.db.models.runtime import Task, TaskResourceBinding
from app.paths import ensure_task_dirs
from app.runtime.packaging import ensure_task_compose_for_task
from app.runtime.resources import (
    binding_target as resolve_binding_target,
)
from app.runtime.resources import (
    ensure_task_resource_bindings,
    load_task_resource_bindings,
)
from app.schemas.runtime import TaskCreate, TaskFileUploadRead

_DEFAULT_TASK_DEFAULTS: dict[str, dict[str, object]] = {
    "workspace": {"mode": "ensure_task_primary"},
    "context": {"mode": "seed_from", "seed_from": ["workspace"]},
    "manifests": {"mode": "ensure_task_root"},
}

_UPLOAD_TARGETS: dict[str, tuple[TaskResourceBindingRole, str, str]] = {
    "workspace_docs": (TaskResourceBindingRole.PRIMARY_WORKSPACE, "workspace_docs", "workspace"),
    "primary_workspace": (TaskResourceBindingRole.PRIMARY_WORKSPACE, "workspace_docs", "workspace"),
    "context_docs": (TaskResourceBindingRole.PRIMARY_CONTEXT, "context_docs", "context"),
    "primary_context": (TaskResourceBindingRole.PRIMARY_CONTEXT, "context_docs", "context"),
    "manifest_bundle": (TaskResourceBindingRole.MANIFEST_ROOT, "manifest_bundle", "manifests"),
    "manifest_root": (TaskResourceBindingRole.MANIFEST_ROOT, "manifest_bundle", "manifests"),
}
async def _bootstrap_task_resource_bindings(
    session: AsyncSession,
    *,
    task: Task,
    task_defaults: dict[str, Any] = _DEFAULT_TASK_DEFAULTS,
) -> dict[str, TaskResourceBinding]:
    return await ensure_task_resource_bindings(
        session,
        task=task,
        task_defaults=task_defaults,
    )


async def bootstrap_task_runtime_state(
    session: AsyncSession,
    *,
    task: Task,
    task_defaults: dict[str, Any] = _DEFAULT_TASK_DEFAULTS,
) -> dict[str, TaskResourceBinding]:
    bindings_by_role = await _bootstrap_task_resource_bindings(
        session,
        task=task,
        task_defaults=task_defaults,
    )
    await ensure_task_compose_for_task(
        session,
        task=task,
        task_defaults=task_defaults,
    )
    return bindings_by_role


async def create_task(
    session: AsyncSession,
    payload: TaskCreate,
    *,
    bootstrap_defaults: bool = True,
) -> Task:
    key = (payload.key or payload.title or "task").strip()
    task = Task(
        title=payload.title,
        description=payload.description,
        input_payload={**payload.input_payload, "_task_key": key},
        status=TaskStatus.PENDING,
    )
    session.add(task)
    await session.flush()
    if bootstrap_defaults:
        await bootstrap_task_runtime_state(session, task=task)
    return task


def _normalize_relative_path(filename: str | None, relative_path: str | None) -> Path:
    candidate = (relative_path or filename or "").strip()
    if not candidate:
        raise ValueError("relative_path is required when the uploaded file has no filename")
    posix_path = PurePosixPath(candidate)
    if posix_path.is_absolute() or any(part in {"", ".", ".."} for part in posix_path.parts):
        raise ValueError("relative_path must stay inside the task-owned workspace")
    return Path(*posix_path.parts)


def _resolve_upload_target(target_slot: str) -> tuple[TaskResourceBindingRole, str, str]:
    resolved = _UPLOAD_TARGETS.get(target_slot.strip())
    if resolved is None:
        allowed = ", ".join(sorted({slot for _, slot, _ in _UPLOAD_TARGETS.values()}))
        raise ValueError(f"unsupported target_slot '{target_slot}', expected one of: {allowed}")
    return resolved


def _assert_upload_destination_within_task_root(
    *,
    destination: Path,
    allowed_root: Path,
    task_root: Path,
) -> None:
    resolved_allowed_root = allowed_root.resolve()
    resolved_task_root = task_root.resolve()
    resolved_destination = destination.resolve(strict=False)

    if not resolved_destination.is_relative_to(resolved_task_root):
        raise ValueError("relative_path escapes the task-owned root")
    if not resolved_destination.is_relative_to(resolved_allowed_root):
        raise ValueError("relative_path escapes the target task binding root")


async def upload_task_file(
    session: AsyncSession,
    *,
    task: Task,
    file: UploadFile,
    target_slot: str = "context_docs",
    relative_path: str | None = None,
) -> TaskFileUploadRead:
    binding_role, canonical_slot, directory_key = _resolve_upload_target(target_slot)
    relative_target = _normalize_relative_path(file.filename, relative_path)
    bindings = await load_task_resource_bindings(session, task_id=task.id)
    bindings_by_role = {binding.binding_role.value: binding for binding in bindings}

    binding = bindings_by_role.get(binding_role.value)
    if binding is None:
        raise ValueError(
            "task runtime binding "
            f"'{binding_role.value}' is missing for task {task.id}; "
            "launch/bootstrap state is incomplete"
        )

    _target_kind, binding_target = resolve_binding_target(binding)
    task_key = None
    if isinstance(task.input_payload, dict):
        task_key = task.input_payload.get("_task_key")
    directories = ensure_task_dirs(task.id, load_settings().data_dir, task_key=task_key)
    destination = directories[directory_key] / relative_target
    destination.parent.mkdir(parents=True, exist_ok=True)
    _assert_upload_destination_within_task_root(
        destination=destination,
        allowed_root=directories[directory_key],
        task_root=directories["task_dir"],
    )

    sha256 = hashlib.sha256()
    size_bytes = 0
    with destination.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            sha256.update(chunk)
            size_bytes += len(chunk)
            handle.write(chunk)
    await file.close()

    await ensure_task_compose_for_task(session, task=task)

    base_storage_uri = binding_target.storage_uri.rstrip("/")
    return TaskFileUploadRead(
        task_id=task.id,
        target_slot=canonical_slot,
        binding_role=binding_role,
        relative_path=relative_target.as_posix(),
        storage_uri=f"{base_storage_uri}/{relative_target.as_posix()}",
        content_type=file.content_type,
        size_bytes=size_bytes,
        sha256=sha256.hexdigest(),
    )
