from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import pytest
import yaml
from app.compiler import (
    MappingRolePolicyLookup,
    PolicyRevisionDefinition,
    RoleRevisionDefinition,
    WorkflowRevisionMetadata,
    compile_workflow,
)
from app.schemas.definitions import (
    PolicyDefinitionFile,
    RoleDefinitionFile,
    WorkflowDefinitionFile,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AUTHORED_DEFINITIONS_ROOT = REPO_ROOT / "definitions"
PACKAGED_SEED_DEFINITIONS_ROOT = resources.files("app.resources").joinpath("definitions")

ROLE_REVISIONS = {
    "architect": 48,
    "engineer": 44,
    "planner": 47,
    "planning_lead": 42,
    "release_operator": 46,
    "researcher": 43,
    "reviewer": 45,
    "root_planning_lead": 41,
}

POLICY_REVISIONS = {
    "standard-parent-planning": 52,
    "standard-release": 55,
    "standard-review": 54,
    "standard-root-planning": 51,
    "standard-worker": 53,
}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _load_packaged_seed_lookup() -> MappingRolePolicyLookup:
    with resources.as_file(PACKAGED_SEED_DEFINITIONS_ROOT) as packaged_seed_root:
        roles = {
            role.id: RoleRevisionDefinition(
                definition=role,
                revision_no=ROLE_REVISIONS[role.id],
            )
            for role in (
                RoleDefinitionFile.model_validate(_load_yaml(path))
                for path in sorted((packaged_seed_root / "roles").glob("*.yaml"))
            )
        }
        policies = {
            policy.id: PolicyRevisionDefinition(
                definition=policy,
                revision_no=POLICY_REVISIONS[policy.id],
            )
            for policy in (
                PolicyDefinitionFile.model_validate(_load_yaml(path))
                for path in sorted((packaged_seed_root / "policies").glob("*.yaml"))
            )
        }

    return MappingRolePolicyLookup(roles=roles, policies=policies)


def _load_authored_workflow_fixture(name: str) -> WorkflowDefinitionFile:
    path = AUTHORED_DEFINITIONS_ROOT / "workflows" / f"{name}.yaml"
    return WorkflowDefinitionFile.model_validate(_load_yaml(path))


def _compile_authored_workflow_fixture(name: str, revision_no: int) -> Any:
    workflow = _load_authored_workflow_fixture(name)
    return compile_workflow(
        workflow=workflow,
        workflow_revision=WorkflowRevisionMetadata(
            workflow_key=workflow.id,
            definition_revision_no=revision_no,
        ),
        compiler_version="phase-1-wave-2",
        lookup=_load_packaged_seed_lookup(),
    )


def _node_by_key(plan: Any, node_key: str) -> Any:
    return next(node for node in plan.nodes if node.node_key == node_key)


def test_compile_minimal_workflow_smoke() -> None:
    plan = _compile_authored_workflow_fixture("minimal_implement_change", revision_no=4)

    assert plan.workflow_key == "minimal-implement-change"
    assert plan.definition_revision_no == 4
    assert plan.compiler_version == "phase-1-wave-2"
    assert [node.node_key for node in plan.nodes] == ["root", "implement_change"]
    assert {node.node_key: node.structural_kind.value for node in plan.nodes} == {
        "root": "root",
        "implement_change": "worker",
    }

    root = _node_by_key(plan, "root")
    assert root.role_revision_no == ROLE_REVISIONS["planning_lead"]
    assert root.policy is None
    assert root.policy_revision_no is None
    assert [criteria.slot for criteria in root.criteria] == ["implementation_rules"]

    implement_change = _node_by_key(plan, "implement_change")
    assert implement_change.consumes is None
    assert [criteria.slot for criteria in implement_change.criteria] == [
        "implement_change_delivery_criteria"
    ]
    assert implement_change.role_revision_no == ROLE_REVISIONS["engineer"]
    assert implement_change.policy_revision_no == POLICY_REVISIONS["standard-worker"]
    assert [artifact.slot for artifact in implement_change.produces.artifacts] == [
        "change_patch",
        "verification_report",
    ]
    assert plan.dependency_edges == ()


def test_compile_normal_workflow_normalizes_structure_and_edges() -> None:
    plan = _compile_authored_workflow_fixture("normal_parent_first_release", revision_no=7)

    assert plan.workflow_key == "normal-parent-first-release"
    assert plan.definition_revision_no == 7
    assert plan.compiler_version == "phase-1-wave-2"

    assert [node.node_key for node in plan.nodes] == [
        "root",
        "implementation_subtree",
        "investigate_issue",
        "implement_change",
        "review_change",
        "release_closure",
    ]
    assert {node.node_key: node.structural_kind.value for node in plan.nodes} == {
        "root": "root",
        "implementation_subtree": "parent",
        "investigate_issue": "worker",
        "implement_change": "worker",
        "review_change": "worker",
        "release_closure": "worker",
    }

    implement_change = _node_by_key(plan, "implement_change")
    assert [criteria.slot for criteria in implement_change.criteria] == [
        "implementation_subtree_requirements",
        "implement_change_delivery_criteria",
    ]
    assert implement_change.role_revision_no == ROLE_REVISIONS["engineer"]
    assert implement_change.policy_revision_no == POLICY_REVISIONS["standard-worker"]

    investigate_issue = _node_by_key(plan, "investigate_issue")
    assert investigate_issue.policy is None
    assert investigate_issue.policy_revision_no is None
    assert [criteria.slot for criteria in investigate_issue.criteria] == [
        "implementation_subtree_requirements"
    ]

    assert [
        (
            edge.provider_node_key,
            edge.consumer_node_key,
            edge.kind.value,
            edge.slot,
        )
        for edge in plan.dependency_edges
    ] == [
        ("investigate_issue", "implement_change", "artifact", "findings_report"),
        ("implement_change", "review_change", "artifact", "change_patch"),
        ("implement_change", "review_change", "artifact", "verification_report"),
        (
            "implementation_subtree",
            "review_change",
            "criteria",
            "implementation_subtree_requirements",
        ),
        ("implement_change", "release_closure", "artifact", "change_patch"),
        ("implement_change", "release_closure", "artifact", "verification_report"),
        ("review_change", "release_closure", "artifact", "review_report"),
        ("root", "release_closure", "criteria", "root_closure_criteria"),
    ]


def test_compile_maximal_workflow_normalizes_structure_edges_and_policy_pins() -> None:
    plan = _compile_authored_workflow_fixture("maximal_parent_first_release", revision_no=11)

    assert [node.node_key for node in plan.nodes] == [
        "root",
        "discovery",
        "gather_evidence",
        "implementation_loop",
        "plan_iteration",
        "implement_change",
        "review_change",
        "qa_sweep",
        "release_closure",
    ]
    assert {node.node_key: node.structural_kind.value for node in plan.nodes} == {
        "root": "root",
        "discovery": "parent",
        "gather_evidence": "worker",
        "implementation_loop": "parent",
        "plan_iteration": "worker",
        "implement_change": "worker",
        "review_change": "worker",
        "qa_sweep": "worker",
        "release_closure": "worker",
    }

    plan_iteration = _node_by_key(plan, "plan_iteration")
    assert [criteria.slot for criteria in plan_iteration.criteria] == [
        "implementation_loop_requirements"
    ]
    assert plan_iteration.policy is None
    assert plan_iteration.policy_revision_no is None
    assert plan_iteration.role_revision_no == ROLE_REVISIONS["planner"]

    qa_sweep = _node_by_key(plan, "qa_sweep")
    assert [criteria.slot for criteria in qa_sweep.criteria] == ["implementation_loop_requirements"]
    assert qa_sweep.policy is None
    assert qa_sweep.policy_revision_no is None
    assert qa_sweep.role_revision_no == ROLE_REVISIONS["architect"]

    root = _node_by_key(plan, "root")
    assert root.role_revision_no == ROLE_REVISIONS["root_planning_lead"]
    assert root.policy_revision_no == POLICY_REVISIONS["standard-root-planning"]

    assert [
        (
            edge.provider_node_key,
            edge.consumer_node_key,
            edge.kind.value,
            edge.slot,
        )
        for edge in plan.dependency_edges
    ] == [
        ("gather_evidence", "plan_iteration", "artifact", "findings_report"),
        ("gather_evidence", "implement_change", "artifact", "findings_report"),
        ("plan_iteration", "implement_change", "artifact", "delivery_plan"),
        ("implement_change", "review_change", "artifact", "change_patch"),
        ("implement_change", "review_change", "artifact", "verification_report"),
        (
            "implementation_loop",
            "review_change",
            "criteria",
            "implementation_review_criteria",
        ),
        ("implement_change", "qa_sweep", "artifact", "change_patch"),
        ("implement_change", "qa_sweep", "artifact", "verification_report"),
        ("review_change", "qa_sweep", "artifact", "review_report"),
        ("gather_evidence", "release_closure", "artifact", "findings_report"),
        ("plan_iteration", "release_closure", "artifact", "delivery_plan"),
        ("implement_change", "release_closure", "artifact", "change_patch"),
        ("implement_change", "release_closure", "artifact", "verification_report"),
        ("review_change", "release_closure", "artifact", "review_report"),
        ("qa_sweep", "release_closure", "artifact", "qa_report"),
        ("root", "release_closure", "criteria", "root_closure_criteria"),
    ]


def test_compile_treats_dotted_node_ids_as_opaque_strings() -> None:
    workflow = WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "dotted-id-opacity",
            "description": "Dotted node ids must not imply parenthood.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "implementation",
                        "role": "planning_lead",
                        "policy": "standard-parent-planning",
                        "description": "Explicit parent branch.",
                        "children": [
                            {
                                "id": "qa.sweep",
                                "role": "engineer",
                                "policy": "standard-worker",
                                "description": "Nested worker with a dotted id.",
                            }
                        ],
                    },
                    {
                        "id": "qa",
                        "role": "reviewer",
                        "policy": "standard-review",
                        "description": "Sibling whose id matches the dotted prefix.",
                    },
                ],
            },
        }
    )

    plan = compile_workflow(
        workflow=workflow,
        workflow_revision=WorkflowRevisionMetadata(
            workflow_key=workflow.id,
            definition_revision_no=2,
        ),
        compiler_version="phase-1-wave-2",
        lookup=_load_packaged_seed_lookup(),
    )

    assert [node.node_key for node in plan.nodes] == ["root", "implementation", "qa.sweep", "qa"]

    implementation = _node_by_key(plan, "implementation")
    qa_sweep = _node_by_key(plan, "qa.sweep")
    qa = _node_by_key(plan, "qa")

    assert implementation.child_node_keys == ("qa.sweep",)
    assert qa_sweep.parent_node_key == "implementation"
    assert qa_sweep.parent_node_key != "qa"
    assert qa.parent_node_key == "root"
    assert plan.dependency_edges == ()


def test_compile_workflow_expands_child_defaults_only_to_direct_children() -> None:
    workflow = WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "child-defaults-direct-only",
            "description": "Validate direct-child-only child_defaults expansion.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "description": "Coordinate direct child defaults only.",
                "produces": {
                    "artifacts": [
                        {
                            "slot": "root_brief",
                            "description": "Shared briefing artifact.",
                        }
                    ]
                },
                "criteria": [
                    {
                        "slot": "root_rule",
                        "description": "Root rule for direct children.",
                        "criteria": ["Direct children must honor the root rule."],
                    }
                ],
                "child_defaults": {
                    "consumes": {"artifacts": [{"slot": "root_brief"}]},
                    "criteria": ["root_rule"],
                },
                "children": [
                    {
                        "id": "parent_branch",
                        "role": "planning_lead",
                        "description": "Direct child parent branch.",
                        "children": [
                            {
                                "id": "grandchild_worker",
                                "role": "engineer",
                                "description": "Grandchild should not inherit root defaults.",
                            }
                        ],
                    },
                    {
                        "id": "direct_worker",
                        "role": "engineer",
                        "description": "Direct worker should inherit root defaults.",
                    },
                ],
            },
        }
    )

    plan = compile_workflow(
        workflow=workflow,
        workflow_revision=WorkflowRevisionMetadata(
            workflow_key=workflow.id,
            definition_revision_no=3,
        ),
        compiler_version="phase-1-wave-2",
        lookup=_load_packaged_seed_lookup(),
    )

    parent_branch = _node_by_key(plan, "parent_branch")
    direct_worker = _node_by_key(plan, "direct_worker")
    grandchild_worker = _node_by_key(plan, "grandchild_worker")

    assert [selector.slot for selector in parent_branch.consumes.artifacts] == ["root_brief"]
    assert [criteria.slot for criteria in parent_branch.criteria] == ["root_rule"]

    assert [selector.slot for selector in direct_worker.consumes.artifacts] == ["root_brief"]
    assert [criteria.slot for criteria in direct_worker.criteria] == ["root_rule"]

    assert grandchild_worker.consumes is None
    assert grandchild_worker.criteria == ()

    assert [
        (
            edge.provider_node_key,
            edge.consumer_node_key,
            edge.kind.value,
            edge.slot,
        )
        for edge in plan.dependency_edges
    ] == [
        ("root", "parent_branch", "artifact", "root_brief"),
        ("root", "direct_worker", "artifact", "root_brief"),
    ]


@pytest.mark.parametrize(
    ("node_role", "lookup_builder", "error_pattern"),
    [
        (
            "missing_role",
            lambda lookup: MappingRolePolicyLookup(
                roles={key: value for key, value in lookup.roles.items() if key != "missing_role"},
                policies=lookup.policies,
            ),
            "role 'missing_role' does not resolve for node 'implement_change'",
        ),
        (
            "root_planning_lead",
            lambda lookup: lookup,
            (
                "role 'root_planning_lead' is incompatible with node kind "
                "'worker' for node 'implement_change'"
            ),
        ),
    ],
)
def test_compile_workflow_fails_for_missing_or_incompatible_roles(
    node_role: str,
    lookup_builder: Any,
    error_pattern: str,
) -> None:
    payload = _load_yaml(AUTHORED_DEFINITIONS_ROOT / "workflows" / "minimal_implement_change.yaml")
    payload["root"]["children"][0]["role"] = node_role
    workflow = WorkflowDefinitionFile.model_validate(payload)

    base_lookup = _load_packaged_seed_lookup()
    lookup = lookup_builder(base_lookup)

    with pytest.raises(ValueError, match=error_pattern):
        compile_workflow(
            workflow=workflow,
            workflow_revision=WorkflowRevisionMetadata(
                workflow_key=workflow.id,
                definition_revision_no=5,
            ),
            compiler_version="phase-1-wave-2",
            lookup=lookup,
        )


@pytest.mark.parametrize(
    ("node_policy", "error_pattern"),
    [
        (
            "missing-policy",
            "policy 'missing-policy' does not resolve for node 'implement_change'",
        ),
        (
            "standard-parent-planning",
            (
                "policy 'standard-parent-planning' is incompatible with node kind "
                "'worker' for node 'implement_change'"
            ),
        ),
    ],
)
def test_compile_workflow_fails_for_missing_or_incompatible_policies(
    node_policy: str,
    error_pattern: str,
) -> None:
    payload = _load_yaml(AUTHORED_DEFINITIONS_ROOT / "workflows" / "minimal_implement_change.yaml")
    payload["root"]["children"][0]["policy"] = node_policy
    workflow = WorkflowDefinitionFile.model_validate(payload)

    with pytest.raises(ValueError, match=error_pattern):
        compile_workflow(
            workflow=workflow,
            workflow_revision=WorkflowRevisionMetadata(
                workflow_key=workflow.id,
                definition_revision_no=5,
            ),
            compiler_version="phase-1-wave-2",
            lookup=_load_packaged_seed_lookup(),
        )


def test_compile_dedupes_repeated_child_default_criteria_slots() -> None:
    workflow = WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "duplicate-child-default-criteria",
            "description": "Deduplicate repeated child-default criteria slots.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "subtree",
                        "role": "planning_lead",
                        "policy": "standard-parent-planning",
                        "description": "Parent subtree.",
                        "criteria": [
                            {
                                "slot": "shared_rules",
                                "description": "Shared subtree rules.",
                                "criteria": ["Child work must honor the shared rules."],
                            }
                        ],
                        "child_defaults": {
                            "criteria": ["shared_rules", "shared_rules"],
                        },
                        "children": [
                            {
                                "id": "child_worker",
                                "role": "engineer",
                                "description": "Worker child.",
                            }
                        ],
                    }
                ],
            },
        }
    )

    plan = compile_workflow(
        workflow=workflow,
        workflow_revision=WorkflowRevisionMetadata(
            workflow_key=workflow.id,
            definition_revision_no=1,
        ),
        compiler_version="phase-1-wave-2",
        lookup=_load_packaged_seed_lookup(),
    )

    child = _node_by_key(plan, "child_worker")
    assert [criteria.slot for criteria in child.criteria] == ["shared_rules"]
