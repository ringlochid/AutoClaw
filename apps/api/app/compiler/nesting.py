from __future__ import annotations

from app.schemas.registry import WorkflowNodeSeed


def flatten_workflow_nodes(
    nodes: list[WorkflowNodeSeed],
    *,
    parent_key: str | None = None,
) -> list[WorkflowNodeSeed]:
    flattened: list[WorkflowNodeSeed] = []
    for node in nodes:
        base = node.model_copy(update={"children": []}, deep=True)
        metadata = dict(base.metadata)
        if parent_key is not None:
            metadata["parent_node_key"] = parent_key
        base.metadata = metadata
        flattened.append(base)
        flattened.extend(flatten_workflow_nodes(node.children, parent_key=node.id))
    return flattened
