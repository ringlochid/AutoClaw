from __future__ import annotations

import importlib


def test_runtime_control_and_launch_owner_shells_share_legacy_exports() -> None:
    autoclaw_control = importlib.import_module("autoclaw.runtime.control")
    autoclaw_assignment = importlib.import_module("autoclaw.runtime.control.assignment")
    autoclaw_boundary = importlib.import_module("autoclaw.runtime.control.boundary")
    autoclaw_checkpoint = importlib.import_module("autoclaw.runtime.control.checkpoint")
    autoclaw_flow = importlib.import_module("autoclaw.runtime.control.flow")
    autoclaw_observability = importlib.import_module("autoclaw.runtime.control.observability")
    autoclaw_parent_tools = importlib.import_module("autoclaw.runtime.control.parent_tools")
    autoclaw_release = importlib.import_module("autoclaw.runtime.control.release")
    autoclaw_launch_persistence = importlib.import_module("autoclaw.runtime.launch.persistence")

    legacy_assignment = importlib.import_module("autoclaw.runtime.control.assignment")
    legacy_boundary = importlib.import_module("autoclaw.runtime.control.boundary")
    legacy_checkpoint = importlib.import_module("autoclaw.runtime.control.checkpoint")
    legacy_flow = importlib.import_module("autoclaw.runtime.control.flow")
    legacy_observability = importlib.import_module("autoclaw.runtime.control.observability")
    legacy_parent_tools = importlib.import_module("autoclaw.runtime.control.parent_tools")
    legacy_release = importlib.import_module("autoclaw.runtime.control.release")
    legacy_launch_persistence = importlib.import_module("autoclaw.runtime.launch.persistence")

    assert autoclaw_control.assignment is autoclaw_assignment
    assert autoclaw_control.boundary is autoclaw_boundary
    assert autoclaw_control.cancel_runtime_flow is autoclaw_flow.cancel_runtime_flow
    assert autoclaw_control.checkpoint is autoclaw_checkpoint
    assert autoclaw_control.continue_runtime_flow is autoclaw_flow.continue_runtime_flow
    assert autoclaw_control.flow is autoclaw_flow
    assert autoclaw_control.list_runtime_flows is autoclaw_flow.list_runtime_flows
    assert autoclaw_control.observability is autoclaw_observability
    assert autoclaw_control.observability_ref is autoclaw_observability.observability_ref
    assert autoclaw_control.operator_snapshot is autoclaw_observability.operator_snapshot
    assert autoclaw_control.operator_trace is autoclaw_observability.operator_trace
    assert autoclaw_control.pause_runtime_flow is autoclaw_flow.pause_runtime_flow
    assert autoclaw_control.parent_tools is autoclaw_parent_tools
    assert autoclaw_control.call_parent_tool is autoclaw_parent_tools.call_parent_tool
    assert autoclaw_control.record_checkpoint is autoclaw_checkpoint.record_checkpoint
    assert autoclaw_control.release is autoclaw_release
    assert autoclaw_control.runtime_flow_read is autoclaw_flow.runtime_flow_read

    assert autoclaw_control.accept_boundary is autoclaw_boundary.accept_boundary
    assert autoclaw_assignment.call_assign_child is legacy_assignment.call_assign_child
    assert autoclaw_boundary.accept_boundary is legacy_boundary.accept_boundary
    assert autoclaw_checkpoint.record_checkpoint is legacy_checkpoint.record_checkpoint
    assert autoclaw_flow.runtime_flow_read is legacy_flow.runtime_flow_read
    assert autoclaw_observability.observability_ref is legacy_observability.observability_ref
    assert autoclaw_observability.operator_snapshot is legacy_observability.operator_snapshot
    assert autoclaw_observability.operator_trace is legacy_observability.operator_trace
    assert autoclaw_parent_tools.call_parent_tool is legacy_parent_tools.call_parent_tool
    assert (
        autoclaw_flow.WORKFLOW_MANIFEST_REF_DESCRIPTION
        == legacy_flow.WORKFLOW_MANIFEST_REF_DESCRIPTION
    )
    assert (
        autoclaw_release.ensure_release_green_preconditions
        is legacy_release.ensure_release_green_preconditions
    )
    assert (
        autoclaw_launch_persistence.persist_bootstrap_runtime_from_precomputed
        is legacy_launch_persistence.persist_bootstrap_runtime_from_precomputed
    )
    assert (
        autoclaw_launch_persistence.write_bootstrap_runtime_outputs
        is legacy_launch_persistence.write_bootstrap_runtime_outputs
    )
