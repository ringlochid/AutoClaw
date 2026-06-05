from __future__ import annotations

import autoclaw.definitions.contracts as definition_schemas
from autoclaw.definitions.contracts import WorkflowDefinitionFile

from .support import (
    AUTHORED_DEFINITIONS_ROOT,
    minimal_workflow_payload,
    workflow_validation_context,
)


def test_minimal_workflow_fixture_validates_against_authored_catalog() -> None:
    validated = WorkflowDefinitionFile.model_validate(
        {"kind": "workflow", **minimal_workflow_payload()},
        context=workflow_validation_context(AUTHORED_DEFINITIONS_ROOT),
    )

    assert validated.id == "minimal-implement-change"
    assert validated.root.id == "root"
    assert validated.root.children is not None
    assert [child.id for child in validated.root.children] == ["implement_change"]


def test_definitions_package_does_not_export_private_validation_helpers() -> None:
    assert not hasattr(definition_schemas, "_build_dependency_graph")
    assert not hasattr(definition_schemas, "_flatten_workflow")
    assert not hasattr(definition_schemas, "_infer_node_kind")
    assert not hasattr(definition_schemas, "_validate_acyclic_dependency_graph")
