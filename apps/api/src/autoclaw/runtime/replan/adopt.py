from __future__ import annotations

from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import (
    FlowEdgeModel,
    FlowModel,
    FlowNodeModel,
    FlowRevisionModel,
    NodePlanRevisionModel,
)
from autoclaw.runtime.errors import illegal_state_error
from autoclaw.runtime.ids import flow_edge_id, flow_node_id, flow_revision_id, node_plan_revision_id
from autoclaw.runtime.replan.lineage import rebind_current_runtime_lineage
from autoclaw.runtime.task_root import criteria_file_path, load_task_root_paths

NodeSnapshot = dict[str, Any]
EdgeSnapshot = dict[str, Any]


async def adopt_candidate(
    session: AsyncSession,
    task_id: str,
    flow: FlowModel,
    current_revision: FlowRevisionModel,
    nodes: list[NodeSnapshot],
    edges: list[EdgeSnapshot],
) -> FlowRevisionModel:
    _sync_child_node_key_mirrors(nodes)
    next_revision_id, next_flow_revision = _create_next_flow_revision(
        flow=flow,
        current_revision=current_revision,
        nodes=nodes,
        edges=edges,
    )
    session.add(next_flow_revision)
    await session.flush()
    await _assign_criteria_versions(
        session,
        task_id=task_id,
        current_revision_id=current_revision.flow_revision_id,
        nodes=nodes,
    )
    await _clear_historical_current_assignments(
        session,
        current_revision_id=current_revision.flow_revision_id,
    )
    next_flow_node_ids = _persist_adopted_nodes(
        session,
        flow_id=flow.flow_id,
        next_revision_id=next_revision_id,
        next_flow_revision=next_flow_revision,
        nodes=nodes,
    )
    await session.flush()
    await rebind_current_runtime_lineage(
        session,
        flow_id=flow.flow_id,
        next_revision_id=next_revision_id,
        nodes=nodes,
        next_flow_node_ids=next_flow_node_ids,
        current_open_dispatch_id=flow.current_open_dispatch_id,
    )
    _persist_adopted_edges(session, next_revision_id, edges)
    flow.active_flow_revision_id = next_revision_id
    return next_flow_revision


def _criteria_signature(criteria: dict[str, object]) -> tuple[str, str, tuple[str, ...]]:
    return (
        str(criteria["slot"]),
        str(criteria["description"]),
        tuple(str(item) for item in cast(list[object], criteria.get("criteria", []))),
    )


def _sync_child_node_key_mirrors(nodes: list[NodeSnapshot]) -> None:
    nodes_by_key = {str(node["node_key"]): node for node in nodes}
    children_by_parent: dict[str, list[tuple[int, str]]] = {}

    for node in nodes:
        node["child_node_keys_json"] = []

    for node in nodes:
        parent_node_key = node.get("parent_node_key")
        if parent_node_key is None:
            continue
        parent_key = str(parent_node_key)
        if parent_key not in nodes_by_key:
            raise illegal_state_error(f"missing parent node '{parent_key}'")
        children_by_parent.setdefault(parent_key, []).append(
            (int(node["order_index"]), str(node["node_key"]))
        )

    for parent_key, children in children_by_parent.items():
        nodes_by_key[parent_key]["child_node_keys_json"] = [
            child_node_key for _, child_node_key in sorted(children, key=lambda item: item)
        ]


def _create_next_flow_revision(
    *,
    flow: FlowModel,
    current_revision: FlowRevisionModel,
    nodes: list[NodeSnapshot],
    edges: list[EdgeSnapshot],
) -> tuple[str, FlowRevisionModel]:
    next_revision_index = int(current_revision.revision_index + 1)
    next_revision_id = flow_revision_id(flow.flow_id, next_revision_index)
    created_by_dispatch_id = flow.current_open_dispatch_id
    if created_by_dispatch_id is None:
        raise illegal_state_error("structural replan requires a current open dispatch")
    return next_revision_id, FlowRevisionModel(
        flow_revision_id=next_revision_id,
        flow_id=flow.flow_id,
        revision_index=next_revision_index,
        parent_flow_revision_id=current_revision.flow_revision_id,
        source_compiled_plan_id=current_revision.source_compiled_plan_id or flow.compiled_plan_id,
        cause=_structural_revision_cause(current_revision, nodes),
        created_by_dispatch_id=created_by_dispatch_id,
        snapshot_json={"nodes": nodes, "edges": edges},
    )


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


async def _clear_historical_current_assignments(
    session: AsyncSession,
    *,
    current_revision_id: str,
) -> None:
    historical_nodes = await session.scalars(
        select(FlowNodeModel).where(
            FlowNodeModel.flow_revision_id == current_revision_id,
            FlowNodeModel.current_assignment_id.is_not(None),
        )
    )
    for historical_node in historical_nodes:
        historical_node.current_assignment_id = None


def _persist_adopted_nodes(
    session: AsyncSession,
    *,
    flow_id: str,
    next_revision_id: str,
    next_flow_revision: FlowRevisionModel,
    nodes: list[NodeSnapshot],
) -> dict[str, str]:
    next_flow_node_ids: dict[str, str] = {}
    for node in nodes:
        node_key = str(node["node_key"])
        next_flow_node_ids[node_key] = flow_node_id(next_revision_id, node_key)
        next_node = FlowNodeModel(
            flow_node_id=next_flow_node_ids[node_key],
            flow_id=flow_id,
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
            node_instruction=node["node_instruction"],
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
    return next_flow_node_ids


def _persist_adopted_edges(
    session: AsyncSession,
    next_revision_id: str,
    edges: list[EdgeSnapshot],
) -> None:
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
