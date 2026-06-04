from __future__ import annotations

from pathlib import Path

import pytest
from autoclaw.db.models.runtime import (
    ArtifactCurrentPointerModel,
    AssignmentModel,
    AttemptModel,
    DispatchTurnModel,
    FlowModel,
    FlowNodeModel,
)
from autoclaw.schemas.runtime import (
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
    )

    dumped = snapshot.model_dump(mode="json")
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
