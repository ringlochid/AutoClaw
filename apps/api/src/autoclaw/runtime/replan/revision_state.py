from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import FlowEdgeModel, FlowModel, FlowNodeModel, FlowRevisionModel
from autoclaw.runtime.errors import illegal_state_error

NodeSnapshot = dict[str, Any]
EdgeSnapshot = dict[str, Any]


async def current_revision_state(
    session: AsyncSession,
    state: Any,
) -> tuple[FlowModel, FlowRevisionModel, list[NodeSnapshot], list[EdgeSnapshot]]:
    flow = state.flow
    revision = await session.get(FlowRevisionModel, flow.active_flow_revision_id)
    if revision is None:
        raise illegal_state_error(f"missing active flow revision '{flow.active_flow_revision_id}'")
    nodes = _node_snapshots_from_models(
        list(
            await session.scalars(
                select(FlowNodeModel)
                .where(FlowNodeModel.flow_revision_id == revision.flow_revision_id)
                .order_by(FlowNodeModel.order_index.asc())
            )
        )
    )
    edges = [
        _edge_snapshot(edge)
        for edge in await session.scalars(
            select(FlowEdgeModel)
            .where(FlowEdgeModel.flow_revision_id == revision.flow_revision_id)
            .order_by(FlowEdgeModel.order_index.asc())
        )
    ]
    return flow, revision, nodes, edges


def _node_snapshot(
    node: FlowNodeModel,
    *,
    parent_node_key: str | None,
    child_node_keys_json: list[str],
) -> NodeSnapshot:
    return {
        "node_key": node.node_key,
        "parent_node_key": parent_node_key,
        "structural_kind": node.structural_kind,
        "role_key": node.role_key,
        "role_revision_no": node.role_revision_no,
        "role_description": node.role_description,
        "role_instruction": node.role_instruction,
        "policy_key": node.policy_key,
        "policy_revision_no": node.policy_revision_no,
        "policy_description": node.policy_description,
        "policy_instruction": node.policy_instruction,
        "description": node.description,
        "child_node_keys_json": child_node_keys_json,
        "consumes_json": node.consumes_json,
        "produces_json": node.produces_json,
        "criteria_json": list(node.criteria_json),
        "child_defaults_json": node.child_defaults_json,
        "current_assignment_id": node.current_assignment_id,
        "order_index": node.order_index,
    }


def _node_snapshots_from_models(nodes: list[FlowNodeModel]) -> list[NodeSnapshot]:
    nodes_by_id = {node.flow_node_id: node for node in nodes}
    children_by_parent_id: defaultdict[str, list[FlowNodeModel]] = defaultdict(list)
    parent_key_by_id: dict[str, str | None] = {}

    for node in nodes:
        if node.parent_flow_node_id is None:
            parent_key_by_id[node.flow_node_id] = None
            continue
        parent = nodes_by_id.get(node.parent_flow_node_id)
        if parent is None:
            raise illegal_state_error(
                "missing relational parent flow node "
                f"'{node.parent_flow_node_id}' for node '{node.node_key}'"
            )
        parent_key_by_id[node.flow_node_id] = parent.node_key
        children_by_parent_id[node.parent_flow_node_id].append(node)

    child_node_keys_by_parent_id = {
        parent_flow_node_id: [
            child.node_key
            for child in sorted(children, key=lambda child: (child.order_index, child.node_key))
        ]
        for parent_flow_node_id, children in children_by_parent_id.items()
    }

    return [
        _node_snapshot(
            node,
            parent_node_key=parent_key_by_id[node.flow_node_id],
            child_node_keys_json=child_node_keys_by_parent_id.get(node.flow_node_id, []),
        )
        for node in nodes
    ]


def _edge_snapshot(edge: FlowEdgeModel) -> EdgeSnapshot:
    return {
        "provider_node_key": edge.provider_node_key,
        "consumer_node_key": edge.consumer_node_key,
        "kind": edge.kind,
        "slot": edge.slot,
        "description": edge.description,
        "order_index": edge.order_index,
    }
