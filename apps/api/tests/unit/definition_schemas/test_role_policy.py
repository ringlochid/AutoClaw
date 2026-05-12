from __future__ import annotations

from typing import Any

import pytest
from app.schemas.definitions import (
    PolicyDefinitionFile,
    PolicyDefinitionInput,
    RoleDefinitionFile,
    RoleDefinitionInput,
)
from pydantic import ValidationError

from .support import RoleOrPolicyDefinitionModel


@pytest.mark.parametrize(
    ("model_type", "payload"),
    [
        (
            RoleDefinitionFile,
            {
                "id": "review-role",
                "description": "Role without file kind.",
                "allowed_node_kinds": ["parent"],
            },
        ),
        (
            PolicyDefinitionFile,
            {
                "id": "review-policy",
                "description": "Policy without file kind.",
                "applies_to": ["parent"],
                "budget_spec": {"child_assignment_limit": 3},
            },
        ),
    ],
)
def test_role_and_policy_file_models_require_kind(
    model_type: type[RoleDefinitionFile] | type[PolicyDefinitionFile],
    payload: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError, match="kind"):
        model_type.model_validate(payload)


@pytest.mark.parametrize(
    ("model_type", "payload", "error_match"),
    [
        (
            RoleDefinitionInput,
            {
                "id": "review-role",
                "description": "Legacy role default policy should be rejected.",
                "allowed_node_kinds": ["parent"],
                "default_policy": "review-policy",
            },
            "default_policy",
        ),
        (
            RoleDefinitionInput,
            {
                "id": "review-role",
                "description": "Legacy allowed_kinds should be rejected.",
                "allowed_kinds": ["parent"],
            },
            "allowed_kinds|allowed_node_kinds",
        ),
        (
            PolicyDefinitionInput,
            {
                "id": "review-policy",
                "description": "Legacy defaults should be rejected.",
                "applies_to": ["parent"],
                "defaults": {"retry_budget": 1},
            },
            "defaults",
        ),
        (
            PolicyDefinitionInput,
            {
                "id": "review-policy",
                "description": "Legacy rules should be rejected.",
                "applies_to": ["worker"],
                "rules": {"allowed_tools": ["shell"]},
            },
            "rules",
        ),
        (
            PolicyDefinitionInput,
            {
                "id": "review-policy",
                "description": "Legacy same-attempt grammar should be rejected.",
                "applies_to": ["worker"],
                "same_attempt_redispatch_limit": 1,
            },
            "same_attempt_redispatch_limit",
        ),
        (
            PolicyDefinitionInput,
            {
                "id": "review-policy",
                "description": "Legacy budget grammar should be rejected.",
                "applies_to": ["worker"],
                "budget_spec": {"same_attempt_continue_limit": 1},
            },
            "same_attempt_continue_limit",
        ),
        (
            PolicyDefinitionInput,
            {
                "id": "review-policy",
                "description": "Budget limits must reject string numerics.",
                "applies_to": ["worker"],
                "budget_spec": {"retry_limit": "2"},
            },
            "retry_limit",
        ),
        (
            RoleDefinitionInput,
            {
                "id": "review-role",
                "description": "Missing allowed_node_kinds should fail required-field validation.",
            },
            "allowed_node_kinds",
        ),
        (
            PolicyDefinitionInput,
            {
                "id": "review-policy",
                "description": "Missing applies_to should fail required-field validation.",
            },
            "applies_to",
        ),
    ],
)
def test_role_and_policy_definition_schema_reject_matrix_parity(
    model_type: RoleOrPolicyDefinitionModel,
    payload: dict[str, Any],
    error_match: str,
) -> None:
    with pytest.raises(ValidationError, match=error_match):
        model_type.model_validate(payload)
