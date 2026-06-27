from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from autoclaw.definitions.contracts import WorkflowDefinitionFile, WorkflowNodeInput
from pydantic import ValidationError

from .support import minimal_workflow_payload


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("inputs", {"legacy": "input"}),
        ("edges", [{"from": "root", "to": "implement_change"}]),
        ("skill_refs", ["legacy-skill"]),
    ],
)
def test_workflow_schema_rejects_removed_top_level_fields(
    field_name: str,
    field_value: Any,
) -> None:
    payload = minimal_workflow_payload()
    payload[field_name] = field_value

    with pytest.raises(ValidationError, match=field_name):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_root_consumes() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["consumes"] = {"artifacts": [{"slot": "change_patch"}]}

    with pytest.raises(ValidationError, match="consumes"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_duplicate_node_ids() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["children"].append(
        {
            "id": "implement_change",
            "role": "reviewer",
            "description": "Duplicate id.",
        }
    )

    with pytest.raises(ValidationError, match="duplicate node id"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_duplicate_artifact_slots() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["children"].append(
        {
            "id": "review_change",
            "role": "reviewer",
            "description": "Review the implementation evidence.",
            "produces": {
                "artifacts": [
                    {
                        "slot": "change_patch",
                        "description": "Duplicate artifact slot.",
                    }
                ]
            },
        }
    )

    with pytest.raises(ValidationError, match="duplicate artifact slot"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_duplicate_criteria_slots() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["children"][0]["criteria"].append(
        {
            "slot": "implementation_rules",
            "description": "Duplicate criteria slot.",
            "criteria": ["This should fail."],
        }
    )

    with pytest.raises(ValidationError, match="duplicate criteria slot"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_missing_consume_selector_targets_even_when_optional() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["children"][0]["consumes"] = {
        "artifacts": [{"slot": "findings_report", "required": False}],
        "criteria": [{"slot": "missing_criteria", "required": False}],
    }

    with pytest.raises(ValidationError, match="missing artifact consume selector target"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_illegal_child_default_criteria_references() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["child_defaults"] = {"criteria": ["missing_root_rule"]}

    with pytest.raises(ValidationError, match=r"child_defaults\.criteria"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_child_defaults_consumes_participate_in_dependency_validation() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["children"].append(
        {
            "id": "review_change",
            "role": "reviewer",
            "description": "Review the change.",
        }
    )
    payload["root"]["child_defaults"] = {"consumes": {"artifacts": [{"slot": "missing_artifact"}]}}

    with pytest.raises(ValidationError, match="missing artifact consume selector target"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_cyclic_dependency_graph() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["children"] = [
        {
            "id": "first_child",
            "role": "engineer",
            "description": "First sibling.",
            "consumes": {"artifacts": [{"slot": "second_output"}]},
            "produces": {
                "artifacts": [
                    {
                        "slot": "first_output",
                        "description": "First output.",
                    }
                ]
            },
        },
        {
            "id": "second_child",
            "role": "reviewer",
            "description": "Second sibling.",
            "consumes": {"artifacts": [{"slot": "first_output"}]},
            "produces": {
                "artifacts": [
                    {
                        "slot": "second_output",
                        "description": "Second output.",
                    }
                ]
            },
        },
    ]

    with pytest.raises(ValidationError, match="cyclic dependency graph"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_removed_fields_are_rejected_on_nested_nodes() -> None:
    payload = minimal_workflow_payload()
    nested_child = deepcopy(payload["root"]["children"][0])
    nested_child["skill_refs"] = ["legacy-child-skill"]
    payload["root"]["children"][0] = nested_child

    with pytest.raises(ValidationError, match="skill_refs"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_removed_skill_refs_are_rejected_on_root_node() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["skill_refs"] = ["legacy-root-skill"]

    with pytest.raises(ValidationError, match="skill_refs"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_nodes_accept_portable_provider_preference() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["provider_preference"] = "codex"
    payload["root"]["children"][0]["provider_preference"] = "openclaw"

    workflow = WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})

    assert workflow.root.provider_preference == "codex"
    assert workflow.root.children is not None
    assert workflow.root.children[0].provider_preference == "openclaw"


def test_workflow_nodes_accept_authored_node_instruction() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["instruction"] = "Coordinate the current task lineage."
    payload["root"]["children"][0]["instruction"] = "Patch only the bounded slice."

    workflow = WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})

    assert workflow.root.instruction == "Coordinate the current task lineage."
    assert workflow.root.children is not None
    assert workflow.root.children[0].instruction == "Patch only the bounded slice."


def test_workflow_nodes_reject_unknown_provider_preference() -> None:
    payload = minimal_workflow_payload()
    payload["root"]["children"][0]["provider_preference"] = "local-shell"

    with pytest.raises(ValidationError, match="provider_preference"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("provider_config", {"model": "gpt-5"}),
        ("transport", {"socket_path": "/tmp/provider.sock"}),
        ("auth_ref", "machine-local-secret"),
    ],
)
def test_workflow_nodes_reject_provider_local_configuration(
    field_name: str,
    field_value: Any,
) -> None:
    payload = minimal_workflow_payload()
    payload["root"]["children"][0][field_name] = field_value

    with pytest.raises(ValidationError, match=field_name):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_portable_workflow_node_contract_accepts_authored_execution_intent() -> None:
    node = WorkflowNodeInput.model_validate(
        {
            "node_key": "implement_slice",
            "kind": "worker",
            "title": "Implement slice",
            "role_id": "engineer",
            "policy_id": "standard-worker",
            "provider_preference": "codex",
            "description": "Implement the bounded slice.",
            "instruction": "Read the current criteria before patching.",
        }
    )

    assert node.model_dump(mode="json") == {
        "node_key": "implement_slice",
        "kind": "worker",
        "title": "Implement slice",
        "role_id": "engineer",
        "policy_id": "standard-worker",
        "provider_preference": "codex",
        "description": "Implement the bounded slice.",
        "instruction": "Read the current criteria before patching.",
    }


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("id", "implement_slice"),
        ("role", "engineer"),
        ("policy", "standard-worker"),
        ("transport", {"socket_path": "/tmp/provider.sock"}),
    ],
)
def test_portable_workflow_node_contract_rejects_non_portable_fields(
    field_name: str,
    field_value: Any,
) -> None:
    payload = {
        "node_key": "implement_slice",
        "kind": "worker",
        "role_id": "engineer",
        "policy_id": "standard-worker",
        "description": "Implement the bounded slice.",
    }
    payload[field_name] = field_value

    with pytest.raises(ValidationError, match=field_name):
        WorkflowNodeInput.model_validate(payload)


def test_portable_workflow_node_contract_requires_policy_reference() -> None:
    with pytest.raises(ValidationError, match="policy_id"):
        WorkflowNodeInput.model_validate(
            {
                "node_key": "implement_slice",
                "kind": "worker",
                "role_id": "engineer",
                "description": "Implement the bounded slice.",
            }
        )
