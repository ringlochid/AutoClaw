from __future__ import annotations

from collections.abc import Iterable

from app.core.enums import FlowNodeState
from app.db.models.runtime import Flow, FlowNode


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
        if node.state in {FlowNodeState.READY, FlowNodeState.RUNNING, FlowNodeState.WAITING}
    ]


def release_next_unstarted_node(flow: Flow) -> FlowNode | None:
    nodes = ordered_nodes(flow)
    if any(node.state == FlowNodeState.READY for node in nodes):
        return first_ready_node(flow)

    for node in nodes:
        if node.state == FlowNodeState.WAITING and not node.attempts:
            node.state = FlowNodeState.READY
            return node

    return None


def pause_open_nodes(flow: Flow) -> list[FlowNode]:
    paused: list[FlowNode] = []
    for node in open_nodes(flow):
        node.state = FlowNodeState.PAUSED
        paused.append(node)
    return paused


def flow_node_ids(nodes: Iterable[FlowNode]) -> set[str]:
    return {str(node.id) for node in nodes}
