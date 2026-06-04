from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.db.models import FlowNodeModel
from autoclaw.runtime.control.boundary.release_descendant_refs import release_turn_descendant_refs
from autoclaw.runtime.control.failures import illegal_state_error, missing_resource_error


async def parent_node_from_relation(
    session: AsyncSession,
    *,
    node: FlowNodeModel,
) -> FlowNodeModel | None:
    if node.parent_flow_node_id is None:
        if node.parent_node_key is not None:
            raise illegal_state_error(
                "runtime node mirror parent_node_key exists without relational parent_flow_node_id"
            )
        return None
    parent = await session.get(FlowNodeModel, node.parent_flow_node_id)
    if parent is None:
        raise missing_resource_error(
            "missing relational parent flow node "
            f"'{node.parent_flow_node_id}' for node '{node.node_key}'"
        )
    return parent


__all__ = ["parent_node_from_relation", "release_turn_descendant_refs"]
