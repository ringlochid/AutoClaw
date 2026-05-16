from __future__ import annotations

from ..paths import DOCS_ROOT

REDESIGN_REQUIRED_MARKERS = {
    DOCS_ROOT / "redesign" / "interfaces" / "distribution-and-database-support-matrix.md": [
        "pipx install autoclaw",
        'pipx install "autoclaw[postgres]"',
        "make docker-up",
        "make test-api-db",
        "make docker-down",
    ],
    DOCS_ROOT / "redesign" / "how-to" / "install-and-onboard.md": [
        "autoclaw init",
        "autoclaw doctor",
        "autoclaw serve",
    ],
    DOCS_ROOT / "redesign" / "how-to" / "use-postgres.md": [
        "AUTOCLAW_DATABASE_URL",
        "make docker-up",
        "make test-api-db",
        "make docker-down",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "README.md": [
        "api-schema-appendix.md",
        "api-machine-catalog.yaml",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "api-machine-catalog.yaml": [
        "version: 1",
        "search_definitions",
        "/definitions/{kind}/{key}",
        "maps_to_http: q",
    ],
    DOCS_ROOT / "redesign" / "workflows" / "README.md": [
        "Workflow schema appendix",
    ],
    DOCS_ROOT / "redesign" / "prompt-layer" / "README.md": [
        "prompt-resource-usage-appendix.md",
        "machine-contract.md",
    ],
    DOCS_ROOT / "redesign" / "architecture" / "assignment-contract.md": [
        "assignment_intent",
        "supplemental_durable_context",
        "`produces` is a requirement list only",
    ],
    DOCS_ROOT / "redesign" / "architecture" / "checkpoint-contract.md": [
        "record_checkpoint",
        "produced_artifacts",
        "transient_surfaces",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "api-surface-and-trust-lane-map.md": [
        "api-schema-appendix.md",
        "DispatchContextRead",
        "CheckpointWrite",
        "ParentToolSuccess",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "plugin-tool-reference.md": [
        "list_definition_versions(kind, key, limit?, cursor?, sort?)",
        "search_definitions(kind, query?, limit?, cursor?, sort?, allowed_node_kind?, applies_to?)",
        "get_definition(kind, key)",
        "## Operator-safe external lane",
        "record_checkpoint(session_key, task_id, checkpoint)",
        "upload_definition(definition_path)",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "api-schema-appendix.md": [
        "## Shared object ownership",
        "### `DefinitionUploadRequest`",
        "### `TaskStartResponse`",
        "### `DispatchContextRead`",
        "### `CheckpointWrite`",
        "### `OperatorFlowSnapshotResponse`",
        "### `ParentToolSuccess`",
        "### `DefinitionListQuery`",
        "### `DefinitionRevisionHistoryQuery`",
        "### `RuntimeTaskListQuery`",
    ],
    DOCS_ROOT / "redesign" / "workflows" / "task-compose-schema.md": [
        "If `roots.workspace` is omitted, it defaults to `ensure_task_default`.",
        "If `roots.context` is omitted, it defaults to `ensure_task_default`.",
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "definition-ingest-and-upload-contract.md": [
        (
            "autoclaw definitions import --file <definition_path> "
            "[--overwrite reject|allow_new_revision]"
        ),
        (
            "zero-arg `autoclaw definitions import` is the canonical shallow "
            "current-working-directory scan/import path"
        ),
    ],
    DOCS_ROOT / "redesign" / "interfaces" / "cli-surface-and-operator-workflows.md": [
        "`autoclaw definitions ...`",
        (
            "autoclaw definitions import --file <definition_path> "
            "[--overwrite reject|allow_new_revision]"
        ),
        "zero-arg `autoclaw definitions import` is a shallow current-working-directory scan only",
    ],
}
