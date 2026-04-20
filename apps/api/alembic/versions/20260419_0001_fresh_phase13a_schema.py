"""fresh phase13a schema baseline"""

revision = '20260419_0001'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.create_table(
        'policy_definitions',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_policy_definitions_key', 'policy_definitions', ['key'], unique=True)

    op.create_table(
        'role_definitions',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_role_definitions_key', 'role_definitions', ['key'], unique=True)

    op.create_table(
        'skill_registry',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('provider', sa.Enum('openclaw', 'local', 'remote', name='skill_provider', native_enum=False), nullable=False),
        sa.Column('source_uri', sa.String(length=512), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_registry_key', 'skill_registry', ['key'], unique=True)

    op.create_table(
        'workflow_definitions',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workflow_definitions_key', 'workflow_definitions', ['key'], unique=True)

    op.create_table(
        'tasks',
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'running', 'blocked', 'failed', 'succeeded', 'cancelled', name='task_status', native_enum=False), nullable=False),
        sa.Column('input_payload', JSON, nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'workspace_roots',
        sa.Column('scope', sa.Enum('task', 'shared', name='resource_scope', native_enum=False), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('storage_uri', sa.String(length=512), nullable=False),
        sa.Column('kind', sa.Enum('repo', 'docs', 'mixed', 'generated', name='workspace_root_kind', native_enum=False), nullable=False),
        sa.Column('mode', sa.Enum('snapshot', 'overlay', 'checkout', 'scratch', name='workspace_root_mode', native_enum=False), nullable=False),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('content_hash', sa.String(length=128), nullable=False),
        sa.Column('last_indexed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', JSON, nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workspace_roots_key', 'workspace_roots', ['key'], unique=True)

    op.create_table(
        'context_spaces',
        sa.Column('scope', sa.Enum('task', 'shared', name='resource_scope', native_enum=False), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('storage_uri', sa.String(length=512), nullable=False),
        sa.Column('source_workspace_root_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('content_hash', sa.String(length=128), nullable=False),
        sa.Column('last_indexed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', JSON, nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['source_workspace_root_id'], ['workspace_roots.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_context_spaces_key', 'context_spaces', ['key'], unique=True)

    op.create_table(
        'manifest_roots',
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('storage_uri', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('metadata', JSON, nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'key', name='uq_manifest_roots_task_key'),
    )

    op.create_table(
        'policy_versions',
        sa.Column('policy_definition_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='definition_version_status', native_enum=False), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', JSON, nullable=False),
        sa.Column('requested_by', sa.String(length=255), nullable=True),
        sa.Column('audit', JSON, nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['policy_definition_id'], ['policy_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_definition_id', 'version', name='uq_policy_versions_definition_version'),
    )
    op.create_index('ix_policy_versions_definition_status_version', 'policy_versions', ['policy_definition_id', 'status', 'version'])

    op.create_table(
        'role_versions',
        sa.Column('role_definition_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='definition_version_status', native_enum=False), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', JSON, nullable=False),
        sa.Column('requested_by', sa.String(length=255), nullable=True),
        sa.Column('audit', JSON, nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['role_definition_id'], ['role_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_definition_id', 'version', name='uq_role_versions_definition_version'),
    )
    op.create_index('ix_role_versions_definition_status_version', 'role_versions', ['role_definition_id', 'status', 'version'])

    op.create_table(
        'skill_versions',
        sa.Column('skill_registry_id', sa.Uuid(), nullable=False),
        sa.Column('version_label', sa.String(length=128), nullable=False),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='definition_version_status', native_enum=False), nullable=False),
        sa.Column('source_ref', sa.String(length=256), nullable=True),
        sa.Column('manifest', JSON, nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['skill_registry_id'], ['skill_registry.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('skill_registry_id', 'version_label', name='uq_skill_versions_registry_version'),
    )
    op.create_index('ix_skill_versions_registry_status', 'skill_versions', ['skill_registry_id', 'status'])

    op.create_table(
        'workflow_versions',
        sa.Column('workflow_definition_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('draft', 'published', 'archived', name='definition_version_status', native_enum=False), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', JSON, nullable=False),
        sa.Column('requested_by', sa.String(length=255), nullable=True),
        sa.Column('audit', JSON, nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['workflow_definition_id'], ['workflow_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_definition_id', 'version', name='uq_workflow_versions_definition_version'),
    )
    op.create_index('ix_workflow_versions_definition_status_version', 'workflow_versions', ['workflow_definition_id', 'status', 'version'])

    op.create_table(
        'compiled_plans',
        sa.Column('workflow_version_id', sa.Uuid(), nullable=False),
        sa.Column('compiler_version', sa.String(length=64), nullable=False),
        sa.Column('plan_hash', sa.String(length=128), nullable=False),
        sa.Column('source_snapshot', JSON, nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['workflow_version_id'], ['workflow_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_compiled_plans_plan_hash', 'compiled_plans', ['plan_hash'], unique=True)


    op.create_table(
        'task_resource_bindings',
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('binding_role', sa.Enum('primary_workspace', 'reference_workspace', 'primary_context', 'reference_context', 'manifest_root', name='task_resource_binding_role', native_enum=False), nullable=False),
        sa.Column('workspace_root_id', sa.Uuid(), nullable=True),
        sa.Column('context_space_id', sa.Uuid(), nullable=True),
        sa.Column('manifest_root_id', sa.Uuid(), nullable=True),
        sa.Column('mode', sa.Enum('use_existing', 'ensure_task_primary', 'ensure_task_root', 'clone_from', 'seed_from', name='task_resource_binding_mode', native_enum=False), nullable=False),
        sa.Column('read_only', sa.Boolean(), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.Column('metadata', JSON, nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_root_id'], ['workspace_roots.id']),
        sa.ForeignKeyConstraint(['context_space_id'], ['context_spaces.id']),
        sa.ForeignKeyConstraint(['manifest_root_id'], ['manifest_roots.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("(CASE WHEN workspace_root_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN context_space_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN manifest_root_id IS NOT NULL THEN 1 ELSE 0 END) = 1", name='ck_task_resource_bindings_exactly_one_target'),
        sa.CheckConstraint("(binding_role != 'manifest_root') OR (manifest_root_id IS NOT NULL)", name='ck_task_resource_bindings_manifest_role_target'),
    )
    op.create_index('ix_task_resource_bindings_task_role', 'task_resource_bindings', ['task_id', 'binding_role'])
    op.create_index(
        'uq_task_resource_bindings_primary_workspace',
        'task_resource_bindings',
        ['task_id'],
        unique=True,
        sqlite_where=sa.text("binding_role = 'primary_workspace'"),
        postgresql_where=sa.text("binding_role = 'primary_workspace'"),
    )
    op.create_index(
        'uq_task_resource_bindings_primary_context',
        'task_resource_bindings',
        ['task_id'],
        unique=True,
        sqlite_where=sa.text("binding_role = 'primary_context'"),
        postgresql_where=sa.text("binding_role = 'primary_context'"),
    )
    op.create_index(
        'uq_task_resource_bindings_manifest_root',
        'task_resource_bindings',
        ['task_id'],
        unique=True,
        sqlite_where=sa.text("binding_role = 'manifest_root'"),
        postgresql_where=sa.text("binding_role = 'manifest_root'"),
    )

    op.create_table(
        'task_composes',
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('workflow_version_id', sa.Uuid(), nullable=True),
        sa.Column('compiled_plan_id', sa.Uuid(), nullable=True),
        sa.Column('entrypoint', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=64), nullable=False),
        sa.Column('metadata', JSON, nullable=False),
        sa.Column('input_payload', JSON, nullable=False),
        sa.Column('context_refs', JSON, nullable=False),
        sa.Column('skill_dependencies', JSON, nullable=False),
        sa.Column('workspace_root_uri', sa.String(length=512), nullable=True),
        sa.Column('context_root_uri', sa.String(length=512), nullable=True),
        sa.Column('manifest_root_uri', sa.String(length=512), nullable=True),
        sa.Column('materialization_root', sa.String(length=512), nullable=False),
        sa.Column('superseded_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_version_id'], ['workflow_versions.id']),
        sa.ForeignKeyConstraint(['compiled_plan_id'], ['compiled_plans.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', name='uq_task_composes_task_id'),
    )

    op.create_table(
        'compiled_plan_nodes',
        sa.Column('compiled_plan_id', sa.Uuid(), nullable=False),
        sa.Column('node_key', sa.String(length=128), nullable=False),
        sa.Column('parent_node_key', sa.String(length=128), nullable=True),
        sa.Column('role_version_id', sa.Uuid(), nullable=True),
        sa.Column('policy_version_id', sa.Uuid(), nullable=True),
        sa.Column('mode', sa.Enum('plan', 'persistent_execute', 'review', 'wait', 'pause', 'sync', name='workflow_mode', native_enum=False), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('skill_bindings', JSON, nullable=False),
        sa.Column('effective_payload', JSON, nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['compiled_plan_id'], ['compiled_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['policy_version_id'], ['policy_versions.id']),
        sa.ForeignKeyConstraint(['role_version_id'], ['role_versions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('compiled_plan_id', 'node_key', name='uq_compiled_plan_nodes_plan_node_key'),
    )
    op.create_index('ix_compiled_plan_nodes_plan_order', 'compiled_plan_nodes', ['compiled_plan_id', 'order_index'])

    op.create_table(
        'compiled_plan_edges',
        sa.Column('compiled_plan_id', sa.Uuid(), nullable=False),
        sa.Column('from_node_key', sa.String(length=128), nullable=False),
        sa.Column('to_node_key', sa.String(length=128), nullable=False),
        sa.Column('edge_kind', sa.Enum('control', 'dependency', name='flow_edge_kind', native_enum=False), nullable=False),
        sa.Column('condition_expr', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['compiled_plan_id'], ['compiled_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_compiled_plan_edges_plan_order', 'compiled_plan_edges', ['compiled_plan_id', 'order_index'])

    op.create_table(
        'role_version_skill_bindings',
        sa.Column('role_version_id', sa.Uuid(), nullable=False),
        sa.Column('skill_version_id', sa.Uuid(), nullable=False),
        sa.Column('state', sa.Enum('allowed', 'preferred', 'required', 'blocked', name='skill_binding_state', native_enum=False), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['role_version_id'], ['role_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_version_id'], ['skill_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_version_id', 'skill_version_id', name='uq_role_version_skill_bindings_pair'),
    )
    op.create_index('ix_role_version_skill_bindings_role_version', 'role_version_skill_bindings', ['role_version_id'])

    op.create_table(
        'workflow_version_skill_bindings',
        sa.Column('workflow_version_id', sa.Uuid(), nullable=False),
        sa.Column('skill_version_id', sa.Uuid(), nullable=False),
        sa.Column('state', sa.Enum('allowed', 'preferred', 'required', 'blocked', name='skill_binding_state', native_enum=False), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['workflow_version_id'], ['workflow_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_version_id'], ['skill_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_version_id', 'skill_version_id', name='uq_workflow_version_skill_bindings_pair'),
    )
    op.create_index('ix_workflow_version_skill_bindings_workflow_version', 'workflow_version_skill_bindings', ['workflow_version_id'])

    op.create_table(
        'workflow_node_skill_bindings',
        sa.Column('workflow_version_id', sa.Uuid(), nullable=False),
        sa.Column('node_key', sa.String(length=128), nullable=False),
        sa.Column('skill_version_id', sa.Uuid(), nullable=False),
        sa.Column('state', sa.Enum('allowed', 'preferred', 'required', 'blocked', name='skill_binding_state', native_enum=False), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['workflow_version_id'], ['workflow_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_version_id'], ['skill_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_version_id', 'node_key', 'skill_version_id', name='uq_workflow_node_skill_bindings_triplet'),
    )
    op.create_index('ix_workflow_node_skill_bindings_workflow_version_node_key', 'workflow_node_skill_bindings', ['workflow_version_id', 'node_key'])

    op.create_table(
        'flows',
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('seed_compiled_plan_id', sa.Uuid(), nullable=False),
        sa.Column('active_flow_revision_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'running', 'blocked', 'paused', 'failed', 'succeeded', 'cancelled', name='flow_status', native_enum=False), nullable=False),
        sa.Column('execution_no', sa.Integer(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seed_compiled_plan_id'], ['compiled_plans.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_flows_task_status', 'flows', ['task_id', 'status'])
    op.create_index('ix_flows_active_flow_revision_id', 'flows', ['active_flow_revision_id'])

    op.create_table(
        'flow_revisions',
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('revision_no', sa.Integer(), nullable=False),
        sa.Column('compiled_plan_id', sa.Uuid(), nullable=False),
        sa.Column('parent_flow_revision_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.Enum('candidate', 'active', 'retired', 'aborted', name='flow_revision_status', native_enum=False), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('source_patch_payload', JSON, nullable=False),
        sa.Column('adopted_from_node_plan_revision_id', sa.Uuid(), nullable=True),
        sa.Column('adopted_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['compiled_plan_id'], ['compiled_plans.id']),
        sa.ForeignKeyConstraint(['parent_flow_revision_id'], ['flow_revisions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flow_id', 'revision_no', name='uq_flow_revisions_flow_revision_no'),
    )

    op.create_table(
        'flow_nodes',
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('flow_revision_id', sa.Uuid(), nullable=False),
        sa.Column('source_compiled_plan_node_id', sa.Uuid(), nullable=True),
        sa.Column('parent_flow_node_id', sa.Uuid(), nullable=True),
        sa.Column('supersedes_flow_node_id', sa.Uuid(), nullable=True),
        sa.Column('logical_node_key', sa.String(length=256), nullable=False),
        sa.Column('node_key', sa.String(length=128), nullable=False),
        sa.Column('node_path', sa.String(length=256), nullable=False),
        sa.Column('state', sa.Enum('ready', 'running', 'waiting', 'paused', 'done', 'failed', name='flow_node_state', native_enum=False), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('status_payload', JSON, nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_revision_id'], ['flow_revisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_compiled_plan_node_id'], ['compiled_plan_nodes.id']),
        sa.ForeignKeyConstraint(['parent_flow_node_id'], ['flow_nodes.id']),
        sa.ForeignKeyConstraint(['supersedes_flow_node_id'], ['flow_nodes.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flow_revision_id', 'node_key', name='uq_flow_nodes_revision_node_key'),
    )
    op.create_index('ix_flow_nodes_flow_revision_order', 'flow_nodes', ['flow_id', 'flow_revision_id', 'order_index'])
    op.create_index('ix_flow_nodes_flow_logical_node', 'flow_nodes', ['flow_id', 'logical_node_key'])

    op.create_table(
        'flow_edges',
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('flow_revision_id', sa.Uuid(), nullable=False),
        sa.Column('from_flow_node_id', sa.Uuid(), nullable=False),
        sa.Column('to_flow_node_id', sa.Uuid(), nullable=False),
        sa.Column('edge_kind', sa.Enum('control', 'dependency', name='flow_edge_kind', native_enum=False), nullable=False),
        sa.Column('condition_expr', sa.Text(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['flow_revision_id'], ['flow_revisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_flow_node_id'], ['flow_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_flow_node_id'], ['flow_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_flow_edges_flow_revision_id', 'flow_edges', ['flow_id', 'flow_revision_id'])

    op.create_table(
        'node_attempts',
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('flow_revision_id', sa.Uuid(), nullable=False),
        sa.Column('flow_node_id', sa.Uuid(), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'blocked', 'failed', 'succeeded', 'cancelled', 'aborted', name='node_attempt_status', native_enum=False), nullable=False),
        sa.Column('retry_of_node_attempt_id', sa.Uuid(), nullable=True),
        sa.Column('failure_signature', sa.String(length=256), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_revision_id'], ['flow_revisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_node_id'], ['flow_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['retry_of_node_attempt_id'], ['node_attempts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flow_node_id', 'number', name='uq_node_attempts_node_number'),
    )
    op.create_index('ix_node_attempts_flow_node_number', 'node_attempts', ['flow_id', 'flow_node_id', 'number'])

    op.create_table(
        'node_sessions',
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('flow_node_id', sa.Uuid(), nullable=False),
        sa.Column('node_attempt_id', sa.Uuid(), nullable=True),
        sa.Column('provider_session_key', sa.String(length=256), nullable=False),
        sa.Column('status', sa.Enum('idle', 'active', 'ended', name='node_session_status', native_enum=False), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_node_id'], ['flow_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_attempt_id'], ['node_attempts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('flow_node_id', name='uq_node_sessions_flow_node_id'),
        sa.UniqueConstraint('provider_session_key', name='uq_node_sessions_provider_session_key'),
    )

    op.create_table(
        'node_checkpoints',
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('flow_node_id', sa.Uuid(), nullable=False),
        sa.Column('node_attempt_id', sa.Uuid(), nullable=False),
        sa.Column('sequence_no', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('green', 'retry', 'blocked', 'needs_approval', name='checkpoint_status', native_enum=False), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('payload', JSON, nullable=False),
        sa.Column('failure_signature', sa.String(length=256), nullable=True),
        sa.Column('recommended_next_action', sa.Text(), nullable=True),
        sa.Column('wait_reason', sa.Enum('approval', 'dependency', 'watchdog', 'operator', 'context', name='wait_reason', native_enum=False), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_node_id'], ['flow_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_attempt_id'], ['node_attempts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('node_attempt_id', 'sequence_no', name='uq_node_checkpoints_attempt_sequence'),
    )
    op.create_index('ix_node_checkpoints_flow_attempt', 'node_checkpoints', ['flow_id', 'node_attempt_id'])

    op.create_table(
        'approvals',
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('flow_node_id', sa.Uuid(), nullable=True),
        sa.Column('node_attempt_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.Enum('not_required', 'pending', 'approved', 'rejected', 'expired', name='approval_status', native_enum=False), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('request_payload', JSON, nullable=False),
        sa.Column('resolution_payload', JSON, nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_node_id'], ['flow_nodes.id']),
        sa.ForeignKeyConstraint(['node_attempt_id'], ['node_attempts.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'context_items',
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('flow_id', sa.Uuid(), nullable=True),
        sa.Column('flow_revision_id', sa.Uuid(), nullable=True),
        sa.Column('flow_node_id', sa.Uuid(), nullable=True),
        sa.Column('node_attempt_id', sa.Uuid(), nullable=True),
        sa.Column('source_checkpoint_id', sa.Uuid(), nullable=True),
        sa.Column('scope', sa.Enum('task_shared', 'flow_shared', 'node_private', 'attempt_scratch', name='context_item_scope', native_enum=False), nullable=False),
        sa.Column('kind', sa.Enum('fact', 'decision', 'summary', 'suggestion', 'note', 'artifact', 'log', name='context_item_kind', native_enum=False), nullable=False),
        sa.Column('visibility_policy', JSON, nullable=False),
        sa.Column('status', sa.Enum('draft', 'published', 'superseded', 'archived', name='context_item_status', native_enum=False), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('storage_uri', sa.String(length=512), nullable=False),
        sa.Column('content_hash', sa.String(length=128), nullable=False),
        sa.Column('metadata', JSON, nullable=False),
        sa.Column('published_by', sa.String(length=128), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id']),
        sa.ForeignKeyConstraint(['flow_node_id'], ['flow_nodes.id']),
        sa.ForeignKeyConstraint(['node_attempt_id'], ['node_attempts.id']),
        sa.ForeignKeyConstraint(['source_checkpoint_id'], ['node_checkpoints.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'context_manifests',
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('flow_node_id', sa.Uuid(), nullable=False),
        sa.Column('node_attempt_id', sa.Uuid(), nullable=False),
        sa.Column('node_session_id', sa.Uuid(), nullable=True),
        sa.Column('manifest_root_id', sa.Uuid(), nullable=True),
        sa.Column('manifest_no', sa.Integer(), nullable=False),
        sa.Column('manifest_payload', JSON, nullable=False),
        sa.Column('manifest_hash', sa.String(length=128), nullable=False),
        sa.Column('status', sa.Enum('projected', 'acked', 'superseded', name='context_manifest_status', native_enum=False), nullable=False),
        sa.Column('projected_at', sa.DateTime(), nullable=False),
        sa.Column('acked_at', sa.DateTime(), nullable=True),
        sa.Column('ack_checkpoint_id', sa.Uuid(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['flow_node_id'], ['flow_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_attempt_id'], ['node_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_session_id'], ['node_sessions.id']),
        sa.ForeignKeyConstraint(['manifest_root_id'], ['manifest_roots.id']),
        sa.ForeignKeyConstraint(['ack_checkpoint_id'], ['node_checkpoints.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'node_plan_revisions',
        sa.Column('flow_id', sa.Uuid(), nullable=False),
        sa.Column('requesting_flow_node_id', sa.Uuid(), nullable=False),
        sa.Column('requesting_node_attempt_id', sa.Uuid(), nullable=True),
        sa.Column('base_flow_revision_id', sa.Uuid(), nullable=False),
        sa.Column('candidate_flow_revision_id', sa.Uuid(), nullable=True),
        sa.Column('patch_payload', JSON, nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('proposed', 'validating', 'validated', 'rejected', 'adopted', 'superseded', name='node_plan_revision_status', native_enum=False), nullable=False),
        sa.Column('error_text', sa.Text(), nullable=True),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.Column('adopted_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['flows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requesting_flow_node_id'], ['flow_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requesting_node_attempt_id'], ['node_attempts.id']),
        sa.ForeignKeyConstraint(['base_flow_revision_id'], ['flow_revisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_flow_revision_id'], ['flow_revisions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_node_plan_revisions_flow_status', 'node_plan_revisions', ['flow_id', 'status'])



def downgrade() -> None:
    raise NotImplementedError('fresh phase13a baseline only')
