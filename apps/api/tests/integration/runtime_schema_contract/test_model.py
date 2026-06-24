from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.persistence.models.runtime import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    AttemptModel,
    BudgetCounterModel,
    ContextItemModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
    WorkspaceRootLeaseModel,
)
from autoclaw.runtime.contracts import (
    DocRef,
    ObservabilityFileRef,
    OperatorFlowSnapshotResponse,
    OperatorSupportSurfaceRef,
    ParentToolCall,
    ReleaseGreenPayload,
    RuntimeTaskListQuery,
    TopActionableItem,
    WorkflowManifestRef,
)
from pydantic import ValidationError
from sqlalchemy.orm import configure_mappers
from tests.integration.runtime_schema_contract.support import (
    relationship_property,
    runtime_flow_read,
)


def test_operator_support_surface_refs_emit_explicit_kinds_for_operator_carriers() -> None:
    manifest_ref = WorkflowManifestRef(
        path=Path("/tmp/task/_runtime/workflow-manifest.md"),
        description="Whole-workflow visible contract for the current task.",
    )
    doc_ref = DocRef(
        kind="doc",
        path=Path("/tmp/task/_runtime/dispatch"),
        description="Dispatch observability directory for task-scoped inspection.",
    )
    normalized_current_paths = (
        OperatorSupportSurfaceRef.model_validate(manifest_ref),
        OperatorSupportSurfaceRef.model_validate(doc_ref),
    )
    snapshot = OperatorFlowSnapshotResponse(
        flow=runtime_flow_read(),
        top_actionable_items=(
            TopActionableItem(
                summary="Current runtime status is 'running'.",
                node_key="implementation_subtree",
                current_paths=normalized_current_paths,
            ),
        ),
        current_paths=normalized_current_paths,
        stream_head_event_id="event.7",
    )

    dumped = snapshot.model_dump(mode="json")
    assert dumped["stream_head_event_id"] == "event.7"
    assert dumped["current_paths"][0]["kind"] == "manifest"
    assert dumped["current_paths"][0]["slot"] is None
    assert dumped["current_paths"][0]["version"] is None
    assert dumped["current_paths"][1]["kind"] == "doc"
    assert dumped["top_actionable_items"][0]["current_paths"][0]["kind"] == "manifest"
    assert (
        OperatorSupportSurfaceRef.model_validate(manifest_ref).model_dump(mode="json")["kind"]
        == "manifest"
    )


def test_observability_file_refs_infer_support_kinds_from_projection_paths() -> None:
    ref = ObservabilityFileRef(
        path=Path("/tmp/task/_runtime/dispatch/dispatch.parent.01/delivery-state.json"),
        description="Latest task-scoped delivery-state projection.",
    )

    assert ref.kind == "delivery_state"
    assert ref.model_dump(mode="json")["kind"] == "delivery_state"
    assert OperatorSupportSurfaceRef.model_validate(ref).kind == "delivery_state"


def test_operator_support_surface_refs_reject_conflicting_fixed_kinds() -> None:
    with pytest.raises(ValidationError, match="must use operator ref kind 'manifest'"):
        OperatorSupportSurfaceRef.model_validate(
            {
                "kind": "doc",
                "path": Path("/tmp/task/_runtime/workflow-manifest.md"),
                "description": "Conflicting kind for manifest path.",
            }
        )

    with pytest.raises(ValidationError, match="must use observability kind 'delivery_state'"):
        ObservabilityFileRef.model_validate(
            {
                "kind": "provider_events",
                "path": Path("/tmp/task/_runtime/dispatch/dispatch.parent.01/delivery-state.json"),
                "description": "Conflicting observability kind.",
            }
        )


def test_parent_tool_call_uses_tool_name_to_validate_payload_shape() -> None:
    release_green = ParentToolCall.model_validate({"tool_name": "release_green", "payload": {}})

    assert release_green.tool_name == "release_green"
    assert isinstance(release_green.payload, ReleaseGreenPayload)
    assert release_green.as_variant().tool_name == "release_green"

    with pytest.raises(ValidationError):
        ParentToolCall.model_validate({"tool_name": "assign_child", "payload": {}})


def test_runtime_task_list_query_rejects_removed_flow_failed_status() -> None:
    query = RuntimeTaskListQuery.model_validate({})

    assert query.status == "any"

    with pytest.raises(ValidationError):
        RuntimeTaskListQuery.model_validate({"status": "failed"})


def test_runtime_mapper_exposes_currentness_chain_and_dispatch_sidecars() -> None:
    configure_mappers()

    active_flow_revision = relationship_property(FlowModel, "active_flow_revision")
    current_open_dispatch = relationship_property(FlowModel, "current_open_dispatch")
    current_assignment = relationship_property(FlowNodeModel, "current_assignment")
    current_attempt = relationship_property(AssignmentModel, "current_attempt")
    latest_checkpoint = relationship_property(AttemptModel, "latest_checkpoint")
    current_publication = relationship_property(ArtifactCurrentPointerModel, "current_publication")
    previous_dispatch = relationship_property(DispatchTurnModel, "previous_dispatch")
    superseded_by_dispatch = relationship_property(DispatchTurnModel, "superseded_by_dispatch")
    delivery_state = relationship_property(DispatchTurnModel, "delivery_state")
    continuity_state = relationship_property(DispatchTurnModel, "continuity_state")
    watchdog_state = relationship_property(DispatchTurnModel, "watchdog_state")
    provider_events = relationship_property(DispatchTurnModel, "provider_events")
    node_sessions = relationship_property(DispatchTurnModel, "node_sessions")

    assert active_flow_revision.viewonly is True
    assert active_flow_revision.lazy == "selectin"
    assert {column.key for column in active_flow_revision.local_columns} == {
        "active_flow_revision_id",
        "flow_id",
    }
    assert current_open_dispatch.viewonly is True
    assert current_open_dispatch.lazy == "selectin"
    assert {column.key for column in current_open_dispatch.local_columns} == {
        "current_open_dispatch_id",
        "flow_id",
    }
    assert current_assignment.viewonly is True
    assert current_assignment.lazy == "selectin"
    assert {column.key for column in current_assignment.local_columns} == {
        "current_assignment_id",
        "flow_node_id",
    }
    assert current_attempt.viewonly is True
    assert current_attempt.lazy == "raise"
    assert {column.key for column in current_attempt.local_columns} == {
        "assignment_id",
        "current_attempt_id",
    }
    assert latest_checkpoint.viewonly is True
    assert latest_checkpoint.lazy == "raise"
    assert {column.key for column in latest_checkpoint.local_columns} == {
        "attempt_id",
        "latest_checkpoint_id",
    }
    assert current_publication.lazy == "raise"
    assert {column.key for column in current_publication.local_columns} == {
        "current_version",
        "flow_node_id",
        "owner_node_key",
        "slot",
        "task_id",
    }
    assert previous_dispatch.lazy == "selectin"
    assert {column.key for column in previous_dispatch.remote_side} == {"dispatch_id"}
    assert superseded_by_dispatch.lazy == "selectin"
    assert {column.key for column in superseded_by_dispatch.remote_side} == {"dispatch_id"}
    assert delivery_state.lazy == "selectin" and delivery_state.uselist is False
    assert continuity_state.lazy == "selectin" and continuity_state.uselist is False
    assert watchdog_state.lazy == "selectin" and watchdog_state.uselist is False
    assert provider_events.lazy == "selectin" and provider_events.uselist is True
    assert node_sessions.lazy == "selectin" and node_sessions.uselist is True


def test_runtime_support_models_expose_owner_relationships() -> None:
    configure_mappers()

    context_task = relationship_property(ContextItemModel, "task")
    context_flow_node = relationship_property(ContextItemModel, "flow_node")
    lease_task = relationship_property(WorkspaceRootLeaseModel, "task")
    lease_flow = relationship_property(WorkspaceRootLeaseModel, "flow")
    budget_flow = relationship_property(BudgetCounterModel, "flow")
    budget_flow_node = relationship_property(BudgetCounterModel, "flow_node")
    budget_assignment = relationship_property(BudgetCounterModel, "assignment")
    budget_attempt = relationship_property(BudgetCounterModel, "attempt")

    assert context_task.lazy == "selectin" and context_task.uselist is False
    assert {column.key for column in context_task.local_columns} == {"task_id"}
    assert context_flow_node.lazy == "selectin" and context_flow_node.uselist is False
    assert {column.key for column in context_flow_node.local_columns} == {"flow_node_id"}
    assert lease_task.lazy == "selectin" and lease_task.uselist is False
    assert {column.key for column in lease_task.local_columns} == {"task_id"}
    assert lease_flow.lazy == "selectin" and lease_flow.uselist is False
    assert {column.key for column in lease_flow.local_columns} == {"flow_id"}
    assert budget_flow.lazy == "selectin" and budget_flow.uselist is False
    assert {column.key for column in budget_flow.local_columns} == {"flow_id"}
    assert budget_flow_node.lazy == "selectin" and budget_flow_node.uselist is False
    assert {column.key for column in budget_flow_node.local_columns} == {"flow_node_id"}
    assert budget_assignment.lazy == "selectin" and budget_assignment.uselist is False
    assert {column.key for column in budget_assignment.local_columns} == {"assignment_id"}
    assert budget_attempt.lazy == "selectin" and budget_attempt.uselist is False
    assert {column.key for column in budget_attempt.local_columns} == {"attempt_id"}
