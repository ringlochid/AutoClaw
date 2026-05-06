from __future__ import annotations

import re
from copy import deepcopy
from importlib import resources
from pathlib import Path
from typing import Any

import pytest
import yaml
from app.schemas.definitions import (
    PolicyDefinitionFile,
    RoleDefinitionFile,
    WorkflowDefinitionFile,
)
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[4]
AUTHORED_DEFINITIONS_ROOT = REPO_ROOT / "definitions"
PACKAGED_SEED_DEFINITIONS_ROOT = resources.files("app.resources").joinpath("definitions")
WORKFLOW_EXAMPLES_ROOT = REPO_ROOT / "docs" / "redesign" / "workflows" / "examples"


def _minimal_workflow_payload() -> dict[str, Any]:
    return {
        "id": "minimal-implement-change",
        "description": "Execute one bounded engineering change under parent ownership.",
        "root": {
            "id": "root",
            "role": "planning_lead",
            "description": (
                "Verify one bounded engineering worker and release only when current "
                "evidence is sufficient."
            ),
            "criteria": [
                {
                    "slot": "implementation_rules",
                    "description": "Parent acceptance criteria for the bounded engineering child.",
                    "criteria": [
                        "keep the child inside the current bounded assignment",
                        "publish patch and verification evidence only through declared "
                        "produce slots",
                    ],
                }
            ],
            "children": [
                {
                    "id": "implement_change",
                    "role": "engineer",
                    "policy": "standard-worker",
                    "description": (
                        "Implement the change and publish patch plus verification evidence "
                        "only for the current bounded assignment."
                    ),
                    "criteria": [
                        {
                            "slot": "implement_change_delivery_criteria",
                            "description": "Delivery criteria for the bounded engineering change.",
                            "criteria": [
                                "patch is limited to the assigned path",
                                "verification evidence demonstrates the intended fix",
                            ],
                        }
                    ],
                    "produces": {
                        "artifacts": [
                            {
                                "slot": "change_patch",
                                "file_hint": "change_patch.diff",
                                "description": "Patch for the bounded change.",
                            },
                            {
                                "slot": "verification_report",
                                "file_hint": "verification_report.md",
                                "description": "Verification evidence for the bounded change.",
                            },
                        ]
                    },
                }
            ],
        },
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _load_first_yaml_fence(path: Path) -> dict[str, Any]:
    match = re.search(r"```yaml\n(.*?)\n```", path.read_text(encoding="utf-8"), re.DOTALL)
    assert match is not None, f"expected a yaml fence in {path}"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def _load_yaml_fences(path: Path) -> list[str]:
    return re.findall(r"```yaml\n(.*?)\n```", path.read_text(encoding="utf-8"), re.DOTALL)


def _load_registry_catalog(definitions_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    roles: dict[str, Any] = {}
    policies: dict[str, Any] = {}

    for path in sorted((definitions_root / "roles").glob("*.yaml")):
        role = RoleDefinitionFile.model_validate(_load_yaml(path))
        roles[role.id] = role

    for path in sorted((definitions_root / "policies").glob("*.yaml")):
        policy = PolicyDefinitionFile.model_validate(_load_yaml(path))
        policies[policy.id] = policy

    return roles, policies


def _load_workflow_ids(
    definitions_root: Path,
    *,
    roles: dict[str, Any],
    policies: dict[str, Any],
) -> set[str]:
    validation_context = {"roles": roles, "policies": policies}

    return {
        WorkflowDefinitionFile.model_validate(
            _load_yaml(path),
            context=validation_context,
        ).id
        for path in sorted((definitions_root / "workflows").glob("*.yaml"))
    }


def _load_definition_tree(definitions_root: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}

    for kind in ("roles", "policies", "workflows"):
        for path in sorted((definitions_root / kind).glob("*.yaml")):
            payloads[str(path.relative_to(definitions_root))] = _load_yaml(path)

    return payloads


def _assert_expected_role_and_policy_ids(
    roles: dict[str, Any],
    policies: dict[str, Any],
) -> None:
    assert {"planning_lead", "root_planning_lead", "engineer", "researcher", "planner"} <= set(
        roles
    )
    assert {"architect", "reviewer", "release_operator"} <= set(roles)
    assert {
        "standard-parent-planning",
        "standard-root-planning",
        "standard-worker",
        "standard-review",
        "standard-release",
    } <= set(policies)


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
    payload = _minimal_workflow_payload()
    payload[field_name] = field_value

    with pytest.raises(ValidationError, match=field_name):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_root_consumes() -> None:
    payload = _minimal_workflow_payload()
    payload["root"]["consumes"] = {"artifacts": [{"slot": "change_patch"}]}

    with pytest.raises(ValidationError, match="consumes"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_duplicate_node_ids() -> None:
    payload = _minimal_workflow_payload()
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
    payload = _minimal_workflow_payload()
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
    payload = _minimal_workflow_payload()
    payload["root"]["children"][0]["criteria"].append(
        {
            "slot": "implementation_rules",
            "description": "Duplicate criteria slot.",
            "criteria": ["This should fail."],
        }
    )

    with pytest.raises(ValidationError, match="duplicate criteria slot"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_missing_consume_selector_targets() -> None:
    payload = _minimal_workflow_payload()
    payload["root"]["children"][0]["consumes"] = {
        "artifacts": [{"slot": "findings_report"}],
        "criteria": [{"slot": "missing_criteria"}],
    }

    with pytest.raises(ValidationError, match="missing artifact consume selector target"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_workflow_schema_rejects_illegal_child_default_criteria_references() -> None:
    payload = _minimal_workflow_payload()
    payload["root"]["child_defaults"] = {"criteria": ["missing_root_rule"]}

    with pytest.raises(ValidationError, match=r"child_defaults\.criteria"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


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


def test_authored_role_and_policy_fixtures_validate() -> None:
    roles, policies = _load_registry_catalog(AUTHORED_DEFINITIONS_ROOT)

    _assert_expected_role_and_policy_ids(roles, policies)


def test_packaged_role_and_policy_seed_definitions_validate() -> None:
    with resources.as_file(PACKAGED_SEED_DEFINITIONS_ROOT) as packaged_seed_root:
        roles, policies = _load_registry_catalog(packaged_seed_root)

    _assert_expected_role_and_policy_ids(roles, policies)


def test_authored_workflow_fixtures_validate_against_authored_catalog() -> None:
    roles, policies = _load_registry_catalog(AUTHORED_DEFINITIONS_ROOT)
    workflow_ids = _load_workflow_ids(
        AUTHORED_DEFINITIONS_ROOT,
        roles=roles,
        policies=policies,
    )

    assert workflow_ids == {
        "minimal-implement-change",
        "normal-parent-first-release",
        "maximal-parent-first-release",
    }


def test_packaged_workflow_seed_definitions_validate_against_packaged_catalog() -> None:
    with resources.as_file(PACKAGED_SEED_DEFINITIONS_ROOT) as packaged_seed_root:
        roles, policies = _load_registry_catalog(packaged_seed_root)
        workflow_ids = _load_workflow_ids(
            packaged_seed_root,
            roles=roles,
            policies=policies,
        )

    assert workflow_ids == {
        "minimal-implement-change",
        "normal-parent-first-release",
        "maximal-parent-first-release",
    }


def test_packaged_seed_tree_matches_repo_authored_definition_fixtures() -> None:
    authored_tree = _load_definition_tree(AUTHORED_DEFINITIONS_ROOT)

    with resources.as_file(PACKAGED_SEED_DEFINITIONS_ROOT) as packaged_seed_root:
        packaged_tree = _load_definition_tree(packaged_seed_root)

    assert packaged_tree == authored_tree


@pytest.mark.parametrize(
    ("workflow_fixture", "example_doc"),
    [
        (
            "minimal_implement_change.yaml",
            "minimal.md",
        ),
        (
            "normal_parent_first_release.yaml",
            "normal.md",
        ),
        (
            "maximal_parent_first_release.yaml",
            "maximal.md",
        ),
    ],
)
def test_authored_workflow_fixtures_match_canonical_example_docs(
    workflow_fixture: str,
    example_doc: str,
) -> None:
    fixture_payload = _load_yaml(AUTHORED_DEFINITIONS_ROOT / "workflows" / workflow_fixture)
    example_payload = _load_first_yaml_fence(WORKFLOW_EXAMPLES_ROOT / example_doc)

    assert fixture_payload == example_payload


def test_workflow_definition_schema_worked_yaml_examples_parse() -> None:
    schema_doc = REPO_ROOT / "docs" / "redesign" / "workflows" / "workflow-definition-schema.md"
    yaml_fences = _load_yaml_fences(schema_doc)

    # The first fence is shape notation, not copy-safe YAML. The later worked examples should parse.
    assert len(yaml_fences[1:]) == 4
    for yaml_fence in yaml_fences[1:]:
        data = yaml.safe_load(yaml_fence)
        assert isinstance(data, dict)


def test_child_defaults_consumes_participate_in_dependency_validation() -> None:
    payload = _minimal_workflow_payload()
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
    payload = _minimal_workflow_payload()
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
    payload = _minimal_workflow_payload()
    nested_child = deepcopy(payload["root"]["children"][0])
    nested_child["skill_refs"] = ["legacy-child-skill"]
    payload["root"]["children"][0] = nested_child

    with pytest.raises(ValidationError, match="skill_refs"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})


def test_removed_skill_refs_are_rejected_on_root_node() -> None:
    payload = _minimal_workflow_payload()
    payload["root"]["skill_refs"] = ["legacy-root-skill"]

    with pytest.raises(ValidationError, match="skill_refs"):
        WorkflowDefinitionFile.model_validate({"kind": "workflow", **payload})
