from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ResourceScope,
    TaskResourceBindingMode,
    TaskResourceBindingRole,
    WorkspaceRootKind,
    WorkspaceRootMode,
)
from app.core.errors import InvalidDefinitionError
from app.db.models.runtime import (
    CompiledPlan,
    CompiledPlanNode,
    ContextSpace,
    ManifestRoot,
    Task,
    TaskResourceBinding,
    WorkspaceRoot,
)

_TASK_REF_ROLE_BY_SLOT = {
    "workspace": TaskResourceBindingRole.PRIMARY_WORKSPACE,
    "context": TaskResourceBindingRole.PRIMARY_CONTEXT,
    "manifests": TaskResourceBindingRole.MANIFEST_ROOT,
}


def _compiled_plan_task_defaults(compiled_plan: CompiledPlan) -> dict[str, dict[str, Any]]:
    resolved = compiled_plan.source_snapshot.get("resolved")
    if isinstance(resolved, dict):
        task_defaults = resolved.get("task_defaults")
        if isinstance(task_defaults, dict):
            return cast(dict[str, dict[str, Any]], task_defaults)

    if compiled_plan.nodes:
        task_defaults = compiled_plan.nodes[0].effective_payload.get("task_defaults")
        if isinstance(task_defaults, dict):
            return cast(dict[str, dict[str, Any]], task_defaults)

    return {}


async def _load_task_resource_bindings(
    session: AsyncSession,
    *,
    task_id: Any,
) -> list[TaskResourceBinding]:
    result = await session.scalars(
        select(TaskResourceBinding)
        .options(
            selectinload(TaskResourceBinding.workspace_root),
            selectinload(TaskResourceBinding.context_space),
            selectinload(TaskResourceBinding.manifest_root),
        )
        .where(TaskResourceBinding.task_id == task_id)
        .order_by(TaskResourceBinding.created_at.asc())
    )
    return list(result.all())


async def _find_workspace_root_by_key(
    session: AsyncSession,
    *,
    key: str,
) -> WorkspaceRoot | None:
    return cast(
        WorkspaceRoot | None,
        await session.scalar(select(WorkspaceRoot).where(WorkspaceRoot.key == key)),
    )


async def _find_context_space_by_key(
    session: AsyncSession,
    *,
    key: str,
) -> ContextSpace | None:
    return cast(
        ContextSpace | None,
        await session.scalar(select(ContextSpace).where(ContextSpace.key == key)),
    )


async def _find_manifest_root(
    session: AsyncSession,
    *,
    task_id: Any,
    key: str,
) -> ManifestRoot | None:
    return cast(
        ManifestRoot | None,
        await session.scalar(
            select(ManifestRoot).where(ManifestRoot.task_id == task_id, ManifestRoot.key == key)
        ),
    )


async def _resolve_required_workspace_root(
    session: AsyncSession,
    *,
    ref: str,
) -> WorkspaceRoot:
    workspace_root = await _find_workspace_root_by_key(session, key=ref)
    if workspace_root is None:
        raise InvalidDefinitionError(f"Workspace root ref '{ref}' could not be resolved")
    return workspace_root


async def _resolve_required_context_space(
    session: AsyncSession,
    *,
    ref: str,
) -> ContextSpace:
    context_space = await _find_context_space_by_key(session, key=ref)
    if context_space is None:
        raise InvalidDefinitionError(f"Context space ref '{ref}' could not be resolved")
    return context_space


async def _ensure_workspace_binding(
    session: AsyncSession,
    *,
    task: Task,
    spec: dict[str, Any],
) -> TaskResourceBinding:
    mode = spec["mode"]
    metadata = dict(spec.get("metadata") or {})

    workspace_root: WorkspaceRoot | None
    if mode == "use_existing":
        workspace_root = await _resolve_required_workspace_root(session, ref=spec["ref"])
    else:
        workspace_root = await _find_workspace_root_by_key(
            session,
            key=f"task.{task.id}.workspace",
        )
        if workspace_root is None:
            source_root: WorkspaceRoot | None = None
            if mode == "clone_from":
                source_root = await _resolve_required_workspace_root(session, ref=spec["ref"])
                metadata.setdefault("clone_from", spec["ref"])

            workspace_root = WorkspaceRoot(
                scope=ResourceScope.TASK,
                key=f"task.{task.id}.workspace",
                title="Task primary workspace",
                storage_uri=f"task://{task.id}/workspace",
                kind=(source_root.kind if source_root is not None else WorkspaceRootKind.REPO),
                mode=(source_root.mode if source_root is not None else WorkspaceRootMode.CHECKOUT),
                content_hash="",
                metadata_=metadata,
            )
            session.add(workspace_root)
            await session.flush()

    binding = TaskResourceBinding(
        task_id=task.id,
        binding_role=TaskResourceBindingRole.PRIMARY_WORKSPACE,
        workspace_root_id=workspace_root.id,
        mode=TaskResourceBindingMode(mode),
        read_only=spec.get("read_only"),
        required=bool(spec.get("required", True)),
        metadata_=metadata,
    )
    session.add(binding)
    await session.flush()
    return binding


async def _ensure_context_binding(
    session: AsyncSession,
    *,
    task: Task,
    spec: dict[str, Any],
    bindings_by_role: dict[str, TaskResourceBinding],
) -> TaskResourceBinding:
    mode = spec["mode"]
    metadata = dict(spec.get("metadata") or {})
    seed_from = spec.get("seed_from") or []
    if seed_from:
        metadata.setdefault("seed_from", list(seed_from))

    context_space: ContextSpace | None
    if mode == "use_existing":
        context_space = await _resolve_required_context_space(session, ref=spec["ref"])
    else:
        context_space = await _find_context_space_by_key(
            session,
            key=f"task.{task.id}.context",
        )
        if context_space is None:
            source_workspace_root_id = None
            if "workspace_docs" in seed_from:
                workspace_binding = bindings_by_role.get(
                    TaskResourceBindingRole.PRIMARY_WORKSPACE.value
                )
                if workspace_binding is not None:
                    source_workspace_root_id = workspace_binding.workspace_root_id
            if mode == "clone_from":
                metadata.setdefault("clone_from", spec["ref"])

            context_space = ContextSpace(
                scope=ResourceScope.TASK,
                key=f"task.{task.id}.context",
                title="Task primary context",
                storage_uri=f"task://{task.id}/context",
                source_workspace_root_id=source_workspace_root_id,
                content_hash="",
                metadata_=metadata,
            )
            session.add(context_space)
            await session.flush()

    binding = TaskResourceBinding(
        task_id=task.id,
        binding_role=TaskResourceBindingRole.PRIMARY_CONTEXT,
        context_space_id=context_space.id,
        mode=TaskResourceBindingMode(mode),
        read_only=spec.get("read_only"),
        required=bool(spec.get("required", True)),
        metadata_=metadata,
    )
    session.add(binding)
    await session.flush()
    return binding


async def _ensure_manifest_binding(
    session: AsyncSession,
    *,
    task: Task,
    spec: dict[str, Any],
) -> TaskResourceBinding:
    manifest_root = await _find_manifest_root(session, task_id=task.id, key="primary")
    if manifest_root is None:
        manifest_root = ManifestRoot(
            task_id=task.id,
            key="primary",
            storage_uri=f"task://{task.id}/manifests",
            metadata_=dict(spec.get("metadata") or {}),
        )
        session.add(manifest_root)
        await session.flush()

    binding = TaskResourceBinding(
        task_id=task.id,
        binding_role=TaskResourceBindingRole.MANIFEST_ROOT,
        manifest_root_id=manifest_root.id,
        mode=TaskResourceBindingMode(spec["mode"]),
        read_only=spec.get("read_only"),
        required=bool(spec.get("required", True)),
        metadata_=dict(spec.get("metadata") or {}),
    )
    session.add(binding)
    await session.flush()
    return binding


async def _ensure_task_default_binding(
    session: AsyncSession,
    *,
    task: Task,
    slot: str,
    spec: dict[str, Any],
    bindings_by_role: dict[str, TaskResourceBinding],
    allow_create: bool,
) -> TaskResourceBinding:
    role = _TASK_REF_ROLE_BY_SLOT[slot]
    existing_binding = bindings_by_role.get(role.value)
    if existing_binding is not None:
        return existing_binding
    if not allow_create:
        raise InvalidDefinitionError(
            f"Task {task.id} is missing required binding '{role.value}' for compiled workflow"
        )

    if slot == "workspace":
        return await _ensure_workspace_binding(session, task=task, spec=spec)
    if slot == "context":
        return await _ensure_context_binding(
            session,
            task=task,
            spec=spec,
            bindings_by_role=bindings_by_role,
        )
    if slot == "manifests":
        return await _ensure_manifest_binding(session, task=task, spec=spec)

    raise InvalidDefinitionError(f"Unsupported task default slot '{slot}'")


def _find_reference_binding(
    bindings: list[TaskResourceBinding],
    *,
    role: TaskResourceBindingRole,
    ref_name: str,
) -> TaskResourceBinding | None:
    for binding in bindings:
        if binding.binding_role != role:
            continue
        if binding.metadata_.get("ref_name") == ref_name:
            return binding
        if binding.workspace_root is not None and binding.workspace_root.key == ref_name:
            return binding
        if binding.context_space is not None and binding.context_space.key == ref_name:
            return binding
    return None


def _resolve_runtime_ref(
    *,
    ref: str,
    bindings: list[TaskResourceBinding],
    bindings_by_role: dict[str, TaskResourceBinding],
) -> TaskResourceBinding:
    if ref == "task.primary_workspace":
        binding = bindings_by_role.get(TaskResourceBindingRole.PRIMARY_WORKSPACE.value)
    elif ref == "task.primary_context":
        binding = bindings_by_role.get(TaskResourceBindingRole.PRIMARY_CONTEXT.value)
    elif ref.startswith("task.reference_workspace."):
        binding = _find_reference_binding(
            bindings,
            role=TaskResourceBindingRole.REFERENCE_WORKSPACE,
            ref_name=ref.removeprefix("task.reference_workspace."),
        )
    elif ref.startswith("task.reference_context."):
        binding = _find_reference_binding(
            bindings,
            role=TaskResourceBindingRole.REFERENCE_CONTEXT,
            ref_name=ref.removeprefix("task.reference_context."),
        )
    else:
        raise InvalidDefinitionError(f"Unsupported runtime resource ref '{ref}'")

    if binding is None:
        raise InvalidDefinitionError(f"Runtime resource ref '{ref}' could not be resolved")
    return binding


def _binding_target(binding: TaskResourceBinding) -> tuple[str, Any]:
    if binding.workspace_root is not None:
        return "workspace", binding.workspace_root
    if binding.context_space is not None:
        return "context", binding.context_space
    if binding.manifest_root is not None:
        return "manifests", binding.manifest_root
    raise InvalidDefinitionError(f"Task resource binding {binding.id} has no target")


def _render_resolved_binding(
    *,
    binding: TaskResourceBinding,
    ref: str,
    access: str | None,
    required: bool,
) -> dict[str, Any]:
    target_kind, target = _binding_target(binding)
    rendered = {
        "ref": ref,
        "binding_role": binding.binding_role.value,
        "binding_mode": binding.mode.value,
        "target_kind": target_kind,
        "target_id": str(target.id),
        "key": target.key,
        "storage_uri": target.storage_uri,
        "required": required,
    }
    if access is not None:
        rendered["access"] = access
    if binding.read_only is not None:
        rendered["read_only"] = binding.read_only
    if binding.metadata_:
        rendered["binding_metadata"] = binding.metadata_
    if target_kind == "workspace":
        rendered["workspace_kind"] = target.kind.value
        rendered["workspace_mode"] = target.mode.value
    return rendered


async def ensure_task_resources_for_compiled_plan(
    session: AsyncSession,
    *,
    task: Task,
    compiled_plan: CompiledPlan,
    allow_create: bool,
) -> None:
    bindings = await _load_task_resource_bindings(session, task_id=task.id)
    bindings_by_role = {binding.binding_role.value: binding for binding in bindings}

    for slot, spec in _compiled_plan_task_defaults(compiled_plan).items():
        binding = await _ensure_task_default_binding(
            session,
            task=task,
            slot=slot,
            spec=spec,
            bindings_by_role=bindings_by_role,
            allow_create=allow_create,
        )
        bindings_by_role[binding.binding_role.value] = binding
        if binding not in bindings:
            bindings.append(binding)

    for compiled_node in compiled_plan.nodes:
        resources = compiled_node.effective_payload.get("resources")
        if not isinstance(resources, dict):
            continue

        for mount in resources.get("workspace", {}).get("mounts", []):
            ref = mount.get("ref")
            if not isinstance(ref, str):
                raise InvalidDefinitionError(
                    f"Compiled node '{compiled_node.node_key}' has invalid workspace mount ref"
                )
            _resolve_runtime_ref(ref=ref, bindings=bindings, bindings_by_role=bindings_by_role)

        for context_ref in resources.get("context", {}).get("refs", []):
            ref = context_ref.get("ref")
            if not isinstance(ref, str):
                raise InvalidDefinitionError(
                    f"Compiled node '{compiled_node.node_key}' has invalid context ref"
                )
            _resolve_runtime_ref(ref=ref, bindings=bindings, bindings_by_role=bindings_by_role)


async def resolve_manifest_projection_resources(
    session: AsyncSession,
    *,
    task: Task,
    compiled_node: CompiledPlanNode,
) -> tuple[dict[str, Any], ManifestRoot | None]:
    bindings = await _load_task_resource_bindings(session, task_id=task.id)
    bindings_by_role = {binding.binding_role.value: binding for binding in bindings}

    resources = compiled_node.effective_payload.get("resources")
    if not isinstance(resources, dict):
        resources = {}

    resolved: dict[str, Any] = {}
    workspace_mounts = []
    for mount in resources.get("workspace", {}).get("mounts", []):
        ref = mount.get("ref")
        if not isinstance(ref, str):
            continue
        binding = _resolve_runtime_ref(
            ref=ref,
            bindings=bindings,
            bindings_by_role=bindings_by_role,
        )
        workspace_mounts.append(
            _render_resolved_binding(
                binding=binding,
                ref=ref,
                access=cast(str | None, mount.get("access")),
                required=bool(mount.get("required", True)),
            )
        )
    if workspace_mounts:
        resolved["workspace"] = {"mounts": workspace_mounts}

    context_refs = []
    for context_ref in resources.get("context", {}).get("refs", []):
        ref = context_ref.get("ref")
        if not isinstance(ref, str):
            continue
        binding = _resolve_runtime_ref(
            ref=ref,
            bindings=bindings,
            bindings_by_role=bindings_by_role,
        )
        context_refs.append(
            _render_resolved_binding(
                binding=binding,
                ref=ref,
                access=None,
                required=bool(context_ref.get("required", True)),
            )
        )
    if context_refs:
        resolved["context"] = {"refs": context_refs}

    for passthrough_key in ("image", "compose", "container"):
        resource_payload = resources.get(passthrough_key)
        if isinstance(resource_payload, dict):
            resolved[passthrough_key] = deepcopy(resource_payload)

    manifest_root_binding = bindings_by_role.get(TaskResourceBindingRole.MANIFEST_ROOT.value)
    manifest_root = manifest_root_binding.manifest_root if manifest_root_binding else None
    return resolved, manifest_root
