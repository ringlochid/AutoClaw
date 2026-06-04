"""Explicit Phase 6 bridge for the legacy flow-control owner."""

from __future__ import annotations

from app.runtime.control.flow import listing as legacy_flow_listing
from app.runtime.control.flow import queries as legacy_flow_queries
from app.runtime.control.flow import reads as legacy_flow_reads
from app.runtime.control.flow import resume as legacy_flow_resume
from app.runtime.control.flow import service as legacy_flow_service
from app.runtime.control.flow import timestamps as legacy_flow_timestamps

WORKFLOW_MANIFEST_REF_DESCRIPTION = legacy_flow_listing.WORKFLOW_MANIFEST_REF_DESCRIPTION
cancel_runtime_flow = legacy_flow_service.cancel_runtime_flow
coerce_datetime_to_utc = legacy_flow_timestamps.coerce_datetime_to_utc
continue_runtime_flow = legacy_flow_service.continue_runtime_flow
current_semantic_flow_target = legacy_flow_queries.current_semantic_flow_target
flow_node_by_key = legacy_flow_queries.flow_node_by_key
latest_checkpoint_for_attempt = legacy_flow_queries.latest_checkpoint_for_attempt
latest_unreplaced_fenced_dispatch = legacy_flow_reads.latest_unreplaced_fenced_dispatch
list_runtime_flows = legacy_flow_reads.list_runtime_flows
next_node_sequence_number = legacy_flow_queries.next_node_sequence_number
pause_runtime_flow = legacy_flow_service.pause_runtime_flow
require_flow_for_task = legacy_flow_queries.require_flow_for_task
resolve_flow_resume_target = legacy_flow_resume.resolve_flow_resume_target
runtime_flow_read = legacy_flow_reads.runtime_flow_read


__all__ = [
    "WORKFLOW_MANIFEST_REF_DESCRIPTION",
    "cancel_runtime_flow",
    "coerce_datetime_to_utc",
    "continue_runtime_flow",
    "current_semantic_flow_target",
    "flow_node_by_key",
    "latest_checkpoint_for_attempt",
    "latest_unreplaced_fenced_dispatch",
    "list_runtime_flows",
    "next_node_sequence_number",
    "pause_runtime_flow",
    "require_flow_for_task",
    "resolve_flow_resume_target",
    "runtime_flow_read",
]
