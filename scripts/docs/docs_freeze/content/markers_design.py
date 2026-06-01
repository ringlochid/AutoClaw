from __future__ import annotations

from ..paths import DESIGN_ROOT

DESIGN_REQUIRED_MARKERS = {
    DESIGN_ROOT / "interfaces" / "distribution-and-database-support-matrix.md": [
        "pipx install autoclaw",
        'pipx install "autoclaw[postgres]"',
        "make docker-up",
        "make test-api-db",
        "make docker-down",
    ],
    DESIGN_ROOT / "how-to" / "install-and-onboard.md": [
        "autoclaw init",
        "autoclaw doctor",
        "autoclaw serve",
    ],
    DESIGN_ROOT / "how-to" / "use-postgres.md": [
        "AUTOCLAW_DATABASE_URL",
        "make docker-up",
        "make test-api-db",
        "make docker-down",
    ],
    DESIGN_ROOT / "interfaces" / "README.md": [
        "api-schema-appendix.md",
        "api-machine-catalog.yaml",
    ],
    DESIGN_ROOT / "interfaces" / "api-machine-catalog.yaml": [
        "version: 1",
        "search_definitions",
        "/definitions/{kind}/{key}",
        "maps_to_http: q",
    ],
    DESIGN_ROOT / "workflows" / "README.md": [
        "Workflow schema appendix",
    ],
    DESIGN_ROOT / "prompt-layer" / "README.md": [
        "prompt-resource-usage-appendix.md",
        "machine-contract.md",
    ],
    DESIGN_ROOT / "architecture" / "assignment-contract.md": [
        "assignment_intent",
        "supplemental_durable_context",
        "`produces` is a requirement list only",
    ],
    DESIGN_ROOT / "architecture" / "checkpoint-contract.md": [
        "record_checkpoint",
        "produced_artifacts",
        "transient_surfaces",
    ],
    DESIGN_ROOT / "interfaces" / "api-surface-and-trust-lane-map.md": [
        "api-schema-appendix.md",
        "DispatchContextRead",
        "CheckpointWrite",
        "ParentToolSuccess",
    ],
    DESIGN_ROOT / "interfaces" / "plugin-tool-reference.md": [
        "list_definition_versions(kind, key, limit?, cursor?, sort?)",
        "search_definitions(kind, query?, limit?, cursor?, sort?, allowed_node_kind?, applies_to?)",
        "get_definition(kind, key)",
        "## Operator-safe external lane",
        "record_checkpoint(session_key, task_id, checkpoint)",
        "upload_definition(definition_path)",
    ],
    DESIGN_ROOT / "interfaces" / "api-schema-appendix.md": [
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
    DESIGN_ROOT / "workflows" / "task-compose-schema.md": [
        "If `roots.workspace` is omitted, it defaults to `ensure_task_default`.",
        "If `roots.context` is omitted, it defaults to `ensure_task_default`.",
    ],
    DESIGN_ROOT / "interfaces" / "definition-ingest-and-upload-contract.md": [
        (
            "autoclaw definitions import --file <definition_path> "
            "[--overwrite reject|allow_new_revision]"
        ),
        (
            "zero-arg `autoclaw definitions import` is the canonical shallow "
            "current-working-directory scan/import path"
        ),
    ],
    DESIGN_ROOT / "interfaces" / "cli-surface-and-operator-workflows.md": [
        "`autoclaw definitions ...`",
        (
            "autoclaw definitions import --file <definition_path> "
            "[--overwrite reject|allow_new_revision]"
        ),
        "zero-arg `autoclaw definitions import` is a shallow current-working-directory scan only",
    ],
}
