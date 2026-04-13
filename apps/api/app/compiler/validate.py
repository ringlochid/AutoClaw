from app.core.errors import InvalidDefinitionError
from app.schemas.compiler import ResolvedWorkflowDefinition


def validate_resolved_workflow(resolved_workflow: ResolvedWorkflowDefinition) -> None:
    if not resolved_workflow.nodes:
        raise InvalidDefinitionError("Workflow must resolve to at least one node")

    node_keys = [node.node_key for node in resolved_workflow.nodes]
    node_key_set = set(node_keys)
    if len(node_keys) != len(node_key_set):
        raise InvalidDefinitionError("Workflow contains duplicate node keys")

    for node in resolved_workflow.nodes:
        if node.mode not in node.allowed_modes:
            raise InvalidDefinitionError(
                f"Node '{node.node_key}' uses mode '{node.mode}' "
                f"which is not allowed by role '{node.role_key}'"
            )

    seen_edges: set[tuple[str, str, str, str | None]] = set()
    for edge in resolved_workflow.edges:
        if edge.from_node not in node_key_set:
            raise InvalidDefinitionError(f"Edge source '{edge.from_node}' does not exist")
        if edge.to_node not in node_key_set:
            raise InvalidDefinitionError(f"Edge target '{edge.to_node}' does not exist")

        edge_key = (
            edge.from_node,
            edge.to_node,
            edge.edge_kind.value,
            edge.condition_expr,
        )
        if edge_key in seen_edges:
            raise InvalidDefinitionError("Workflow contains duplicate edges")
        seen_edges.add(edge_key)
