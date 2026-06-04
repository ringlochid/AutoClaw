from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from autoclaw.runtime.control.failures import illegal_state_error

NodeSnapshot = dict[str, Any]
EdgeSnapshot = dict[str, Any]


def rebuild_dependency_edges(nodes: list[NodeSnapshot]) -> list[EdgeSnapshot]:
    nodes_by_key = {str(node["node_key"]): node for node in nodes}
    artifact_slots, criteria_slots = _collect_dependency_slots(nodes, nodes_by_key)
    edges = _build_dependency_edges(nodes, artifact_slots, criteria_slots)
    _validate_acyclic_graph(nodes, edges)
    for index, edge in enumerate(edges):
        edge["order_index"] = index
    return edges


def _collect_dependency_slots(
    nodes: list[NodeSnapshot],
    nodes_by_key: dict[str, NodeSnapshot],
) -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, dict[str, object]]]]:
    artifact_slots: dict[str, tuple[str, str]] = {}
    criteria_slots: dict[str, tuple[str, dict[str, object]]] = {}
    for node in nodes:
        produces_json = node.get("produces_json") or {}
        for artifact in produces_json.get("artifacts") or []:
            slot = str(artifact["slot"])
            if slot in artifact_slots:
                owner = artifact_slots[slot][0]
                raise illegal_state_error(
                    f"duplicate artifact slot '{slot}' on nodes '{owner}' and '{node['node_key']}'"
                )
            artifact_slots[slot] = (
                node["node_key"],
                artifact["description"],
            )
        for criteria in node["criteria_json"]:
            slot = str(criteria["slot"])
            if slot in criteria_slots:
                owner, owner_criteria = criteria_slots[slot]
                if (
                    _is_ancestor_node(
                        nodes_by_key,
                        ancestor_node_key=str(owner),
                        descendant_node_key=str(node["node_key"]),
                    )
                    and dict(criteria) == owner_criteria
                ):
                    continue
                raise illegal_state_error(
                    f"duplicate criteria slot '{slot}' on nodes '{owner}' and '{node['node_key']}'"
                )
            criteria_slots[slot] = (
                node["node_key"],
                dict(criteria),
            )
    return artifact_slots, criteria_slots


def _build_dependency_edges(
    nodes: list[NodeSnapshot],
    artifact_slots: dict[str, tuple[str, str]],
    criteria_slots: dict[str, tuple[str, dict[str, object]]],
) -> list[EdgeSnapshot]:
    edges: list[EdgeSnapshot] = []
    for node in nodes:
        consumes_json = node.get("consumes_json") or {}
        for selector in consumes_json.get("artifacts") or []:
            provider = artifact_slots.get(selector["slot"])
            if provider is None:
                raise illegal_state_error(
                    f"missing artifact provider for slot '{selector['slot']}'"
                )
            edges.append(
                {
                    "provider_node_key": provider[0],
                    "consumer_node_key": node["node_key"],
                    "kind": "artifact",
                    "slot": selector["slot"],
                    "description": provider[1],
                }
            )
        for selector in consumes_json.get("criteria") or []:
            criteria_provider = criteria_slots.get(selector["slot"])
            if criteria_provider is None:
                raise illegal_state_error(
                    f"missing criteria provider for slot '{selector['slot']}'"
                )
            edges.append(
                {
                    "provider_node_key": criteria_provider[0],
                    "consumer_node_key": node["node_key"],
                    "kind": "criteria",
                    "slot": selector["slot"],
                    "description": str(criteria_provider[1]["description"]),
                }
            )
    return edges


def _validate_acyclic_graph(nodes: list[NodeSnapshot], edges: list[EdgeSnapshot]) -> None:
    indegree: defaultdict[str, int] = defaultdict(int)
    adjacency: defaultdict[str, list[str]] = defaultdict(list)
    order_index = {node["node_key"]: int(node["order_index"]) for node in nodes}
    for edge in edges:
        indegree[edge["consumer_node_key"]] += 1
        adjacency[edge["provider_node_key"]].append(edge["consumer_node_key"])
    queue = deque(
        sorted(
            [node["node_key"] for node in nodes if indegree[node["node_key"]] == 0],
            key=lambda key: (order_index[key], key),
        )
    )
    emitted: list[str] = []
    while queue:
        node_key = queue.popleft()
        emitted.append(node_key)
        for successor in sorted(adjacency[node_key], key=lambda key: (order_index[key], key)):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if len(emitted) != len(nodes):
        raise illegal_state_error("candidate structural graph is cyclic")


def _is_ancestor_node(
    nodes_by_key: dict[str, NodeSnapshot],
    *,
    ancestor_node_key: str,
    descendant_node_key: str,
) -> bool:
    current_node_key = descendant_node_key
    while True:
        node = nodes_by_key.get(current_node_key)
        if node is None:
            return False
        parent_node_key = node.get("parent_node_key")
        if parent_node_key is None:
            return False
        if parent_node_key == ancestor_node_key:
            return True
        current_node_key = str(parent_node_key)
