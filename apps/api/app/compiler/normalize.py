from app.core.enums import FlowEdgeKind
from app.schemas.compiler import (
    NormalizedCompiledPlan,
    NormalizedCompiledPlanEdge,
    NormalizedCompiledPlanNode,
    ResolvedWorkflowDefinition,
)


def normalize_resolved_workflow(
    resolved_workflow: ResolvedWorkflowDefinition,
) -> NormalizedCompiledPlan:
    node_order = {node.node_key: index for index, node in enumerate(resolved_workflow.nodes)}

    parent_map: dict[str, str | None] = {}
    for node in resolved_workflow.nodes:
        explicit_parent = node.provenance.get("parent_node_key")
        if isinstance(explicit_parent, str) and explicit_parent:
            parent_map[node.node_key] = explicit_parent
        else:
            parent_map[node.node_key] = None

    for node in resolved_workflow.nodes:
        if parent_map[node.node_key] is not None:
            continue
        incoming_forward_control_edges = sorted(
            (
                edge
                for edge in resolved_workflow.edges
                if edge.edge_kind == FlowEdgeKind.CONTROL
                and edge.to_node == node.node_key
                and node_order[edge.from_node] < node_order[edge.to_node]
            ),
            key=lambda edge: node_order[edge.from_node],
        )
        if incoming_forward_control_edges:
            parent_map[node.node_key] = incoming_forward_control_edges[0].from_node

    normalized_nodes = [
        NormalizedCompiledPlanNode(
            node_key=node.node_key,
            parent_node_key=parent_map[node.node_key],
            role_version_id=node.role_version_id,
            policy_version_id=node.policy_version_id,
            mode=node.mode,
            order_index=node_order[node.node_key],
            skill_bindings=[binding.model_dump(mode="json") for binding in node.skill_bindings],
            effective_payload={
                "node_key": node.node_key,
                "role": {
                    "key": node.role_key,
                    "version_id": str(node.role_version_id),
                },
                "policy": {
                    "key": node.policy_key,
                    "version_id": str(node.policy_version_id),
                },
                "mode": node.mode.value,
                "description": node.description,
                "description_context": node.description_context,
                "task_defaults": resolved_workflow.task_defaults,
                "metadata": node.metadata,
                "resources": node.resources,
                "skill_bindings": [
                    binding.model_dump(mode="json") for binding in node.skill_bindings
                ],
                "provenance": {
                    **node.provenance,
                    "task_defaults": resolved_workflow.task_defaults_provenance,
                },
            },
        )
        for node in resolved_workflow.nodes
    ]

    normalized_edges = [
        NormalizedCompiledPlanEdge(
            from_node=edge.from_node,
            to_node=edge.to_node,
            edge_kind=edge.edge_kind,
            condition_expr=edge.condition_expr,
            order_index=index,
        )
        for index, edge in enumerate(resolved_workflow.edges)
    ]

    return NormalizedCompiledPlan(
        workflow_key=resolved_workflow.workflow_key,
        workflow_version_id=resolved_workflow.workflow_version_id,
        nodes=normalized_nodes,
        edges=normalized_edges,
        source_snapshot={
            **resolved_workflow.source_snapshot,
            "resolved": resolved_workflow.model_dump(mode="json"),
        },
    )
