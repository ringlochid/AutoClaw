from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import RuntimeBase


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


class TaskModel(RuntimeBase):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_key: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_root_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class WorkspaceRootModel(RuntimeBase):
    __tablename__ = "workspace_roots"

    workspace_root_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    path: Mapped[str] = mapped_column(Text)
    binding_mode: Mapped[str] = mapped_column(String(64))


class ContextSpaceModel(RuntimeBase):
    __tablename__ = "context_spaces"

    context_space_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    path: Mapped[str] = mapped_column(Text)
    binding_mode: Mapped[str] = mapped_column(String(64))


class ManifestRootModel(RuntimeBase):
    __tablename__ = "manifest_roots"

    manifest_root_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    path: Mapped[str] = mapped_column(Text)


class TaskResourceBindingModel(RuntimeBase):
    __tablename__ = "task_resource_bindings"

    task_resource_binding_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    binding_kind: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(Text)
    binding_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)


class TaskComposeModel(RuntimeBase):
    __tablename__ = "task_composes"

    task_compose_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    workflow_key: Mapped[str] = mapped_column(String(255))
    workflow_revision_no: Mapped[int] = mapped_column(Integer)
    compiled_plan_id: Mapped[str] = mapped_column(String(255))
    workspace_root_path: Mapped[str] = mapped_column(Text)
    context_root_path: Mapped[str] = mapped_column(Text)
    outputs_root_path: Mapped[str] = mapped_column(Text)
    runtime_root_path: Mapped[str] = mapped_column(Text)
    compose_payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CompiledPlanModel(RuntimeBase):
    __tablename__ = "compiled_plans"

    compiled_plan_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    workflow_key: Mapped[str] = mapped_column(String(255))
    definition_revision_no: Mapped[int] = mapped_column(Integer)
    compiler_version: Mapped[str] = mapped_column(String(255))
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CompiledPlanNodeModel(RuntimeBase):
    __tablename__ = "compiled_plan_nodes"
    __table_args__ = (UniqueConstraint("compiled_plan_id", "node_key"),)

    compiled_plan_node_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    compiled_plan_id: Mapped[str] = mapped_column(ForeignKey("compiled_plans.compiled_plan_id"))
    node_key: Mapped[str] = mapped_column(String(255))
    parent_node_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    structural_kind: Mapped[str] = mapped_column(String(64))
    role_key: Mapped[str] = mapped_column(String(255))
    role_revision_no: Mapped[int] = mapped_column(Integer)
    role_description: Mapped[str] = mapped_column(Text)
    role_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_revision_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    child_node_keys_json: Mapped[list[str]] = mapped_column(JSON)
    consumes_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    produces_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    criteria_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    child_defaults_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer)


class CompiledPlanEdgeModel(RuntimeBase):
    __tablename__ = "compiled_plan_edges"
    __table_args__ = (UniqueConstraint("compiled_plan_id", "consumer_node_key", "kind", "slot"),)

    compiled_plan_edge_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    compiled_plan_id: Mapped[str] = mapped_column(ForeignKey("compiled_plans.compiled_plan_id"))
    provider_node_key: Mapped[str] = mapped_column(String(255))
    consumer_node_key: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(64))
    slot: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)


class FlowModel(RuntimeBase):
    __tablename__ = "flows"

    flow_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), unique=True, index=True)
    compiled_plan_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), index=True)
    active_flow_revision_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_open_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_node_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class FlowRevisionModel(RuntimeBase):
    __tablename__ = "flow_revisions"
    __table_args__ = (UniqueConstraint("flow_id", "revision_index"),)

    flow_revision_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.flow_id"), index=True)
    revision_index: Mapped[int] = mapped_column(Integer)
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FlowNodeModel(RuntimeBase):
    __tablename__ = "flow_nodes"
    __table_args__ = (UniqueConstraint("flow_revision_id", "node_key"),)

    flow_node_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_revision_id: Mapped[str] = mapped_column(ForeignKey("flow_revisions.flow_revision_id"))
    node_key: Mapped[str] = mapped_column(String(255))
    parent_node_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    structural_kind: Mapped[str] = mapped_column(String(64))
    role_key: Mapped[str] = mapped_column(String(255))
    role_revision_no: Mapped[int] = mapped_column(Integer)
    role_description: Mapped[str] = mapped_column(Text)
    role_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_revision_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    child_node_keys_json: Mapped[list[str]] = mapped_column(JSON)
    consumes_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    produces_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    criteria_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    child_defaults_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    current_assignment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer)


class FlowEdgeModel(RuntimeBase):
    __tablename__ = "flow_edges"
    __table_args__ = (UniqueConstraint("flow_revision_id", "consumer_node_key", "kind", "slot"),)

    flow_edge_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_revision_id: Mapped[str] = mapped_column(ForeignKey("flow_revisions.flow_revision_id"))
    provider_node_key: Mapped[str] = mapped_column(String(255))
    consumer_node_key: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(64))
    slot: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)


class NodePlanRevisionModel(RuntimeBase):
    __tablename__ = "node_plan_revisions"

    node_plan_revision_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_revision_id: Mapped[str] = mapped_column(ForeignKey("flow_revisions.flow_revision_id"))
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"))
    role_key: Mapped[str] = mapped_column(String(255))
    role_revision_no: Mapped[int] = mapped_column(Integer)
    role_description: Mapped[str] = mapped_column(Text)
    role_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_revision_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)


class AssignmentModel(RuntimeBase):
    __tablename__ = "assignments"

    assignment_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_node_id: Mapped[str] = mapped_column(ForeignKey("flow_nodes.flow_node_id"), index=True)
    assignment_key: Mapped[str] = mapped_column(String(255), unique=True)
    node_key: Mapped[str] = mapped_column(String(255), index=True)
    summary: Mapped[str] = mapped_column(Text)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    consumes_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    produces_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    transient_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    task_memory_search_hints_json: Mapped[list[str]] = mapped_column(JSON)
    current_attempt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_green_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    release_blocked_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AssignmentCriteriaRefModel(RuntimeBase):
    __tablename__ = "assignment_criteria_refs"

    assignment_criteria_ref_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_id"), index=True)
    slot: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)


class AttemptModel(RuntimeBase):
    __tablename__ = "attempts"

    attempt_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.assignment_id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    node_key: Mapped[str] = mapped_column(String(255), index=True)
    latest_checkpoint_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    terminal_outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AttemptCheckpointModel(RuntimeBase):
    __tablename__ = "attempt_checkpoints"

    checkpoint_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"), index=True)
    checkpoint_kind: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    next_step: Mapped[str] = mapped_column(Text)
    blockers_json: Mapped[list[str]] = mapped_column(JSON)
    risks_json: Mapped[list[str]] = mapped_column(JSON)
    produced_artifacts_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    transient_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    task_memory_search_hints_json: Mapped[list[str]] = mapped_column(JSON)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AttemptConsumedRefModel(RuntimeBase):
    __tablename__ = "attempt_consumed_refs"

    attempt_consumed_ref_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"), index=True)
    ref_kind: Mapped[str] = mapped_column(String(64))
    slot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)


class AttemptProducedRefModel(RuntimeBase):
    __tablename__ = "attempt_produced_refs"

    attempt_produced_ref_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.attempt_id"), index=True)
    slot: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    order_index: Mapped[int] = mapped_column(Integer)


class ArtifactPublicationModel(RuntimeBase):
    __tablename__ = "artifact_publications"
    __table_args__ = (UniqueConstraint("task_id", "owner_node_key", "slot", "version"),)

    artifact_publication_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    owner_node_key: Mapped[str] = mapped_column(String(255), index=True)
    slot: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    assignment_key: Mapped[str] = mapped_column(String(255))
    attempt_id: Mapped[str] = mapped_column(String(255))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    supersedes_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class ArtifactCurrentPointerModel(RuntimeBase):
    __tablename__ = "artifact_current_pointers"
    __table_args__ = (UniqueConstraint("task_id", "owner_node_key", "slot"),)

    artifact_current_pointer_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    owner_node_key: Mapped[str] = mapped_column(String(255))
    slot: Mapped[str] = mapped_column(String(255))
    current_version: Mapped[int] = mapped_column(Integer)
    current_path: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    assignment_key: Mapped[str] = mapped_column(String(255))
    attempt_id: Mapped[str] = mapped_column(String(255))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    supersedes_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class DispatchTurnModel(RuntimeBase):
    __tablename__ = "dispatch_turns"

    dispatch_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_id: Mapped[str] = mapped_column(ForeignKey("flows.flow_id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    node_key: Mapped[str] = mapped_column(String(255), index=True)
    assignment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignment_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_name: Mapped[str] = mapped_column(String(255))
    send_mode: Mapped[str] = mapped_column(String(64))
    delivery_status: Mapped[str] = mapped_column(String(64))
    control_state: Mapped[str] = mapped_column(String(64))
    prompt_path: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(255))
    previous_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    superseded_by_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    staged_child_assignment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accepted_boundary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    rendered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DispatchCallbackBindingModel(RuntimeBase):
    __tablename__ = "dispatch_callback_bindings"

    dispatch_callback_binding_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    dispatch_id: Mapped[str] = mapped_column(
        ForeignKey("dispatch_turns.dispatch_id"),
        unique=True,
        index=True,
    )
    attempt_id: Mapped[str] = mapped_column(String(255))
    assignment_id: Mapped[str] = mapped_column(String(255))
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    session_key: Mapped[str] = mapped_column(String(255), unique=True)
    binding_status: Mapped[str] = mapped_column(String(64))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DispatchDeliveryStateModel(RuntimeBase):
    __tablename__ = "dispatch_delivery_states"

    dispatch_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignment_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    node_key: Mapped[str] = mapped_column(String(255))
    transport_family: Mapped[str] = mapped_column(String(255))
    transport_state: Mapped[str] = mapped_column(String(255))
    controller_observation_state: Mapped[str] = mapped_column(String(255))
    last_provider_event_kind: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_final_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    send_mode: Mapped[str] = mapped_column(String(64))
    previous_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    superseded_by_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_provider_signal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_controller_progress_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_controller_terminal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class DispatchContinuityStateModel(RuntimeBase):
    __tablename__ = "dispatch_continuity_states"

    dispatch_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignment_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    node_key: Mapped[str] = mapped_column(String(255))
    continuity_state: Mapped[str] = mapped_column(String(255))
    previous_response_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_key_present: Mapped[bool] = mapped_column(Boolean, default=False)
    invalidation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class DispatchWatchdogStateModel(RuntimeBase):
    __tablename__ = "dispatch_watchdog_states"

    dispatch_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignment_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    node_key: Mapped[str] = mapped_column(String(255))
    watchdog_state: Mapped[str] = mapped_column(String(255))
    current_watchdog_kind: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_watchdog_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recovery_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    superseded_by_dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class ProviderEventRecordModel(RuntimeBase):
    __tablename__ = "provider_event_records"

    provider_event_record_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    dispatch_id: Mapped[str] = mapped_column(ForeignKey("dispatch_turns.dispatch_id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    event_kind: Mapped[str] = mapped_column(String(255))
    event_payload_json: Mapped[dict[str, object]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ContextItemModel(RuntimeBase):
    __tablename__ = "context_items"

    context_item_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_node_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    item_kind: Mapped[str] = mapped_column(String(64))
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class NodeSessionModel(RuntimeBase):
    __tablename__ = "node_sessions"

    node_session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    flow_node_id: Mapped[str] = mapped_column(String(255), index=True)
    assignment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dispatch_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_status: Mapped[str] = mapped_column(String(64))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkspaceRootLeaseModel(RuntimeBase):
    __tablename__ = "workspace_root_leases"

    workspace_root_lease_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    normalized_workspace_root_path: Mapped[str] = mapped_column(Text, unique=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.task_id"), index=True)
    flow_id: Mapped[str] = mapped_column(String(255), index=True)
    lease_status: Mapped[str] = mapped_column(String(64))
    leased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BudgetCounterModel(RuntimeBase):
    __tablename__ = "budget_counters"

    budget_counter_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    budget_family: Mapped[str] = mapped_column(String(255))
    scope_kind: Mapped[str] = mapped_column(String(64))
    flow_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    initial_limit: Mapped[int] = mapped_column(Integer)
    remaining: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    exhausted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_version: Mapped[int] = mapped_column(Integer, default=1)


Index("ix_assignments_task_node", AssignmentModel.task_id, AssignmentModel.node_key)
Index("ix_attempts_task_node", AttemptModel.task_id, AttemptModel.node_key)
Index(
    "ix_artifact_publications_lookup",
    ArtifactPublicationModel.task_id,
    ArtifactPublicationModel.owner_node_key,
    ArtifactPublicationModel.slot,
)
