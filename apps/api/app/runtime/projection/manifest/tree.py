from __future__ import annotations

from pathlib import Path
from typing import Any

from app.db.models import FlowEdgeModel, FlowNodeModel
from app.runtime.contracts import (
    EvidenceKind,
    ManifestNodeConsumeProjection,
    ManifestNodeCriteriaProjection,
    ManifestNodeProduceProjection,
    ManifestNodeProjection,
    NodeKind,
    TaskRootPaths,
)
from app.runtime.control.failures import illegal_state_error
from app.runtime.projection.projection_mappers import (
    int_or_none,
    json_list,
    json_mapping,
    sorted_unique,
)
from app.runtime.task_root import criteria_file_path


def flow_node_parent_key_by_id(nodes: list[FlowNodeModel]) -> dict[str, str | None]:
    nodes_by_id = {node.flow_node_id: node for node in nodes}
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
    return parent_key_by_id


def child_node_keys_by_parent_id(nodes: list[FlowNodeModel]) -> dict[str, tuple[str, ...]]:
    children_by_parent_id: dict[str, list[FlowNodeModel]] = {}
    for node in nodes:
        if node.parent_flow_node_id is None:
            continue
        children_by_parent_id.setdefault(node.parent_flow_node_id, []).append(node)
    return {
        parent_flow_node_id: tuple(
            child.node_key
            for child in sorted(children, key=lambda child: (child.order_index, child.node_key))
        )
        for parent_flow_node_id, children in children_by_parent_id.items()
    }


def criteria_description_by_slot(nodes: list[FlowNodeModel]) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for node in nodes:
        for criteria in node.criteria_json:
            slot = str(criteria["slot"])
            descriptions[slot] = str(criteria["description"])
    return descriptions


def _criteria_owner_node_key(
    *,
    node: FlowNodeModel,
    criteria: dict[str, Any],
) -> str:
    owner_node_key = criteria.get("owner_node_key")
    if isinstance(owner_node_key, str) and owner_node_key.strip():
        return owner_node_key
    return node.node_key


def _node_consumes(
    *,
    node: FlowNodeModel,
    dependency_descriptions: dict[tuple[str, str, str], str],
    criteria_descriptions: dict[str, str],
) -> tuple[ManifestNodeConsumeProjection, ...]:
    consumes: list[ManifestNodeConsumeProjection] = []
    consumes_json = json_mapping(node.consumes_json)
    for selector in json_list(consumes_json.get("artifacts", [])):
        consumes.append(
            ManifestNodeConsumeProjection(
                kind=EvidenceKind.ARTIFACT,
                slot=str(selector["slot"]),
                description=dependency_descriptions[
                    (node.node_key, "artifact", str(selector["slot"]))
                ],
                required=bool(selector.get("required", True)),
            )
        )
    for selector in json_list(consumes_json.get("criteria", [])):
        consumes.append(
            ManifestNodeConsumeProjection(
                kind=EvidenceKind.CRITERIA,
                slot=str(selector["slot"]),
                description=criteria_descriptions[str(selector["slot"])],
                required=bool(selector.get("required", True)),
            )
        )
    return tuple(consumes)


def _node_criteria(
    *,
    node: FlowNodeModel,
    paths: TaskRootPaths,
) -> tuple[ManifestNodeCriteriaProjection, ...]:
    return tuple(
        ManifestNodeCriteriaProjection(
            owner_node_key=_criteria_owner_node_key(node=node, criteria=item),
            slot=str(item["slot"]),
            description=str(item["description"]),
            path=(
                Path(str(item["path"]))
                if item.get("path") is not None
                else criteria_file_path(
                    paths=paths,
                    slot=str(item["slot"]),
                    version=int_or_none(item.get("version")),
                )
            ),
        )
        for item in node.criteria_json
    )


def _manifest_node_projection(
    *,
    node: FlowNodeModel,
    edges: list[FlowEdgeModel],
    paths: TaskRootPaths,
    parent_node_key_by_id: dict[str, str | None],
    child_node_keys_by_parent_id: dict[str, tuple[str, ...]],
    dependency_descriptions: dict[tuple[str, str, str], str],
    criteria_descriptions: dict[str, str],
) -> ManifestNodeProjection:
    return ManifestNodeProjection(
        node_key=node.node_key,
        parent_node_key=parent_node_key_by_id[node.flow_node_id],
        child_node_keys=child_node_keys_by_parent_id.get(node.flow_node_id, ()),
        node_kind=NodeKind(node.structural_kind),
        role=node.role_key,
        policy=node.policy_key,
        description=node.description,
        consumes=_node_consumes(
            node=node,
            dependency_descriptions=dependency_descriptions,
            criteria_descriptions=criteria_descriptions,
        ),
        produces=tuple(
            ManifestNodeProduceProjection.model_validate(item)
            for item in json_list(json_mapping(node.produces_json).get("artifacts", []))
        ),
        criteria=_node_criteria(node=node, paths=paths),
        depends_on_node_keys=sorted_unique(
            edge.provider_node_key for edge in edges if edge.consumer_node_key == node.node_key
        ),
        depended_on_by_node_keys=sorted_unique(
            edge.consumer_node_key for edge in edges if edge.provider_node_key == node.node_key
        ),
    )


def build_manifest_node_tree(
    *,
    nodes: list[FlowNodeModel],
    edges: list[FlowEdgeModel],
    paths: TaskRootPaths,
    parent_node_key_by_id: dict[str, str | None],
    child_node_keys_by_parent_id: dict[str, tuple[str, ...]],
    dependency_descriptions: dict[tuple[str, str, str], str],
    criteria_descriptions: dict[str, str],
) -> tuple[ManifestNodeProjection, ...]:
    return tuple(
        _manifest_node_projection(
            node=node,
            edges=edges,
            paths=paths,
            parent_node_key_by_id=parent_node_key_by_id,
            child_node_keys_by_parent_id=child_node_keys_by_parent_id,
            dependency_descriptions=dependency_descriptions,
            criteria_descriptions=criteria_descriptions,
        )
        for node in nodes
    )
