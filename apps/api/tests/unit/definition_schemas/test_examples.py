from __future__ import annotations

from typing import Any

import pytest
from autoclaw.definitions.contracts import (
    PolicyDefinitionFile,
    PolicyDefinitionInput,
    RoleDefinitionFile,
    RoleDefinitionInput,
    WorkflowDefinitionFile,
)

from .support import (
    WORKFLOW_EXAMPLES_ROOT,
    RoleOrPolicyDefinitionModel,
    load_first_yaml_fence,
    load_role_policy_schema_examples,
    load_workflow_schema_worked_examples,
    load_yaml,
    resolve_committed_seed_definitions_root,
    workflow_validation_context,
)


@pytest.mark.parametrize(
    ("workflow_fixture", "example_doc"),
    [
        ("bounded_change.yaml", "bounded-change.md"),
        ("reviewed_change_release.yaml", "reviewed-change-release.md"),
        ("staged_delivery_release.yaml", "staged-delivery-release.md"),
    ],
)
def test_packaged_workflow_seed_definitions_match_canonical_example_docs(
    workflow_fixture: str,
    example_doc: str,
) -> None:
    with resolve_committed_seed_definitions_root() as definitions_root:
        fixture_payload = load_yaml(definitions_root / "workflows" / workflow_fixture)
    example_payload = load_first_yaml_fence(WORKFLOW_EXAMPLES_ROOT / example_doc)

    assert fixture_payload == example_payload


def test_workflow_definition_schema_worked_yaml_examples_validate() -> None:
    examples = load_workflow_schema_worked_examples()
    with resolve_committed_seed_definitions_root() as definitions_root:
        validation_context = workflow_validation_context(definitions_root)

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
