from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.definitions.contracts.workflow import NodeKind
from autoclaw.runtime.contracts import ChildNodeDraft, ChildNodePatch
from autoclaw.runtime.errors import illegal_state_error, illegal_target_relation_error
from autoclaw.runtime.replan.adopt import adopt_candidate
from autoclaw.runtime.replan.defaults import apply_child_defaults, refresh_descendant_defaults
from autoclaw.runtime.replan.edges import rebuild_dependency_edges
from autoclaw.runtime.replan.lineage import node_has_open_current_work
from autoclaw.runtime.replan.lookup import resolve_policy, resolve_role
from autoclaw.runtime.replan.revision_state import current_revision_state

NodeSnapshot = dict[str, Any]


async def add_child_to_current_flow(
    session: AsyncSession,
    task_id: str,
    state: Any,
    child: ChildNodeDraft,
) -> str:
    flow, revision, nodes, _edges = await current_revision_state(session, state)
    parent = _resolve_add_child_parent(
        state,
        nodes=nodes,
        target_parent_node_key=child.parent_node_key,
    )
    new_nodes, _next_order_index = await _draft_subtree_nodes(
        session,
        draft=child,
        parent_node_key=str(parent["node_key"]),
        next_order_index=max(int(node["order_index"]) for node in nodes) + 1,
    )
    all_existing_keys = {str(node["node_key"]) for node in nodes}
    new_node_keys = [str(node["node_key"]) for node in new_nodes]
    duplicate_new_keys = {key for key in new_node_keys if new_node_keys.count(key) > 1}
    if duplicate_new_keys:
        duplicate_key = sorted(duplicate_new_keys)[0]
        raise illegal_state_error(f"node_key '{duplicate_key}' already exists in candidate subtree")
    for node_key in new_node_keys:
        if node_key in all_existing_keys:
            raise illegal_state_error(f"node_key '{node_key}' already exists")
    apply_child_defaults(parent, new_nodes[0])
    nodes.extend(new_nodes)
    edges = rebuild_dependency_edges(nodes)
    await adopt_candidate(session, task_id, flow, revision, nodes, edges)
    await session.flush()
    return child.node_key


async def update_child_in_current_flow(
    session: AsyncSession,
    task_id: str,
    state: Any,
    child_node_key: str,
    patch: ChildNodePatch,
) -> None:
    flow, revision, nodes, _edges = await current_revision_state(session, state)
    target, _parent = _resolve_structural_mutation_target(
        state,
        nodes=nodes,
        child_node_key=child_node_key,
        action_name="update_child",
    )
    previous_target = deepcopy(target)
    if patch.role is not None:
        role = await resolve_role(
            session,
            patch.role,
            node_kind=NodeKind(str(target["structural_kind"])),
            node_key=child_node_key,
        )
        target["role_key"] = patch.role
        target["role_revision_no"] = role.revision_no
        target["role_description"] = role.definition.description
        target["role_instruction"] = role.definition.instruction
    if patch.policy is not None:
        policy = await resolve_policy(
            session,
            patch.policy,
            node_kind=NodeKind(str(target["structural_kind"])),
            node_key=child_node_key,
        )
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
    if patch.criteria is not None or patch.child_defaults is not None:
        refresh_descendant_defaults(
            nodes,
            previous_parent=previous_target,
            updated_parent=target,
        )
    edges = rebuild_dependency_edges(nodes)
    await adopt_candidate(session, task_id, flow, revision, nodes, edges)
    await session.flush()


async def remove_child_from_current_flow(
    session: AsyncSession,
    task_id: str,
    state: Any,
    child_node_key: str,
) -> None:
    flow, revision, nodes, _edges = await current_revision_state(session, state)
    _target, _parent = _resolve_structural_mutation_target(
        state,
        nodes=nodes,
        child_node_key=child_node_key,
        action_name="remove_child",
    )
    descendants = {child_node_key}
    changed = True
    while changed:
        changed = False
        for node in nodes:
            if node["parent_node_key"] in descendants and node["node_key"] not in descendants:
                descendants.add(node["node_key"])
                changed = True
    for node in nodes:
        if node["node_key"] in descendants and await node_has_open_current_work(session, node):
            raise illegal_state_error("remove_child cannot delete open current child work")
    nodes = [node for node in nodes if node["node_key"] not in descendants]
    edges = rebuild_dependency_edges(nodes)
    await adopt_candidate(session, task_id, flow, revision, nodes, edges)
    await session.flush()


async def _draft_subtree_nodes(
    session: AsyncSession,
    *,
    draft: ChildNodeDraft,
    parent_node_key: str,
    next_order_index: int,
) -> tuple[list[NodeSnapshot], int]:
    structural_kind = NodeKind.PARENT if draft.children else NodeKind.WORKER
    role = await resolve_role(
        session,
        draft.role,
        node_kind=structural_kind,
        node_key=draft.node_key,
    )
    policy = None
    if draft.policy is not None:
        policy = await resolve_policy(
            session,
            draft.policy,
            node_kind=structural_kind,
            node_key=draft.node_key,
        )
    root_node: NodeSnapshot = {
        "node_key": draft.node_key,
        "parent_node_key": parent_node_key,
        "structural_kind": structural_kind.value,
        "role_key": draft.role,
        "role_revision_no": role.revision_no,
        "role_description": role.definition.description,
        "role_instruction": role.definition.instruction,
        "policy_key": draft.policy,
        "policy_revision_no": policy.revision_no if policy else None,
        "policy_description": policy.definition.description if policy else None,
        "policy_instruction": policy.definition.instruction if policy else None,
        "description": draft.description,
        "child_node_keys_json": [],
        "consumes_json": draft.consumes.model_dump(mode="json") if draft.consumes else None,
        "produces_json": draft.produces.model_dump(mode="json") if draft.produces else None,
        "criteria_json": [criteria.model_dump(mode="json") for criteria in draft.criteria or []],
        "child_defaults_json": draft.child_defaults.model_dump(mode="json")
        if draft.child_defaults
        else None,
        "current_assignment_id": None,
        "order_index": next_order_index,
    }
    subtree_nodes = [root_node]
    current_order_index = next_order_index + 1
    for child_draft in draft.children or []:
        child_nodes, current_order_index = await _draft_subtree_nodes(
            session,
            draft=child_draft,
            parent_node_key=draft.node_key,
            next_order_index=current_order_index,
        )
        apply_child_defaults(root_node, child_nodes[0])
        subtree_nodes.extend(child_nodes)
    return subtree_nodes, current_order_index


def _resolve_structural_mutation_target(
    state: Any,
    *,
    nodes: list[NodeSnapshot],
    child_node_key: str,
    action_name: str,
) -> tuple[NodeSnapshot, NodeSnapshot]:
    target = next((node for node in nodes if node["node_key"] == child_node_key), None)
    if target is None:
        raise illegal_target_relation_error(f"unknown child node '{child_node_key}'")
    if target["node_key"] == state.current_node.node_key:
        raise illegal_target_relation_error(
            f"{action_name} target must be an explicit descendant node"
        )
    parent_node_key = target["parent_node_key"]
    if parent_node_key == state.current_node.node_key:
        parent = next(node for node in nodes if node["node_key"] == state.current_node.node_key)
        return target, parent
    if state.current_node.structural_kind != NodeKind.ROOT.value:
        raise illegal_target_relation_error(f"{action_name} target must be a direct child")
    if parent_node_key is None:
        raise illegal_target_relation_error(
            f"{action_name} target must be an explicit descendant node"
        )
    for node in nodes:
        if node["node_key"] == parent_node_key:
            return target, node
    raise illegal_state_error(f"missing parent node '{parent_node_key}'")


def _resolve_add_child_parent(
    state: Any,
    *,
    nodes: list[NodeSnapshot],
    target_parent_node_key: str | None,
) -> NodeSnapshot:
    if target_parent_node_key is None or target_parent_node_key == state.current_node.node_key:
        return next(node for node in nodes if node["node_key"] == state.current_node.node_key)
    if state.current_node.structural_kind != NodeKind.ROOT.value:
        raise illegal_target_relation_error("add_child target parent must be a direct child")
    target_parent = next(
        (node for node in nodes if node["node_key"] == target_parent_node_key),
        None,
    )
    if target_parent is None:
        raise illegal_state_error(f"missing parent node '{target_parent_node_key}'")
    if target_parent["structural_kind"] != NodeKind.PARENT.value:
        raise illegal_target_relation_error(
            "add_child target parent must be an explicit descendant parent"
        )
    return target_parent
