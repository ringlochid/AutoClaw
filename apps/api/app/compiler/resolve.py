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
    WorkflowDefaultsSeed,
    WorkflowDefinitionSeed,
    WorkflowNodeSeed,
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
        binding = ResolvedSkillBinding(
            provider=provider,
            key=key,
            version_label=skill_version.version_label,
            skill_version_id=skill_version.id,
            source_ref=skill_version.source_ref,
            manifest=skill_version.manifest,
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
