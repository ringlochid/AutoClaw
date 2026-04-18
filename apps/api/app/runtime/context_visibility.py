from __future__ import annotations

from app.core.enums import ContextItemScope


def is_context_item_visible_to_target(
    item: object,
    *,
    flow_id: object,
    flow_node_id: object,
    node_attempt_id: object,
) -> bool:
    scope = getattr(item, "scope")
    if scope == ContextItemScope.TASK_SHARED:
        return True
    if scope == ContextItemScope.FLOW_SHARED:
        return getattr(item, "flow_id", None) == flow_id
    if scope == ContextItemScope.NODE_PRIVATE:
        return getattr(item, "flow_node_id", None) == flow_node_id
    if scope == ContextItemScope.ATTEMPT_SCRATCH:
        return getattr(item, "node_attempt_id", None) == node_attempt_id
    return False
