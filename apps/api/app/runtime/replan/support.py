from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AssignmentModel,
    AttemptModel,
    DispatchTurnModel,
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
    NodePlanRevisionModel,
)
from app.runtime.ids import flow_edge_id, flow_node_id, flow_revision_id, node_plan_revision_id
from app.runtime.projection import load_task_root_paths
from app.runtime.resources import criteria_file_path

NodeSnapshot = dict[str, Any]
EdgeSnapshot = dict[str, Any]


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
            raise ValueError(
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


def _validated_child_default_criteria_slots(parent: NodeSnapshot) -> tuple[str, ...]:
    child_defaults = parent.get("child_defaults_json")
    if not isinstance(child_defaults, dict):
        return ()
    criteria_defaults = list(child_defaults.get("criteria", []))
    if not criteria_defaults:
        return ()
    criteria_by_slot = {
        str(criteria["slot"]): dict(criteria) for criteria in parent.get("criteria_json", [])
    }
    validated_slots: list[str] = []
    seen_slots: set[str] = set()
    for slot in criteria_defaults:
        slot_key = str(slot)
        if slot_key in seen_slots:
            continue
        if slot_key not in criteria_by_slot:
            raise ValueError(
                "child_defaults.criteria on node "
                f"'{parent['node_key']}' references unknown local criteria slot '{slot_key}'"
            )
        seen_slots.add(slot_key)
        validated_slots.append(slot_key)
    return tuple(validated_slots)


def _remove_child_defaults(parent: NodeSnapshot, child: NodeSnapshot) -> None:
    inherited_criteria_slots = set(_validated_child_default_criteria_slots(parent))
    if inherited_criteria_slots:
        child["criteria_json"] = [
            dict(criteria)
            for criteria in child["criteria_json"]
            if str(criteria["slot"]) not in inherited_criteria_slots
        ]

    child_defaults = parent.get("child_defaults_json")
    if not isinstance(child_defaults, dict):
        return
    consumes_defaults = child_defaults.get("consumes")
    if not isinstance(consumes_defaults, dict):
        return
    local_consumes = child.get("consumes_json") or {}
    default_artifact_slots = {
        str(selector["slot"]) for selector in consumes_defaults.get("artifacts") or []
    }
    default_criteria_slots = {
        str(selector["slot"]) for selector in consumes_defaults.get("criteria") or []
    }
    cleaned_consumes = {
        "artifacts": [
            dict(selector)
            for selector in local_consumes.get("artifacts") or []
            if str(selector["slot"]) not in default_artifact_slots
        ]
        or None,
        "criteria": [
            dict(selector)
            for selector in local_consumes.get("criteria") or []
            if str(selector["slot"]) not in default_criteria_slots
        ]
        or None,
    }
    child["consumes_json"] = (
        cleaned_consumes
        if cleaned_consumes["artifacts"] is not None or cleaned_consumes["criteria"] is not None
        else None
    )


def _apply_child_defaults(parent: NodeSnapshot, child: NodeSnapshot) -> None:
    child_defaults = parent.get("child_defaults_json")
    if not isinstance(child_defaults, dict):
        return
    _remove_child_defaults(parent, child)
    criteria_defaults = _validated_child_default_criteria_slots(parent)
    if criteria_defaults:
        criteria_by_slot = {
            str(criteria["slot"]): dict(criteria) for criteria in parent.get("criteria_json", [])
        }
        local_criteria = [dict(criteria) for criteria in child["criteria_json"]]
        child["criteria_json"] = [
            criteria_by_slot[slot] for slot in criteria_defaults
        ] + local_criteria

    consumes_defaults = child_defaults.get("consumes")
    if isinstance(consumes_defaults, dict):
        local_consumes = child.get("consumes_json") or {}
        merged_artifacts = _merge_consume_selectors(
            consumes_defaults.get("artifacts") or [],
            local_consumes.get("artifacts") or [],
        )
        merged_criteria = _merge_consume_selectors(
            consumes_defaults.get("criteria") or [],
            local_consumes.get("criteria") or [],
        )
        if merged_artifacts or merged_criteria:
            child["consumes_json"] = {
                "artifacts": merged_artifacts or None,
                "criteria": merged_criteria or None,
            }
        else:
            child["consumes_json"] = None


def _refresh_descendant_defaults(
    nodes: list[NodeSnapshot],
    *,
    previous_parent: NodeSnapshot,
    updated_parent: NodeSnapshot,
) -> None:
    nodes_by_key = {str(node["node_key"]): node for node in nodes}
    children_by_parent: defaultdict[str, list[NodeSnapshot]] = defaultdict(list)
    for node in nodes:
        parent_node_key = node.get("parent_node_key")
        if parent_node_key is not None:
            children_by_parent[str(parent_node_key)].append(node)

    queue: deque[str] = deque()
    for child in children_by_parent.get(str(updated_parent["node_key"]), []):
        _remove_child_defaults(previous_parent, child)
        _apply_child_defaults(updated_parent, child)
        queue.append(str(child["node_key"]))

    while queue:
        parent_node_key = queue.popleft()
        parent_node = nodes_by_key[parent_node_key]
        for child in children_by_parent.get(parent_node_key, []):
            _apply_child_defaults(parent_node, child)
            queue.append(str(child["node_key"]))


def _merge_consume_selectors(
    default_selectors: list[dict[str, object]],
    local_selectors: list[dict[str, object]],
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    index_by_slot: dict[str, int] = {}

    for selector in default_selectors:
        slot = str(selector["slot"])
        if slot in index_by_slot:
            continue
        index_by_slot[slot] = len(merged)
        merged.append(dict(selector))

    for selector in local_selectors:
        slot = str(selector["slot"])
        if slot in index_by_slot:
            merged[index_by_slot[slot]] = dict(selector)
            continue
        index_by_slot[slot] = len(merged)
        merged.append(dict(selector))

    return merged


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


def _rebuild_dependency_edges(nodes: list[NodeSnapshot]) -> list[EdgeSnapshot]:
    artifact_slots: dict[str, tuple[str, str]] = {}
    criteria_slots: dict[str, tuple[str, dict[str, object]]] = {}
    nodes_by_key = {str(node["node_key"]): node for node in nodes}
    for node in nodes:
        produces_json = node.get("produces_json") or {}
        for artifact in produces_json.get("artifacts") or []:
            slot = str(artifact["slot"])
            if slot in artifact_slots:
                owner = artifact_slots[slot][0]
                raise ValueError(
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
                raise ValueError(
                    f"duplicate criteria slot '{slot}' on nodes '{owner}' and '{node['node_key']}'"
                )
            criteria_slots[slot] = (
                node["node_key"],
                dict(criteria),
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
            criteria_provider = criteria_slots.get(selector["slot"])
            if criteria_provider is None:
                raise ValueError(f"missing criteria provider for slot '{selector['slot']}'")
            edges.append(
                {
                    "provider_node_key": criteria_provider[0],
                    "consumer_node_key": node["node_key"],
                    "kind": "criteria",
                    "slot": selector["slot"],
                    "description": str(criteria_provider[1]["description"]),
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


def _criteria_signature(criteria: dict[str, object]) -> tuple[str, str, tuple[str, ...]]:
    return (
        str(criteria["slot"]),
        str(criteria["description"]),
        tuple(str(item) for item in cast(list[object], criteria.get("criteria", []))),
    )


def _sync_child_node_key_mirrors(nodes: list[NodeSnapshot]) -> None:
    nodes_by_key = {str(node["node_key"]): node for node in nodes}
    children_by_parent: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)

    for node in nodes:
        node["child_node_keys_json"] = []

    for node in nodes:
        parent_node_key = node.get("parent_node_key")
        if parent_node_key is None:
            continue
        parent_key = str(parent_node_key)
        if parent_key not in nodes_by_key:
            raise ValueError(f"missing parent node '{parent_key}'")
        children_by_parent[parent_key].append((int(node["order_index"]), str(node["node_key"])))

    for parent_key, children in children_by_parent.items():
        nodes_by_key[parent_key]["child_node_keys_json"] = [
            child_node_key for _, child_node_key in sorted(children, key=lambda item: item)
        ]


async def _assign_criteria_versions(
    session: AsyncSession,
    *,
    task_id: str,
    current_revision_id: str,
    nodes: list[NodeSnapshot],
) -> None:
    paths = await load_task_root_paths(session, task_id)
    previous_slots: dict[str, dict[str, object]] = {}
    current_nodes = await session.scalars(
        select(FlowNodeModel).where(FlowNodeModel.flow_revision_id == current_revision_id)
    )
    for current_node in current_nodes:
        for criteria in current_node.criteria_json:
            previous_slots[str(criteria["slot"])] = dict(criteria)
    for node in nodes:
        normalized_criteria: list[dict[str, object]] = []
        for criteria in node["criteria_json"]:
            criteria_payload = dict(criteria)
            slot = str(criteria_payload["slot"])
            previous = previous_slots.get(slot)
            if previous is not None and _criteria_signature(previous) == _criteria_signature(
                criteria_payload
            ):
                version = int(cast(int | str, previous.get("version") or 1))
            elif previous is not None:
                version = int(cast(int | str, previous.get("version") or 1)) + 1
            else:
                version = 1
            criteria_payload["version"] = version
            criteria_payload["path"] = str(
                criteria_file_path(paths=paths, slot=slot, version=version)
            )
            normalized_criteria.append(criteria_payload)
            previous_slots[slot] = criteria_payload
        node["criteria_json"] = normalized_criteria


async def _node_has_open_current_work(
    session: AsyncSession,
    node: NodeSnapshot,
) -> bool:
    current_assignment_id = node.get("current_assignment_id")
    if current_assignment_id is None:
        return False
    assignment = await session.get(AssignmentModel, str(current_assignment_id))
    if assignment is None or assignment.current_attempt_id is None:
        return False
    attempt = await session.get(AttemptModel, assignment.current_attempt_id)
    if attempt is None:
        return False
    return attempt.closed_at is None or attempt.terminal_outcome is None


def _structural_revision_cause(
    current_revision: FlowRevisionModel,
    next_nodes: list[NodeSnapshot],
) -> str:
    snapshot = current_revision.snapshot_json
    current_snapshot_nodes = snapshot.get("nodes") if isinstance(snapshot, dict) else None
    current_node_count = (
        len(current_snapshot_nodes) if isinstance(current_snapshot_nodes, list) else 0
    )
    if len(next_nodes) > current_node_count:
        return "add_child"
    if len(next_nodes) < current_node_count:
        return "remove_child"
    return "update_child"


async def _rebind_current_runtime_lineage(
    session: AsyncSession,
    *,
    flow_id: str,
    next_revision_id: str,
    nodes: list[NodeSnapshot],
    next_flow_node_ids: dict[str, str],
) -> None:
    for node in nodes:
        current_assignment_id = node["current_assignment_id"]
        if current_assignment_id is None:
            continue
        assignment = await session.get(AssignmentModel, str(current_assignment_id))
        if assignment is None:
            raise ValueError(f"missing current assignment '{current_assignment_id}'")
        next_flow_node_id = next_flow_node_ids[str(node["node_key"])]
        assignment.flow_id = flow_id
        assignment.flow_revision_id = next_revision_id
        assignment.flow_node_id = next_flow_node_id

        await session.execute(
            update(AttemptModel)
            .where(AttemptModel.assignment_id == assignment.assignment_id)
            .values(flow_node_id=next_flow_node_id),
            execution_options={"synchronize_session": "fetch"},
        )

        await session.execute(
            update(DispatchTurnModel)
            .where(DispatchTurnModel.assignment_id == assignment.assignment_id)
            .values(
                flow_revision_id=next_revision_id,
                flow_node_id=next_flow_node_id,
            ),
            execution_options={"synchronize_session": "fetch"},
        )


async def _adopt_candidate(
    session: AsyncSession,
    task_id: str,
    flow: FlowModel,
    current_revision: FlowRevisionModel,
    nodes: list[NodeSnapshot],
    edges: list[EdgeSnapshot],
) -> None:
    _sync_child_node_key_mirrors(nodes)
    next_revision_index = int(current_revision.revision_index + 1)
    next_revision_id = flow_revision_id(flow.flow_id, next_revision_index)
    created_by_dispatch_id = flow.current_open_dispatch_id
    if created_by_dispatch_id is None:
        raise ValueError("structural replan requires a current open dispatch")
    next_flow_revision = FlowRevisionModel(
        flow_revision_id=next_revision_id,
        flow_id=flow.flow_id,
        revision_index=next_revision_index,
        parent_flow_revision_id=current_revision.flow_revision_id,
        source_compiled_plan_id=current_revision.source_compiled_plan_id or flow.compiled_plan_id,
        cause=_structural_revision_cause(current_revision, nodes),
        created_by_dispatch_id=created_by_dispatch_id,
        snapshot_json={"nodes": nodes, "edges": edges},
    )
    session.add(next_flow_revision)
    await session.flush()
    await _assign_criteria_versions(
        session,
        task_id=task_id,
        current_revision_id=current_revision.flow_revision_id,
        nodes=nodes,
    )
    historical_nodes = await session.scalars(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == current_revision.flow_revision_id,
            FlowNodeModel.current_assignment_id.is_not(None),
        )
    )
    for historical_node in historical_nodes:
        historical_node.current_assignment_id = None
    next_flow_node_ids: dict[str, str] = {}
    for node in nodes:
        node_key = str(node["node_key"])
        next_flow_node_ids[node_key] = flow_node_id(next_revision_id, node_key)
        next_node = FlowNodeModel(
            flow_node_id=next_flow_node_ids[node_key],
            flow_id=flow.flow_id,
            flow_revision=next_flow_revision,
            node_key=node_key,
            parent_flow_node_id=(
                next_flow_node_ids.get(str(node["parent_node_key"]))
                or flow_node_id(next_revision_id, str(node["parent_node_key"]))
                if node["parent_node_key"] is not None
                else None
            ),
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
        session.add(next_node)
        session.add(
            NodePlanRevisionModel(
                node_plan_revision_id=node_plan_revision_id(next_revision_id, node_key),
                flow_revision=next_flow_revision,
                flow_node=next_node,
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
    await _rebind_current_runtime_lineage(
        session,
        flow_id=flow.flow_id,
        next_revision_id=next_revision_id,
        nodes=nodes,
        next_flow_node_ids=next_flow_node_ids,
    )
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
                provider_flow_node_id=flow_node_id(
                    next_revision_id,
                    str(edge["provider_node_key"]),
                ),
                consumer_flow_node_id=flow_node_id(
                    next_revision_id,
                    str(edge["consumer_node_key"]),
                ),
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
