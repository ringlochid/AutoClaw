from __future__ import annotations

import json
import re
from collections.abc import Iterable

from app.core.enums import FlowEdgeKind, FlowNodeState
from app.db.models.runtime import Flow, FlowNode, NodeCheckpoint

_STATUS_EQUALS_RE = re.compile(r'^checkpoint\.status\s*==\s*"([a-z_]+)"$')
_STATUS_IN_RE = re.compile(r"^checkpoint\.status\s+in\s+(\[.*\])$")


def active_nodes(flow: Flow) -> list[FlowNode]:
    if flow.active_flow_revision is None:
        return []
    return list(flow.active_flow_revision.nodes)


def ordered_nodes(flow: Flow) -> list[FlowNode]:
    return sorted(active_nodes(flow), key=lambda node: node.order_index)


def all_nodes_done(flow: Flow) -> bool:
    nodes = active_nodes(flow)
    return bool(nodes) and all(node.state == FlowNodeState.DONE for node in nodes)


def first_running_node(flow: Flow) -> FlowNode | None:
    return next((node for node in ordered_nodes(flow) if node.state == FlowNodeState.RUNNING), None)


def first_ready_node(flow: Flow) -> FlowNode | None:
    return next((node for node in ordered_nodes(flow) if node.state == FlowNodeState.READY), None)


def open_nodes(flow: Flow) -> list[FlowNode]:
    return [
        node
        for node in ordered_nodes(flow)
        if node.state
        in {
            FlowNodeState.READY,
            FlowNodeState.RUNNING,
            FlowNodeState.WAITING,
            FlowNodeState.PAUSED,
        }
    ]


def _latest_checkpoint(node: FlowNode) -> NodeCheckpoint | None:
    if not node.attempts:
        return None
    latest_attempt = node.attempts[-1]
    if not latest_attempt.checkpoints:
        return None
    return latest_attempt.checkpoints[-1]


def _condition_matches(node: FlowNode, condition_expr: str | None) -> bool:
    if condition_expr is None:
        return node.state == FlowNodeState.DONE

    latest_checkpoint = _latest_checkpoint(node)
    if latest_checkpoint is None:
        return False

    match = _STATUS_EQUALS_RE.match(condition_expr)
    if match is not None:
        return latest_checkpoint.status.value == match.group(1)

    match = _STATUS_IN_RE.match(condition_expr)
    if match is not None:
        expected = json.loads(match.group(1))
        return latest_checkpoint.status.value in expected

    return False


def node_dependencies_satisfied(
    flow_node: FlowNode,
    nodes_by_id: dict[str, FlowNode],
) -> bool:
    dependency_edges = [
        edge for edge in flow_node.incoming_edges if edge.edge_kind == FlowEdgeKind.DEPENDENCY
    ]
    control_edges = [
        edge for edge in flow_node.incoming_edges if edge.edge_kind == FlowEdgeKind.CONTROL
    ]

    for edge in dependency_edges:
        predecessor = nodes_by_id.get(str(edge.from_flow_node_id))
        if predecessor is None or predecessor.state != FlowNodeState.DONE:
            return False

    if not control_edges:
        return True

    # Ignore back-edge-like control links when control checks reference future nodes in
    # the current execution order. This keeps initial source nodes runnable even when
    # workflows encode loop-style edges.
    effective_control_edges = []
    for edge in control_edges:
        predecessor = nodes_by_id.get(str(edge.from_flow_node_id))
        if predecessor is None:
            continue
        if predecessor.order_index > flow_node.order_index:
            continue
        effective_control_edges.append((edge, predecessor))

    if not effective_control_edges:
        return True

    for edge, predecessor in effective_control_edges:
        latest_checkpoint = _latest_checkpoint(predecessor)
        if latest_checkpoint is None:
            return False
        if _condition_matches(predecessor, edge.condition_expr):
            return True

    return False


def release_next_unstarted_node(flow: Flow) -> FlowNode | None:
    nodes = ordered_nodes(flow)
    if any(node.state == FlowNodeState.READY for node in nodes):
        return first_ready_node(flow)

    nodes_by_id = {str(node.id): node for node in nodes}
    for node in nodes:
        if (
            node.state == FlowNodeState.WAITING
            and not node.attempts
            and node_dependencies_satisfied(node, nodes_by_id)
        ):
            node.state = FlowNodeState.READY
            return node

    return None


def pause_open_nodes(flow: Flow) -> list[FlowNode]:
    paused: list[FlowNode] = []
    for node in open_nodes(flow):
        node.state = FlowNodeState.PAUSED
        paused.append(node)
    return paused


def restore_paused_nodes(flow: Flow) -> list[FlowNode]:
    restored: list[FlowNode] = []
    nodes_by_id = {str(node.id): node for node in ordered_nodes(flow)}
    for node in ordered_nodes(flow):
        if node.state != FlowNodeState.PAUSED:
            continue
        if node.attempts:
            node.state = FlowNodeState.WAITING
        elif node_dependencies_satisfied(node, nodes_by_id):
            node.state = FlowNodeState.READY
        else:
            node.state = FlowNodeState.WAITING
        restored.append(node)
    return restored


def flow_node_ids(nodes: Iterable[FlowNode]) -> set[str]:
    return {str(node.id) for node in nodes}
