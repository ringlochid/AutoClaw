"""Explicit Phase 6 bridge for the legacy node-operation control owner."""

from __future__ import annotations

from app.runtime.control import node_operations as legacy_node_operations

BoundaryNodeOperation = legacy_node_operations.BoundaryNodeOperation
CheckpointNodeOperation = legacy_node_operations.CheckpointNodeOperation
NodeOperation = legacy_node_operations.NodeOperation
NodeOperationResult = legacy_node_operations.NodeOperationResult
ParentToolNodeOperation = legacy_node_operations.ParentToolNodeOperation
execute_bound_node_operation = legacy_node_operations.execute_bound_node_operation
execute_node_operation = legacy_node_operations.execute_node_operation

__all__ = [
    "BoundaryNodeOperation",
    "CheckpointNodeOperation",
    "NodeOperation",
    "NodeOperationResult",
    "ParentToolNodeOperation",
    "execute_bound_node_operation",
    "execute_node_operation",
]
