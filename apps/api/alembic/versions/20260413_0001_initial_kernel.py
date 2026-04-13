"""initial kernel schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260413_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    definition_version_status = postgresql.ENUM("draft", "published", "archived", name="definition_version_status", create_type=False)
    skill_provider = postgresql.ENUM("openclaw", "local", "remote", name="skill_provider", create_type=False)
    workflow_mode = postgresql.ENUM(
        "plan",
        "persistent_execute",
        "review",
        "wait",
        "pause",
        "sync",
        name="workflow_mode",
        create_type=False,
    )
    flow_edge_kind = postgresql.ENUM("control", "dependency", name="flow_edge_kind", create_type=False)
    task_status = postgresql.ENUM("pending", "running", "blocked", "failed", "succeeded", "cancelled", name="task_status", create_type=False)
    run_status = postgresql.ENUM("pending", "running", "blocked", "failed", "succeeded", "cancelled", name="run_status", create_type=False)
    attempt_status = postgresql.ENUM("pending", "running", "blocked", "failed", "succeeded", "cancelled", name="attempt_status", create_type=False)
    flow_status = postgresql.ENUM("pending", "running", "blocked", "failed", "succeeded", "cancelled", name="flow_status", create_type=False)
    flow_node_state = postgresql.ENUM("ready", "running", "waiting", "paused", "done", "failed", name="flow_node_state", create_type=False)
    checkpoint_status = postgresql.ENUM("green", "retry", "blocked", "needs_approval", name="checkpoint_status", create_type=False)
    approval_status = postgresql.ENUM("not_required", "pending", "approved", "rejected", "expired", name="approval_status", create_type=False)

    bind = op.get_bind()
    definition_version_status.create(bind, checkfirst=True)
    skill_provider.create(bind, checkfirst=True)
    workflow_mode.create(bind, checkfirst=True)
    flow_edge_kind.create(bind, checkfirst=True)
    task_status.create(bind, checkfirst=True)
    run_status.create(bind, checkfirst=True)
    attempt_status.create(bind, checkfirst=True)
    flow_status.create(bind, checkfirst=True)
    flow_node_state.create(bind, checkfirst=True)
    checkpoint_status.create(bind, checkfirst=True)
    approval_status.create(bind, checkfirst=True)

    op.create_table(
        "role_definitions",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_definitions")),
        sa.UniqueConstraint("key", name=op.f("uq_role_definitions_key")),
    )
    op.create_index(op.f("ix_role_definitions_key"), "role_definitions", ["key"], unique=False)

    op.create_table(
        "policy_definitions",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_definitions")),
        sa.UniqueConstraint("key", name=op.f("uq_policy_definitions_key")),
    )
    op.create_index(op.f("ix_policy_definitions_key"), "policy_definitions", ["key"], unique=False)

    op.create_table(
        "workflow_definitions",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_definitions")),
        sa.UniqueConstraint("key", name=op.f("uq_workflow_definitions_key")),
    )
    op.create_index(op.f("ix_workflow_definitions_key"), "workflow_definitions", ["key"], unique=False)

    op.create_table(
        "skill_registry",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("provider", skill_provider, nullable=False),
        sa.Column("source_uri", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skill_registry")),
        sa.UniqueConstraint("key", name=op.f("uq_skill_registry_key")),
    )
    op.create_index(op.f("ix_skill_registry_key"), "skill_registry", ["key"], unique=False)

    op.create_table(
        "role_versions",
        sa.Column("role_definition_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", definition_version_status, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["role_definition_id"], ["role_definitions.id"], name=op.f("fk_role_versions_role_definition_id_role_definitions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_versions")),
        sa.UniqueConstraint("role_definition_id", "version", name="uq_role_versions_definition_version"),
    )

    op.create_table(
        "policy_versions",
        sa.Column("policy_definition_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", definition_version_status, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["policy_definition_id"], ["policy_definitions.id"], name=op.f("fk_policy_versions_policy_definition_id_policy_definitions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_versions")),
        sa.UniqueConstraint("policy_definition_id", "version", name="uq_policy_versions_definition_version"),
    )

    op.create_table(
        "workflow_versions",
        sa.Column("workflow_definition_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", definition_version_status, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workflow_definition_id"], ["workflow_definitions.id"], name=op.f("fk_workflow_versions_workflow_definition_id_workflow_definitions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_versions")),
        sa.UniqueConstraint("workflow_definition_id", "version", name="uq_workflow_versions_definition_version"),
    )

    op.create_table(
        "skill_versions",
        sa.Column("skill_registry_id", sa.Uuid(), nullable=False),
        sa.Column("version_label", sa.String(length=128), nullable=False),
        sa.Column("status", definition_version_status, nullable=False),
        sa.Column("source_ref", sa.String(length=256), nullable=True),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["skill_registry_id"], ["skill_registry.id"], name=op.f("fk_skill_versions_skill_registry_id_skill_registry"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skill_versions")),
        sa.UniqueConstraint("skill_registry_id", "version_label", name="uq_skill_versions_registry_version"),
    )

    op.create_table(
        "tasks",
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status, nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
    )

    op.create_table(
        "compiled_plans",
        sa.Column("workflow_version_id", sa.Uuid(), nullable=False),
        sa.Column("compiler_version", sa.String(length=64), nullable=False),
        sa.Column("plan_hash", sa.String(length=128), nullable=False),
        sa.Column("source_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workflow_version_id"], ["workflow_versions.id"], name=op.f("fk_compiled_plans_workflow_version_id_workflow_versions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compiled_plans")),
        sa.UniqueConstraint("plan_hash", name=op.f("uq_compiled_plans_plan_hash")),
    )
    op.create_index(op.f("ix_compiled_plans_plan_hash"), "compiled_plans", ["plan_hash"], unique=False)

    op.create_table(
        "compiled_plan_nodes",
        sa.Column("compiled_plan_id", sa.Uuid(), nullable=False),
        sa.Column("node_key", sa.String(length=128), nullable=False),
        sa.Column("parent_node_key", sa.String(length=128), nullable=True),
        sa.Column("role_version_id", sa.Uuid(), nullable=True),
        sa.Column("policy_version_id", sa.Uuid(), nullable=True),
        sa.Column("mode", workflow_mode, nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("skill_bindings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["compiled_plan_id"], ["compiled_plans.id"], name=op.f("fk_compiled_plan_nodes_compiled_plan_id_compiled_plans"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], name=op.f("fk_compiled_plan_nodes_policy_version_id_policy_versions")),
        sa.ForeignKeyConstraint(["role_version_id"], ["role_versions.id"], name=op.f("fk_compiled_plan_nodes_role_version_id_role_versions")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compiled_plan_nodes")),
        sa.UniqueConstraint("compiled_plan_id", "node_key", name="uq_compiled_plan_nodes_plan_node_key"),
    )

    op.create_table(
        "compiled_plan_edges",
        sa.Column("compiled_plan_id", sa.Uuid(), nullable=False),
        sa.Column("from_node_key", sa.String(length=128), nullable=False),
        sa.Column("to_node_key", sa.String(length=128), nullable=False),
        sa.Column("edge_kind", flow_edge_kind, nullable=False),
        sa.Column("condition_expr", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["compiled_plan_id"], ["compiled_plans.id"], name=op.f("fk_compiled_plan_edges_compiled_plan_id_compiled_plans"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compiled_plan_edges")),
    )

    op.create_table(
        "runs",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_version_id", sa.Uuid(), nullable=False),
        sa.Column("compiled_plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("current_attempt_number", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["compiled_plan_id"], ["compiled_plans.id"], name=op.f("fk_runs_compiled_plan_id_compiled_plans")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name=op.f("fk_runs_task_id_tasks"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_version_id"], ["workflow_versions.id"], name=op.f("fk_runs_workflow_version_id_workflow_versions")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
    )

    op.create_table(
        "attempts",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("status", attempt_status, nullable=False),
        sa.Column("retry_of_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["retry_of_attempt_id"], ["attempts.id"], name=op.f("fk_attempts_retry_of_attempt_id_attempts")),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_attempts_run_id_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attempts")),
        sa.UniqueConstraint("run_id", "number", name="uq_attempts_run_number"),
    )

    op.create_table(
        "flows",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("compiled_plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", flow_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"], name=op.f("fk_flows_attempt_id_attempts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["compiled_plan_id"], ["compiled_plans.id"], name=op.f("fk_flows_compiled_plan_id_compiled_plans")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_flows")),
    )

    op.create_table(
        "flow_nodes",
        sa.Column("flow_id", sa.Uuid(), nullable=False),
        sa.Column("compiled_plan_node_id", sa.Uuid(), nullable=False),
        sa.Column("parent_flow_node_id", sa.Uuid(), nullable=True),
        sa.Column("node_key", sa.String(length=128), nullable=False),
        sa.Column("state", flow_node_state, nullable=False),
        sa.Column("iteration_index", sa.Integer(), nullable=False),
        sa.Column("status_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["compiled_plan_node_id"], ["compiled_plan_nodes.id"], name=op.f("fk_flow_nodes_compiled_plan_node_id_compiled_plan_nodes")),
        sa.ForeignKeyConstraint(["flow_id"], ["flows.id"], name=op.f("fk_flow_nodes_flow_id_flows"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_flow_node_id"], ["flow_nodes.id"], name=op.f("fk_flow_nodes_parent_flow_node_id_flow_nodes")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_flow_nodes")),
        sa.UniqueConstraint("flow_id", "node_key", name="uq_flow_nodes_flow_node_key"),
    )

    op.create_table(
        "node_checkpoints",
        sa.Column("flow_id", sa.Uuid(), nullable=False),
        sa.Column("flow_node_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("status", checkpoint_status, nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("failure_signature", sa.String(length=256), nullable=True),
        sa.Column("recommended_next_action", sa.String(length=128), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["flow_id"], ["flows.id"], name=op.f("fk_node_checkpoints_flow_id_flows"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["flow_node_id"], ["flow_nodes.id"], name=op.f("fk_node_checkpoints_flow_node_id_flow_nodes"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_node_checkpoints")),
        sa.UniqueConstraint("flow_node_id", "sequence_no", name="uq_node_checkpoints_node_sequence"),
    )

    op.create_table(
        "approvals",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=True),
        sa.Column("flow_node_id", sa.Uuid(), nullable=True),
        sa.Column("status", approval_status, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resolution_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"], name=op.f("fk_approvals_attempt_id_attempts")),
        sa.ForeignKeyConstraint(["flow_node_id"], ["flow_nodes.id"], name=op.f("fk_approvals_flow_node_id_flow_nodes")),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_approvals_run_id_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approvals")),
    )


def downgrade() -> None:
    bind = op.get_bind()
    approval_status = postgresql.ENUM("not_required", "pending", "approved", "rejected", "expired", name="approval_status", create_type=False)
    checkpoint_status = postgresql.ENUM("green", "retry", "blocked", "needs_approval", name="checkpoint_status", create_type=False)
    flow_node_state = postgresql.ENUM("ready", "running", "waiting", "paused", "done", "failed", name="flow_node_state", create_type=False)
    flow_status = postgresql.ENUM("pending", "running", "blocked", "failed", "succeeded", "cancelled", name="flow_status", create_type=False)
    attempt_status = postgresql.ENUM("pending", "running", "blocked", "failed", "succeeded", "cancelled", name="attempt_status", create_type=False)
    run_status = postgresql.ENUM("pending", "running", "blocked", "failed", "succeeded", "cancelled", name="run_status", create_type=False)
    task_status = postgresql.ENUM("pending", "running", "blocked", "failed", "succeeded", "cancelled", name="task_status", create_type=False)
    flow_edge_kind = postgresql.ENUM("control", "dependency", name="flow_edge_kind", create_type=False)
    workflow_mode = postgresql.ENUM(
        "plan",
        "persistent_execute",
        "review",
        "wait",
        "pause",
        "sync",
        name="workflow_mode",
        create_type=False,
    )
    skill_provider = postgresql.ENUM("openclaw", "local", "remote", name="skill_provider", create_type=False)
    definition_version_status = postgresql.ENUM("draft", "published", "archived", name="definition_version_status", create_type=False)

    op.drop_table("approvals")
    op.drop_table("node_checkpoints")
    op.drop_table("flow_nodes")
    op.drop_table("flows")
    op.drop_table("attempts")
    op.drop_table("runs")
    op.drop_index(op.f("ix_compiled_plans_plan_hash"), table_name="compiled_plans")
    op.drop_table("compiled_plan_edges")
    op.drop_table("compiled_plan_nodes")
    op.drop_table("compiled_plans")
    op.drop_table("tasks")
    op.drop_table("skill_versions")
    op.drop_table("workflow_versions")
    op.drop_table("policy_versions")
    op.drop_table("role_versions")
    op.drop_index(op.f("ix_skill_registry_key"), table_name="skill_registry")
    op.drop_table("skill_registry")
    op.drop_index(op.f("ix_workflow_definitions_key"), table_name="workflow_definitions")
    op.drop_table("workflow_definitions")
    op.drop_index(op.f("ix_policy_definitions_key"), table_name="policy_definitions")
    op.drop_table("policy_definitions")
    op.drop_index(op.f("ix_role_definitions_key"), table_name="role_definitions")
    op.drop_table("role_definitions")

    approval_status.drop(bind, checkfirst=True)
    checkpoint_status.drop(bind, checkfirst=True)
    flow_node_state.drop(bind, checkfirst=True)
    flow_status.drop(bind, checkfirst=True)
    attempt_status.drop(bind, checkfirst=True)
    run_status.drop(bind, checkfirst=True)
    task_status.drop(bind, checkfirst=True)
    flow_edge_kind.drop(bind, checkfirst=True)
    workflow_mode.drop(bind, checkfirst=True)
    skill_provider.drop(bind, checkfirst=True)
    definition_version_status.drop(bind, checkfirst=True)
