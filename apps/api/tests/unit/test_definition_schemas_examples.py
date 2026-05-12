from __future__ import annotations

from typing import Any

import pytest
from app.schemas.definitions import (
    PolicyDefinitionFile,
    PolicyDefinitionInput,
    RoleDefinitionFile,
    RoleDefinitionInput,
    WorkflowDefinitionFile,
)
from tests.unit.definition_schema_test_support import (
    AUTHORED_DEFINITIONS_ROOT,
    WORKFLOW_EXAMPLES_ROOT,
    RoleOrPolicyDefinitionModel,
    load_first_yaml_fence,
    load_role_policy_schema_examples,
    load_workflow_schema_worked_examples,
    load_yaml,
    workflow_validation_context,
)


@pytest.mark.parametrize(
    ("workflow_fixture", "example_doc"),
    [
        ("minimal_implement_change.yaml", "minimal.md"),
        ("normal_parent_first_release.yaml", "normal.md"),
        ("maximal_parent_first_release.yaml", "maximal.md"),
    ],
)
def test_authored_workflow_fixtures_match_canonical_example_docs(
    workflow_fixture: str,
    example_doc: str,
) -> None:
    fixture_payload = load_yaml(AUTHORED_DEFINITIONS_ROOT / "workflows" / workflow_fixture)
    example_payload = load_first_yaml_fence(WORKFLOW_EXAMPLES_ROOT / example_doc)

    assert fixture_payload == example_payload


def test_workflow_definition_schema_worked_yaml_examples_validate() -> None:
    examples = load_workflow_schema_worked_examples()
    validation_context = workflow_validation_context(AUTHORED_DEFINITIONS_ROOT)

    assert [payload["id"] for payload in examples] == ["auth-refresh-bugfix"]

    for payload in examples:
        validated = WorkflowDefinitionFile.model_validate(
            payload,
            context=validation_context,
        )
        assert validated.id == payload["id"]


@pytest.mark.parametrize("payload", load_role_policy_schema_examples())
def test_role_and_policy_definition_schema_worked_yaml_examples_validate(
    payload: dict[str, Any],
) -> None:
    model_type: RoleOrPolicyDefinitionModel
    if "allowed_node_kinds" in payload:
        model_type = RoleDefinitionFile if payload.get("kind") == "role" else RoleDefinitionInput
    else:
        model_type = (
            PolicyDefinitionFile if payload.get("kind") == "policy" else PolicyDefinitionInput
        )

    validated = model_type.model_validate(payload)

    assert validated.id == payload["id"]
