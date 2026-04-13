from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.compiler.parse import parse_policy_content, parse_role_content, parse_workflow_content
from app.db.models.registry import WorkflowVersion
from app.schemas.compiler import (
    ResolvedSkillBinding,
    ResolvedWorkflowDefinition,
    ResolvedWorkflowEdge,
    ResolvedWorkflowNode,
)
from app.schemas.registry import SkillReferenceSeed, WorkflowDefinitionSeed
from app.services.registry_service import (
    get_published_policy_version,
    get_published_role_version,
    get_published_skill_version,
    get_published_workflow_version,
)


def _merge_workflow_seeds(
    base_seed: WorkflowDefinitionSeed,
    override_seed: WorkflowDefinitionSeed,
) -> WorkflowDefinitionSeed:
    return WorkflowDefinitionSeed(
        id=override_seed.id,
        description=override_seed.description or base_seed.description,
        extends=override_seed.extends,
        policy=override_seed.policy if override_seed.policy is not None else base_seed.policy,
        nodes=override_seed.nodes if override_seed.nodes else base_seed.nodes,
        edges=override_seed.edges if override_seed.edges else base_seed.edges,
        skill_refs=override_seed.skill_refs if override_seed.skill_refs else base_seed.skill_refs,
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


async def _resolve_skill_bindings(
    session: AsyncSession,
    skill_refs: list[SkillReferenceSeed],
) -> list[ResolvedSkillBinding]:
    bindings: list[ResolvedSkillBinding] = []
    for skill_ref in skill_refs:
        skill_version = await get_published_skill_version(
            session,
            provider=skill_ref.provider,
            key=skill_ref.key,
            version_label=skill_ref.version,
        )
        bindings.append(
            ResolvedSkillBinding(
                provider=skill_ref.provider.value,
                key=skill_ref.key,
                version_label=skill_version.version_label,
                skill_version_id=skill_version.id,
                source_ref=skill_version.source_ref,
                manifest=skill_version.manifest,
            )
        )
    return bindings


async def resolve_workflow_definition(
    session: AsyncSession,
    workflow_key: str,
) -> ResolvedWorkflowDefinition:
    workflow_version, workflow_seed = await _resolve_workflow_seed(session, workflow_key)
    skill_bindings = await _resolve_skill_bindings(session, workflow_seed.skill_refs)

    resolved_nodes: list[ResolvedWorkflowNode] = []
    for node in workflow_seed.nodes:
        role_version = await get_published_role_version(session, node.role)
        role_seed = parse_role_content(role_version.content)

        effective_policy_key = node.policy or workflow_seed.policy or role_seed.default_policy
        if effective_policy_key is None:
            raise ValueError(f"No policy could be resolved for node '{node.id}'")

        policy_version = await get_published_policy_version(session, effective_policy_key)
        parse_policy_content(policy_version.content)

        resolved_nodes.append(
            ResolvedWorkflowNode(
                node_key=node.id,
                role_key=node.role,
                role_version_id=role_version.id,
                policy_key=effective_policy_key,
                policy_version_id=policy_version.id,
                mode=node.mode,
                allowed_modes=role_seed.allowed_modes,
                metadata=node.metadata,
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
        workflow_version_id=workflow_version.id,
        description=workflow_seed.description,
        workflow_policy_key=workflow_seed.policy,
        nodes=resolved_nodes,
        edges=resolved_edges,
        skill_bindings=skill_bindings,
        source_snapshot={
            "workflow": workflow_seed.model_dump(mode="json", by_alias=True),
            "workflow_version_id": str(workflow_version.id),
        },
    )
