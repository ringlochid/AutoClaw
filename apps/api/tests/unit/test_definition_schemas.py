from __future__ import annotations

from app.schemas.definitions import WorkflowDefinitionFile
from tests.unit.definition_schema_test_support import (
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
