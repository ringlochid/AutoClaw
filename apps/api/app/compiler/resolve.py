from __future__ import annotations

from collections import OrderedDict
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.compiler.parse import parse_policy_content, parse_role_content, parse_workflow_content
from app.core.enums import SkillBindingState
from app.core.errors import InvalidDefinitionError
from app.db.models.registry import PolicyVersion, RoleVersion, SkillVersion, WorkflowVersion
from app.schemas.compiler import (
    ResolvedSkillBinding,
    ResolvedWorkflowDefinition,
    ResolvedWorkflowEdge,
    ResolvedWorkflowNode,
)
from app.schemas.registry import (
    RoleDefinitionSeed,
    SkillReferenceSeed,
    WorkflowComposeResourceSeed,
    WorkflowContainerResourceSeed,
    WorkflowContextRefSeed,
    WorkflowContextResourcesSeed,
    WorkflowDefaultsSeed,
    WorkflowDefinitionSeed,
    WorkflowImageResourceSeed,
    WorkflowNodeResourcesSeed,
    WorkflowNodeSeed,
    WorkflowTaskDefaultsSeed,
    WorkflowTaskResourceSeed,
    WorkflowWorkspaceMountSeed,
    WorkflowWorkspaceResourcesSeed,
)
from app.services.registry_service import (
    get_published_policy_version,
    get_published_role_version,
    get_published_skill_version,
    get_published_workflow_version,
)


def _skill_ref_identity(skill_ref: SkillReferenceSeed) -> tuple[str, str]:
    return (skill_ref.provider.value, skill_ref.key)


def _merge_skill_refs(
    base_refs: list[SkillReferenceSeed],
    override_refs: list[SkillReferenceSeed],
) -> list[SkillReferenceSeed]:
    merged: OrderedDict[tuple[str, str], SkillReferenceSeed] = OrderedDict()
    for skill_ref in [*base_refs, *override_refs]:
        merged[_skill_ref_identity(skill_ref)] = skill_ref
    return list(merged.values())


def _merge_workflow_defaults(
    base_defaults: WorkflowDefaultsSeed,
    override_defaults: WorkflowDefaultsSeed,
) -> WorkflowDefaultsSeed:
    return WorkflowDefaultsSeed(
        metadata={
            **base_defaults.metadata,
            **override_defaults.metadata,
        },
        skill_refs=_merge_skill_refs(base_defaults.skill_refs, override_defaults.skill_refs),
    )


def _merge_task_resource_seed(
    base_seed: WorkflowTaskResourceSeed,
    override_seed: WorkflowTaskResourceSeed,
) -> WorkflowTaskResourceSeed:
    return WorkflowTaskResourceSeed(
        mode=override_seed.mode,
        auto_create=(
            override_seed.auto_create
            if override_seed.auto_create is not None
            else base_seed.auto_create
        ),
        ref=override_seed.ref if override_seed.ref is not None else base_seed.ref,
        seed_from=(
            override_seed.seed_from
            if override_seed.seed_from is not None
            else base_seed.seed_from
        ),
        read_only=(
            override_seed.read_only
            if override_seed.read_only is not None
            else base_seed.read_only
        ),
        required=(
            override_seed.required if override_seed.required is not None else base_seed.required
        ),
        metadata={
            **base_seed.metadata,
            **override_seed.metadata,
        },
    )


def _merge_task_defaults(
    base_defaults: WorkflowTaskDefaultsSeed,
    override_defaults: WorkflowTaskDefaultsSeed,
) -> WorkflowTaskDefaultsSeed:
    return WorkflowTaskDefaultsSeed(
        workspace=(
            _merge_task_resource_seed(base_defaults.workspace, override_defaults.workspace)
            if base_defaults.workspace is not None and override_defaults.workspace is not None
            else override_defaults.workspace or base_defaults.workspace
        ),
        context=(
            _merge_task_resource_seed(base_defaults.context, override_defaults.context)
            if base_defaults.context is not None and override_defaults.context is not None
            else override_defaults.context or base_defaults.context
        ),
        manifests=(
            _merge_task_resource_seed(base_defaults.manifests, override_defaults.manifests)
            if base_defaults.manifests is not None and override_defaults.manifests is not None
            else override_defaults.manifests or base_defaults.manifests
        ),
    )


def _merge_workspace_mount_seed(
    base_mount: WorkflowWorkspaceMountSeed,
    override_mount: WorkflowWorkspaceMountSeed,
) -> WorkflowWorkspaceMountSeed:
    return WorkflowWorkspaceMountSeed(
        ref=override_mount.ref,
        access=(
            override_mount.access if override_mount.access is not None else base_mount.access
        ),
        required=(
            override_mount.required
            if override_mount.required is not None
            else base_mount.required
        ),
    )


def _merge_context_ref_seed(
    base_ref: WorkflowContextRefSeed,
    override_ref: WorkflowContextRefSeed,
) -> WorkflowContextRefSeed:
    return WorkflowContextRefSeed(
        ref=override_ref.ref,
        required=(
            override_ref.required if override_ref.required is not None else base_ref.required
        ),
    )


def _merge_workspace_mounts(
    base_mounts: list[WorkflowWorkspaceMountSeed],
    override_mounts: list[WorkflowWorkspaceMountSeed],
) -> list[WorkflowWorkspaceMountSeed]:
    merged: OrderedDict[str, WorkflowWorkspaceMountSeed] = OrderedDict(
        (mount.ref, mount) for mount in base_mounts
    )
    for mount in override_mounts:
        existing = merged.get(mount.ref)
        merged[mount.ref] = (
            _merge_workspace_mount_seed(existing, mount) if existing is not None else mount
        )
    return list(merged.values())


def _merge_context_refs(
    base_refs: list[WorkflowContextRefSeed],
    override_refs: list[WorkflowContextRefSeed],
) -> list[WorkflowContextRefSeed]:
    merged: OrderedDict[str, WorkflowContextRefSeed] = OrderedDict(
        (ref.ref, ref) for ref in base_refs
    )
    for ref in override_refs:
        existing = merged.get(ref.ref)
        merged[ref.ref] = _merge_context_ref_seed(existing, ref) if existing is not None else ref
    return list(merged.values())


def _merge_image_resource_seed(
    base_image: WorkflowImageResourceSeed | None,
    override_image: WorkflowImageResourceSeed | None,
) -> WorkflowImageResourceSeed | None:
    if base_image is None:
        return override_image
    if override_image is None:
        return base_image
    return WorkflowImageResourceSeed(
        ref=override_image.ref if override_image.ref is not None else base_image.ref,
        kind=override_image.kind if override_image.kind is not None else base_image.kind,
        required=(
            override_image.required if override_image.required is not None else base_image.required
        ),
        metadata={
            **base_image.metadata,
            **override_image.metadata,
        },
    )


def _merge_compose_resource_seed(
    base_compose: WorkflowComposeResourceSeed | None,
    override_compose: WorkflowComposeResourceSeed | None,
) -> WorkflowComposeResourceSeed | None:
    if base_compose is None:
        return override_compose
    if override_compose is None:
        return base_compose
    services = override_compose.services if override_compose.services else base_compose.services
    return WorkflowComposeResourceSeed(
        ref=override_compose.ref if override_compose.ref is not None else base_compose.ref,
        services=list(services),
        required=(
            override_compose.required
            if override_compose.required is not None
            else base_compose.required
        ),
        metadata={
            **base_compose.metadata,
            **override_compose.metadata,
        },
    )


def _merge_container_resource_seed(
    base_container: WorkflowContainerResourceSeed | None,
    override_container: WorkflowContainerResourceSeed | None,
) -> WorkflowContainerResourceSeed | None:
    if base_container is None:
        return override_container
    if override_container is None:
        return base_container
    return WorkflowContainerResourceSeed(
        ref=(
            override_container.ref if override_container.ref is not None else base_container.ref
        ),
        backend_kind=(
            override_container.backend_kind
            if override_container.backend_kind is not None
            else base_container.backend_kind
        ),
        reuse_policy=(
            override_container.reuse_policy
            if override_container.reuse_policy is not None
            else base_container.reuse_policy
        ),
        required=(
            override_container.required
            if override_container.required is not None
            else base_container.required
        ),
        metadata={
            **base_container.metadata,
            **override_container.metadata,
        },
    )


def _merge_node_resources(
    base_resources: WorkflowNodeResourcesSeed,
    override_resources: WorkflowNodeResourcesSeed,
) -> WorkflowNodeResourcesSeed:
    return WorkflowNodeResourcesSeed(
        workspace=WorkflowWorkspaceResourcesSeed(
            mounts=_merge_workspace_mounts(
                base_resources.workspace.mounts,
                override_resources.workspace.mounts,
            )
        ),
        context=WorkflowContextResourcesSeed(
            refs=_merge_context_refs(
                base_resources.context.refs,
                override_resources.context.refs,
            )
        ),
        image=_merge_image_resource_seed(base_resources.image, override_resources.image),
        compose=_merge_compose_resource_seed(base_resources.compose, override_resources.compose),
        container=_merge_container_resource_seed(
            base_resources.container,
            override_resources.container,
        ),
    )


def _merge_workflow_node_seed(
    base_node: WorkflowNodeSeed,
    override_node: WorkflowNodeSeed,
) -> WorkflowNodeSeed:
    return WorkflowNodeSeed(
        id=override_node.id,
        role=override_node.role,
        mode=override_node.mode,
        policy=(override_node.policy if override_node.policy is not None else base_node.policy),
        description=(
            override_node.description
            if override_node.description is not None
            else base_node.description
        ),
        metadata={
            **base_node.metadata,
            **override_node.metadata,
        },
        resources=_merge_node_resources(base_node.resources, override_node.resources),
        skill_refs=_merge_skill_refs(base_node.skill_refs, override_node.skill_refs),
    )


def _merge_workflow_nodes(
    base_nodes: list[WorkflowNodeSeed],
    override_nodes: list[WorkflowNodeSeed],
) -> list[WorkflowNodeSeed]:
    merged_nodes: OrderedDict[str, WorkflowNodeSeed] = OrderedDict(
        (node.id, node) for node in base_nodes
    )
    for node in override_nodes:
        existing = merged_nodes.get(node.id)
        merged_nodes[node.id] = (
            _merge_workflow_node_seed(existing, node) if existing is not None else node
        )
    return list(merged_nodes.values())


def _edge_identity(edge: Any) -> tuple[str, str, str, str | None]:
    return (edge.from_node, edge.to_node, edge.kind.value, edge.when)


def _merge_workflow_edges(
    base_edges: list[Any],
    override_edges: list[Any],
) -> list[Any]:
    merged_edges: OrderedDict[tuple[str, str, str, str | None], Any] = OrderedDict()
    for edge in [*base_edges, *override_edges]:
        merged_edges[_edge_identity(edge)] = edge
    return list(merged_edges.values())


def _merge_workflow_seeds(
    base_seed: WorkflowDefinitionSeed,
    override_seed: WorkflowDefinitionSeed,
) -> WorkflowDefinitionSeed:
    return WorkflowDefinitionSeed(
        id=override_seed.id,
        description=override_seed.description or base_seed.description,
        extends=override_seed.extends,
        policy=override_seed.policy if override_seed.policy is not None else base_seed.policy,
        defaults=_merge_workflow_defaults(base_seed.defaults, override_seed.defaults),
        task_defaults=_merge_task_defaults(base_seed.task_defaults, override_seed.task_defaults),
        nodes=_merge_workflow_nodes(base_seed.nodes, override_seed.nodes),
        edges=_merge_workflow_edges(base_seed.edges, override_seed.edges),
        skill_refs=_merge_skill_refs(base_seed.skill_refs, override_seed.skill_refs),
    )


async def _resolve_workflow_seed(
    session: AsyncSession,
    workflow_key: str,
) -> tuple[WorkflowVersion, WorkflowDefinitionSeed]:
    workflow_version = await get_published_workflow_version(session, workflow_key)
    workflow_seed = parse_workflow_content(workflow_version.content)

    if workflow_seed.extends:
        _base_version, base_seed = await _resolve_workflow_seed(session, workflow_seed.extends)
        return workflow_version, _merge_workflow_seeds(base_seed, workflow_seed)

    return workflow_version, workflow_seed


def _workflow_default_skill_refs(workflow_seed: WorkflowDefinitionSeed) -> list[SkillReferenceSeed]:
    return _merge_skill_refs(workflow_seed.defaults.skill_refs, workflow_seed.skill_refs)


async def _resolve_role_version(
    session: AsyncSession,
    role_key: str,
    cache: dict[str, tuple[RoleVersion, RoleDefinitionSeed]],
) -> tuple[RoleVersion, RoleDefinitionSeed]:
    cached = cache.get(role_key)
    if cached is not None:
        return cached
    role_version = await get_published_role_version(session, role_key)
    role_seed = parse_role_content(role_version.content)
    cache[role_key] = (role_version, role_seed)
    return role_version, role_seed


async def _resolve_policy_version(
    session: AsyncSession,
    policy_key: str,
    cache: dict[str, tuple[PolicyVersion, Any]],
) -> tuple[PolicyVersion, Any]:
    cached = cache.get(policy_key)
    if cached is not None:
        return cached
    policy_version = await get_published_policy_version(session, policy_key)
    policy_seed = parse_policy_content(policy_version.content)
    cache[policy_key] = (policy_version, policy_seed)
    return policy_version, policy_seed


async def _resolve_skill_version(
    session: AsyncSession,
    skill_ref: SkillReferenceSeed,
    cache: dict[tuple[str, str, str | None], SkillVersion],
) -> SkillVersion:
    cache_key = (skill_ref.provider.value, skill_ref.key, skill_ref.version)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    skill_version = await get_published_skill_version(
        session,
        provider=skill_ref.provider,
        key=skill_ref.key,
        version_label=skill_ref.version,
    )
    cache[cache_key] = skill_version
    return skill_version


def _merge_metadata(
    *,
    role_key: str,
    role_version_id: Any,
    workflow_key: str,
    workflow_version_id: Any,
    node: WorkflowNodeSeed,
    role_defaults: dict[str, Any],
    workflow_defaults: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    layers = [
        ("role", role_defaults, role_key, role_version_id),
        ("workflow", workflow_defaults, workflow_key, workflow_version_id),
        ("node", node.metadata, node.id, None),
    ]
    for layer, values, definition_key, version_id in layers:
        for key, value in values.items():
            metadata[key] = value
            provenance[key] = {
                "layer": layer,
                "definition_key": definition_key,
                "version_id": str(version_id) if version_id is not None else None,
            }
    return metadata, provenance


def _effective_auto_create(seed: WorkflowTaskResourceSeed) -> bool | None:
    if seed.auto_create is not None:
        return seed.auto_create
    if seed.mode.value in {"ensure_task_primary", "ensure_task_root", "seed_from"}:
        return True
    return None


_TASK_DEFAULT_ROLE_BY_SLOT = {
    "workspace": "primary_workspace",
    "context": "primary_context",
    "manifests": "manifest_root",
}


def _normalize_task_defaults(
    workflow_seed: WorkflowDefinitionSeed,
    *,
    workflow_version_id: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    for slot in ("workspace", "context", "manifests"):
        seed = getattr(workflow_seed.task_defaults, slot)
        if seed is None:
            continue

        binding: dict[str, Any] = {
            "binding_role": _TASK_DEFAULT_ROLE_BY_SLOT[slot],
            "mode": seed.mode.value,
            "required": True if seed.required is None else seed.required,
            "metadata": dict(seed.metadata),
        }
        auto_create = _effective_auto_create(seed)
        if auto_create is not None:
            binding["auto_create"] = auto_create
        if seed.ref is not None:
            binding["ref"] = seed.ref
        if seed.seed_from:
            binding["seed_from"] = list(seed.seed_from)
        if seed.read_only is not None:
            binding["read_only"] = seed.read_only

        resolved[slot] = binding
        provenance[slot] = {
            "layer": "workflow",
            "definition_key": workflow_seed.id,
            "version_id": str(workflow_version_id),
        }
    return resolved, provenance


def _normalize_node_resources(node: WorkflowNodeSeed) -> tuple[dict[str, Any], dict[str, Any]]:
    workspace_mounts = [
        {
            "ref": mount.ref,
            "access": mount.access or "read_only",
            "required": True if mount.required is None else mount.required,
        }
        for mount in node.resources.workspace.mounts
    ]
    context_refs = [
        {
            "ref": ref.ref,
            "required": True if ref.required is None else ref.required,
        }
        for ref in node.resources.context.refs
    ]

    resources: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    if workspace_mounts:
        resources["workspace"] = {"mounts": workspace_mounts}
        provenance["workspace"] = {"layer": "node", "definition_key": node.id}
    if context_refs:
        resources["context"] = {"refs": context_refs}
        provenance["context"] = {"layer": "node", "definition_key": node.id}

    if node.resources.image is not None:
        image_resource: dict[str, Any] = {
            "required": (
                True if node.resources.image.required is None else node.resources.image.required
            )
        }
        if node.resources.image.ref is not None:
            image_resource["ref"] = node.resources.image.ref
        if node.resources.image.kind is not None:
            image_resource["kind"] = node.resources.image.kind
        if node.resources.image.metadata:
            image_resource["metadata"] = dict(node.resources.image.metadata)
        if len(image_resource) > 1 or node.resources.image.required is not None:
            resources["image"] = image_resource
            provenance["image"] = {"layer": "node", "definition_key": node.id}

    if node.resources.compose is not None:
        compose_resource: dict[str, Any] = {
            "required": (
                True
                if node.resources.compose.required is None
                else node.resources.compose.required
            )
        }
        if node.resources.compose.ref is not None:
            compose_resource["ref"] = node.resources.compose.ref
        if node.resources.compose.services:
            compose_resource["services"] = list(node.resources.compose.services)
        if node.resources.compose.metadata:
            compose_resource["metadata"] = dict(node.resources.compose.metadata)
        if len(compose_resource) > 1 or node.resources.compose.required is not None:
            resources["compose"] = compose_resource
            provenance["compose"] = {"layer": "node", "definition_key": node.id}

    if node.resources.container is not None:
        container_resource: dict[str, Any] = {
            "required": (
                True
                if node.resources.container.required is None
                else node.resources.container.required
            )
        }
        if node.resources.container.ref is not None:
            container_resource["ref"] = node.resources.container.ref
        if node.resources.container.backend_kind is not None:
            container_resource["backend_kind"] = node.resources.container.backend_kind
        if node.resources.container.reuse_policy is not None:
            container_resource["reuse_policy"] = node.resources.container.reuse_policy
        if node.resources.container.metadata:
            container_resource["metadata"] = dict(node.resources.container.metadata)
        if len(container_resource) > 1 or node.resources.container.required is not None:
            resources["container"] = container_resource
            provenance["container"] = {"layer": "node", "definition_key": node.id}
    return resources, provenance


def _effective_description(
    workflow_description: str | None,
    role_description: str | None,
    policy_description: str | None,
    node_description: str | None,
) -> tuple[str | None, dict[str, str | None], dict[str, Any]]:
    description = node_description or role_description or workflow_description
    if node_description is not None:
        layer = "node"
        definition_key = None
    elif role_description is not None:
        layer = "role"
        definition_key = None
    elif workflow_description is not None:
        layer = "workflow"
        definition_key = None
    else:
        layer = "policy" if policy_description is not None else "workflow"
        definition_key = None
    return (
        description,
        {
            "workflow": workflow_description,
            "role": role_description,
            "policy": policy_description,
            "node": node_description,
        },
        {
            "layer": layer,
            "definition_key": definition_key,
        },
    )


def _validate_layer_skill_declarations(
    *,
    node_key: str,
    declarations: list[tuple[str, SkillReferenceSeed]],
) -> None:
    per_layer: dict[str, set[tuple[str, str | None, str | None]]] = {}
    for layer, skill_ref in declarations:
        per_layer.setdefault(layer, set()).add(
            (
                skill_ref.state.value,
                skill_ref.version,
                skill_ref.source_uri,
            )
        )
    for layer, variants in per_layer.items():
        if len(variants) > 1:
            raise InvalidDefinitionError(
                f"Node '{node_key}' has ambiguous skill declarations in layer '{layer}'"
            )


async def _resolve_node_skill_bindings(
    session: AsyncSession,
    *,
    workflow_key: str,
    workflow_version_id: Any,
    role_key: str,
    role_version_id: Any,
    node: WorkflowNodeSeed,
    role_skill_refs: list[SkillReferenceSeed],
    workflow_skill_refs: list[SkillReferenceSeed],
    skill_cache: dict[tuple[str, str, str | None], SkillVersion],
) -> tuple[list[ResolvedSkillBinding], dict[str, Any]]:
    layered_refs = [
        ("role", role_skill_refs, role_key, role_version_id),
        ("workflow", workflow_skill_refs, workflow_key, workflow_version_id),
        ("node", node.skill_refs, node.id, None),
    ]

    declarations_by_skill: OrderedDict[
        tuple[str, str],
        list[tuple[str, str, Any, SkillReferenceSeed]],
    ] = OrderedDict()
    for layer, refs, definition_key, version_id in layered_refs:
        for skill_ref in refs:
            declarations_by_skill.setdefault((skill_ref.provider.value, skill_ref.key), []).append(
                (layer, definition_key, version_id, skill_ref)
            )

    bindings: list[ResolvedSkillBinding] = []
    provenance: dict[str, Any] = {}
    for (provider, key), declarations in declarations_by_skill.items():
        _validate_layer_skill_declarations(
            node_key=node.id,
            declarations=[
                (layer, skill_ref)
                for layer, _definition_key, _version_id, skill_ref in declarations
            ],
        )
        states = {
            skill_ref.state for _layer, _definition_key, _version_id, skill_ref in declarations
        }
        if SkillBindingState.REQUIRED in states and SkillBindingState.BLOCKED in states:
            raise InvalidDefinitionError(
                "Node "
                f"'{node.id}' has conflicting required/blocked skill refs for "
                f"'{provider}:{key}'"
            )

        effective_layer, definition_key, version_id, effective_ref = declarations[-1]
        skill_version = await _resolve_skill_version(session, effective_ref, skill_cache)
        runtime_name = skill_version.manifest.get("runtime_name")
        if not isinstance(runtime_name, str) or not runtime_name:
            runtime_name = f"{provider}:{key}"
        manifest_summary = {
            "provider": provider,
            "key": key,
            "version_label": skill_version.version_label,
            "state": effective_ref.state.value,
            "manifest_keys": sorted(skill_version.manifest.keys()),
        }
        artifact_metadata = {
            "source_ref": skill_version.source_ref,
            "source_uri": effective_ref.source_uri,
            "requested_version": effective_ref.version,
        }
        binding = ResolvedSkillBinding(
            provider=provider,
            key=key,
            version_label=skill_version.version_label,
            skill_version_id=skill_version.id,
            source_ref=skill_version.source_ref,
            runtime_name=runtime_name,
            manifest=skill_version.manifest,
            manifest_summary=manifest_summary,
            artifact_metadata=artifact_metadata,
            state=effective_ref.state,
            provenance={
                "effective_layer": effective_layer,
                "layers": [
                    {
                        "layer": layer,
                        "definition_key": decl_definition_key,
                        "version_id": str(decl_version_id) if decl_version_id is not None else None,
                        "requested_version": skill_ref.version,
                        "requested_state": skill_ref.state.value,
                        "source_uri": skill_ref.source_uri,
                    }
                    for layer, decl_definition_key, decl_version_id, skill_ref in declarations
                ],
                "effective_definition_key": definition_key,
                "effective_definition_version_id": (
                    str(version_id) if version_id is not None else None
                ),
            },
        )
        bindings.append(binding)
        provenance[f"{provider}:{key}"] = binding.provenance

    return bindings, provenance


async def resolve_workflow_seed_content(
    session: AsyncSession,
    workflow_seed: WorkflowDefinitionSeed,
    *,
    workflow_version_id: UUID | None = None,
    source_snapshot: dict[str, Any] | None = None,
) -> ResolvedWorkflowDefinition:
    effective_workflow_version_id = workflow_version_id or uuid5(
        NAMESPACE_URL,
        f"draft-workflow:{workflow_seed.id}",
    )

    role_cache: dict[str, tuple[RoleVersion, RoleDefinitionSeed]] = {}
    policy_cache: dict[str, tuple[PolicyVersion, Any]] = {}
    skill_cache: dict[tuple[str, str, str | None], SkillVersion] = {}

    resolved_nodes: list[ResolvedWorkflowNode] = []
    unique_skill_bindings: OrderedDict[tuple[str, str, str, str], ResolvedSkillBinding] = (
        OrderedDict()
    )
    workflow_skill_refs = _workflow_default_skill_refs(workflow_seed)
    resolved_task_defaults, task_defaults_provenance = _normalize_task_defaults(
        workflow_seed,
        workflow_version_id=effective_workflow_version_id,
    )

    for node in workflow_seed.nodes:
        role_version, role_seed = await _resolve_role_version(session, node.role, role_cache)

        effective_policy_key = node.policy or workflow_seed.policy or role_seed.default_policy
        if effective_policy_key is None:
            raise InvalidDefinitionError(f"No policy could be resolved for node '{node.id}'")

        policy_version, policy_seed = await _resolve_policy_version(
            session,
            effective_policy_key,
            policy_cache,
        )

        metadata, metadata_provenance = _merge_metadata(
            role_key=node.role,
            role_version_id=role_version.id,
            workflow_key=workflow_seed.id,
            workflow_version_id=effective_workflow_version_id,
            node=node,
            role_defaults=role_seed.defaults,
            workflow_defaults=workflow_seed.defaults.metadata,
        )
        description, description_context, description_provenance = _effective_description(
            workflow_seed.description,
            role_seed.description,
            policy_seed.description,
            node.description,
        )
        resources, resources_provenance = _normalize_node_resources(node)
        skill_bindings, skill_provenance = await _resolve_node_skill_bindings(
            session,
            workflow_key=workflow_seed.id,
            workflow_version_id=effective_workflow_version_id,
            role_key=node.role,
            role_version_id=role_version.id,
            node=node,
            role_skill_refs=role_seed.skill_refs,
            workflow_skill_refs=workflow_skill_refs,
            skill_cache=skill_cache,
        )
        for binding in skill_bindings:
            unique_skill_bindings[
                (
                    binding.provider,
                    binding.key,
                    binding.version_label,
                    binding.state.value,
                )
            ] = binding

        if node.policy is not None:
            policy_layer = "node"
        elif workflow_seed.policy is not None:
            policy_layer = "workflow"
        else:
            policy_layer = "role"

        resolved_nodes.append(
            ResolvedWorkflowNode(
                node_key=node.id,
                role_key=node.role,
                role_version_id=role_version.id,
                policy_key=effective_policy_key,
                policy_version_id=policy_version.id,
                mode=node.mode,
                allowed_modes=role_seed.allowed_modes,
                description=description,
                description_context=description_context,
                metadata=metadata,
                resources=resources,
                skill_bindings=skill_bindings,
                provenance={
                    "role": {
                        "layer": "role",
                        "definition_key": node.role,
                        "version_id": str(role_version.id),
                    },
                    "policy": {
                        "layer": policy_layer,
                        "definition_key": effective_policy_key,
                        "version_id": str(policy_version.id),
                    },
                    "mode": {
                        "layer": "node",
                        "definition_key": node.id,
                    },
                    "description": description_provenance,
                    "metadata": metadata_provenance,
                    "resources": resources_provenance,
                    "skills": skill_provenance,
                },
            )
        )

    resolved_edges = [
        ResolvedWorkflowEdge(
            from_node=edge.from_node,
            to_node=edge.to_node,
            condition_expr=edge.when,
            edge_kind=edge.kind,
        )
        for edge in workflow_seed.edges
    ]

    return ResolvedWorkflowDefinition(
        workflow_key=workflow_seed.id,
        workflow_version_id=effective_workflow_version_id,
        description=workflow_seed.description,
        workflow_policy_key=workflow_seed.policy,
        task_defaults=resolved_task_defaults,
        task_defaults_provenance=task_defaults_provenance,
        nodes=resolved_nodes,
        edges=resolved_edges,
        skill_bindings=list(unique_skill_bindings.values()),
        source_snapshot={
            "workflow": workflow_seed.model_dump(mode="json", by_alias=True),
            "workflow_version_id": str(effective_workflow_version_id),
            **(source_snapshot or {}),
            "resolved": {
                "nodes": [node.model_dump(mode="json") for node in resolved_nodes],
                "edges": [edge.model_dump(mode="json") for edge in resolved_edges],
            },
        },
    )


async def resolve_workflow_definition(
    session: AsyncSession,
    workflow_key: str,
) -> ResolvedWorkflowDefinition:
    workflow_version, workflow_seed = await _resolve_workflow_seed(session, workflow_key)
    return await resolve_workflow_seed_content(
        session,
        workflow_seed,
        workflow_version_id=workflow_version.id,
        source_snapshot={"published_workflow_version_id": str(workflow_version.id)},
    )
