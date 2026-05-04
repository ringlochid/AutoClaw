from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
    NodePlanRevisionModel,
)
from app.runtime.ids import flow_edge_id, flow_node_id, flow_revision_id, node_plan_revision_id
from app.runtime.lookup import resolve_policy, resolve_role
from app.schemas.runtime import ChildNodeDraft, ChildNodePatch
from app.schemas.workflow_definitions import NodeKind

NodeSnapshot = dict[str, Any]
EdgeSnapshot = dict[str, Any]


def _node_snapshot(node: FlowNodeModel) -> NodeSnapshot:
    return {
        "node_key": node.node_key,
        "parent_node_key": node.parent_node_key,
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
        "child_node_keys_json": list(node.child_node_keys_json),
        "consumes_json": node.consumes_json,
        "produces_json": node.produces_json,
        "criteria_json": list(node.criteria_json),
        "child_defaults_json": node.child_defaults_json,
        "current_assignment_id": node.current_assignment_id,
        "order_index": node.order_index,
    }


def _edge_snapshot(edge: FlowEdgeModel) -> EdgeSnapshot:
    return {
        "provider_node_key": edge.provider_node_key,
        "consumer_node_key": edge.consumer_node_key,
        "kind": edge.kind,
        "slot": edge.slot,
        "description": edge.description,
        "order_index": edge.order_index,
    }


def _apply_child_defaults(parent: NodeSnapshot, child: NodeSnapshot) -> None:
    child_defaults = parent.get("child_defaults_json")
    if not isinstance(child_defaults, dict):
        return
    criteria_defaults = list(child_defaults.get("criteria", []))
    if criteria_defaults:
        existing = {item["slot"] for item in child["criteria_json"]}
        for slot in criteria_defaults:
            if slot in existing:
                continue
            child["criteria_json"].insert(
                0,
                {
                    "slot": slot,
                    "description": slot,
                    "criteria": [slot],
                },
            )


def _rebuild_dependency_edges(nodes: list[NodeSnapshot]) -> list[EdgeSnapshot]:
    artifact_slots: dict[str, tuple[str, str]] = {}
    criteria_slots: dict[str, tuple[str, str]] = {}
    for node in nodes:
        produces_json = node.get("produces_json") or {}
        for artifact in produces_json.get("artifacts") or []:
            artifact_slots.setdefault(
                artifact["slot"],
                (node["node_key"], artifact["description"]),
            )
        for criteria in node["criteria_json"]:
            criteria_slots.setdefault(
                criteria["slot"],
                (node["node_key"], criteria["description"]),
            )
    edges: list[EdgeSnapshot] = []
    for node in nodes:
        consumes_json = node.get("consumes_json") or {}
        for selector in consumes_json.get("artifacts") or []:
            provider = artifact_slots.get(selector["slot"])
            if provider is None:
                raise ValueError(f"missing artifact provider for slot '{selector['slot']}'")
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
            provider = criteria_slots.get(selector["slot"])
            if provider is None:
                raise ValueError(f"missing criteria provider for slot '{selector['slot']}'")
            edges.append(
                {
                    "provider_node_key": provider[0],
                    "consumer_node_key": node["node_key"],
                    "kind": "criteria",
                    "slot": selector["slot"],
                    "description": provider[1],
                }
            )
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
        raise ValueError("candidate structural graph is cyclic")
    for index, edge in enumerate(edges):
        edge["order_index"] = index
    return edges


async def _adopt_candidate(
    session: AsyncSession,
    task_id: str,
    flow: FlowModel,
    current_revision: FlowRevisionModel,
    nodes: list[NodeSnapshot],
    edges: list[EdgeSnapshot],
) -> None:
    next_revision_index = int(current_revision.revision_index + 1)
    next_revision_id = flow_revision_id(flow.flow_id, next_revision_index)
    session.add(
        FlowRevisionModel(
            flow_revision_id=next_revision_id,
            flow_id=flow.flow_id,
            revision_index=next_revision_index,
            snapshot_json={"nodes": nodes, "edges": edges},
        )
    )
    await session.flush()
    for node in nodes:
        session.add(
            FlowNodeModel(
                flow_node_id=flow_node_id(next_revision_id, str(node["node_key"])),
                flow_revision_id=next_revision_id,
                node_key=str(node["node_key"]),
                parent_node_key=node["parent_node_key"],
                structural_kind=str(node["structural_kind"]),
                role_key=str(node["role_key"]),
                role_revision_no=int(node["role_revision_no"]),
                role_description=str(node["role_description"]),
                role_instruction=node["role_instruction"],
                policy_key=node["policy_key"],
                policy_revision_no=node["policy_revision_no"],
                policy_description=node["policy_description"],
                policy_instruction=node["policy_instruction"],
                description=str(node["description"]),
                child_node_keys_json=list(node["child_node_keys_json"]),
                consumes_json=node["consumes_json"],
                produces_json=node["produces_json"],
                criteria_json=list(node["criteria_json"]),
                child_defaults_json=node["child_defaults_json"],
                current_assignment_id=node["current_assignment_id"],
                order_index=int(node["order_index"]),
            )
        )
        session.add(
            NodePlanRevisionModel(
                node_plan_revision_id=node_plan_revision_id(
                    next_revision_id, str(node["node_key"])
                ),
                flow_revision_id=next_revision_id,
                flow_node_id=flow_node_id(next_revision_id, str(node["node_key"])),
                role_key=str(node["role_key"]),
                role_revision_no=int(node["role_revision_no"]),
                role_description=str(node["role_description"]),
                role_instruction=node["role_instruction"],
                policy_key=node["policy_key"],
                policy_revision_no=node["policy_revision_no"],
                policy_description=node["policy_description"],
                policy_instruction=node["policy_instruction"],
            )
        )
    await session.flush()
    for edge in edges:
        session.add(
            FlowEdgeModel(
                flow_edge_id=flow_edge_id(
                    next_revision_id,
                    str(edge["consumer_node_key"]),
                    str(edge["kind"]),
                    str(edge["slot"]),
                ),
                flow_revision_id=next_revision_id,
                provider_node_key=str(edge["provider_node_key"]),
                consumer_node_key=str(edge["consumer_node_key"]),
                kind=str(edge["kind"]),
                slot=str(edge["slot"]),
                description=str(edge["description"]),
                order_index=int(edge["order_index"]),
            )
        )
    flow.active_flow_revision_id = next_revision_id


async def _current_revision_state(
    session: AsyncSession,
    state: Any,
) -> tuple[FlowModel, FlowRevisionModel, list[NodeSnapshot], list[EdgeSnapshot]]:
    flow = state.flow
    revision = await session.get(FlowRevisionModel, flow.active_flow_revision_id)
    if revision is None:
        raise ValueError(f"missing active flow revision '{flow.active_flow_revision_id}'")
    nodes = [
        _node_snapshot(node)
        for node in await session.scalars(
            select(FlowNodeModel)
            .where(FlowNodeModel.flow_revision_id == revision.flow_revision_id)
            .order_by(FlowNodeModel.order_index.asc())
        )
    ]
    edges = [
        _edge_snapshot(edge)
        for edge in await session.scalars(
            select(FlowEdgeModel)
            .where(FlowEdgeModel.flow_revision_id == revision.flow_revision_id)
            .order_by(FlowEdgeModel.order_index.asc())
        )
    ]
    return flow, revision, nodes, edges


async def add_child_to_current_flow(
    session: AsyncSession,
    task_id: str,
    state: Any,
    child: ChildNodeDraft,
) -> str:
    flow, revision, nodes, _edges = await _current_revision_state(session, state)
    if any(node["node_key"] == child.id for node in nodes):
        raise ValueError(f"node_key '{child.id}' already exists")
    parent = next(node for node in nodes if node["node_key"] == state.current_node.node_key)
    role = resolve_role(child.role)
    policy = resolve_policy(child.policy) if child.policy is not None else None
    candidate = {
        "node_key": child.id,
        "parent_node_key": state.current_node.node_key,
        "structural_kind": NodeKind.PARENT.value if child.children else NodeKind.WORKER.value,
        "role_key": child.role,
        "role_revision_no": role.revision_no,
        "role_description": role.definition.description,
        "role_instruction": role.definition.instruction,
        "policy_key": child.policy,
        "policy_revision_no": policy.revision_no if policy else None,
        "policy_description": policy.definition.description if policy else None,
        "policy_instruction": policy.definition.instruction if policy else None,
        "description": child.description,
        "child_node_keys_json": [grandchild.id for grandchild in child.children or []],
        "consumes_json": child.consumes.model_dump(mode="json") if child.consumes else None,
        "produces_json": child.produces.model_dump(mode="json") if child.produces else None,
        "criteria_json": [criteria.model_dump(mode="json") for criteria in child.criteria or []],
        "child_defaults_json": child.child_defaults.model_dump(mode="json")
        if child.child_defaults
        else None,
        "current_assignment_id": None,
        "order_index": max(int(node["order_index"]) for node in nodes) + 1,
    }
    _apply_child_defaults(parent, candidate)
    parent["child_node_keys_json"].append(child.id)
    nodes.append(candidate)
    edges = _rebuild_dependency_edges(nodes)
    await _adopt_candidate(session, task_id, flow, revision, nodes, edges)
    await session.flush()
    return child.id


async def update_child_in_current_flow(
    session: AsyncSession,
    task_id: str,
    state: Any,
    child_node_key: str,
    patch: ChildNodePatch,
) -> None:
    flow, revision, nodes, _edges = await _current_revision_state(session, state)
    target = next((node for node in nodes if node["node_key"] == child_node_key), None)
    if target is None:
        raise ValueError(f"unknown child node '{child_node_key}'")
    if target["parent_node_key"] != state.current_node.node_key:
        raise ValueError("update_child target must be a direct child")
    if patch.role is not None:
        role = resolve_role(patch.role)
        target["role_key"] = patch.role
        target["role_revision_no"] = role.revision_no
        target["role_description"] = role.definition.description
        target["role_instruction"] = role.definition.instruction
    if patch.policy is not None:
        policy = resolve_policy(patch.policy)
        target["policy_key"] = patch.policy
        target["policy_revision_no"] = policy.revision_no
        target["policy_description"] = policy.definition.description
        target["policy_instruction"] = policy.definition.instruction
    if patch.description is not None:
        target["description"] = patch.description
    if patch.consumes is not None:
        target["consumes_json"] = patch.consumes.model_dump(mode="json")
    if patch.produces is not None:
        target["produces_json"] = patch.produces.model_dump(mode="json")
    if patch.criteria is not None:
        target["criteria_json"] = [criteria.model_dump(mode="json") for criteria in patch.criteria]
    if patch.child_defaults is not None:
        target["child_defaults_json"] = patch.child_defaults.model_dump(mode="json")
    edges = _rebuild_dependency_edges(nodes)
    await _adopt_candidate(session, task_id, flow, revision, nodes, edges)
    await session.flush()


async def remove_child_from_current_flow(
    session: AsyncSession,
    task_id: str,
    state: Any,
    child_node_key: str,
) -> None:
    flow, revision, nodes, _edges = await _current_revision_state(session, state)
    target = next((node for node in nodes if node["node_key"] == child_node_key), None)
    if target is None:
        raise ValueError(f"unknown child node '{child_node_key}'")
    if target["parent_node_key"] != state.current_node.node_key:
        raise ValueError("remove_child target must be a direct child")
    if target["current_assignment_id"] is not None:
        raise ValueError("remove_child cannot delete a node with current assignment lineage")
    parent = next(node for node in nodes if node["node_key"] == state.current_node.node_key)
    parent["child_node_keys_json"] = [
        key for key in parent["child_node_keys_json"] if key != child_node_key
    ]
    descendants = {child_node_key}
    changed = True
    while changed:
        changed = False
        for node in nodes:
            if node["parent_node_key"] in descendants and node["node_key"] not in descendants:
                descendants.add(node["node_key"])
                changed = True
    nodes = [node for node in nodes if node["node_key"] not in descendants]
    edges = _rebuild_dependency_edges(nodes)
    await _adopt_candidate(session, task_id, flow, revision, nodes, edges)
    await session.flush()
