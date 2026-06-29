from __future__ import annotations

from autoclaw.definitions.compiler import WorkflowRevisionMetadata, compile_workflow
from autoclaw.definitions.contracts import WorkflowDefinitionFile

from .support import (
    WORKFLOW_COMPILER_TEST_VERSION,
    load_packaged_seed_lookup,
    node_by_key,
)


def test_compile_preserves_optional_consume_selectors_for_runtime_surfaces() -> None:
    workflow = WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "optional-consume-selectors",
            "description": "Optional consume selectors stay explicit in normalized output.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root",
                "description": "Root coordinator.",
                "produces": {
                    "artifacts": [
                        {
                            "slot": "shared_brief",
                            "description": "Shared briefing artifact.",
                        }
                    ]
                },
                "criteria": [
                    {
                        "slot": "shared_rule",
                        "description": "Shared criteria for downstream work.",
                        "criteria": ["Downstream work may skip this only when runtime says so."],
                    }
                ],
                "children": [
                    {
                        "id": "implement_change",
                        "role": "engineer",
                        "policy": "standard-worker",
                        "description": "Worker child.",
                        "consumes": {
                            "artifacts": [
                                {
                                    "slot": "shared_brief",
                                    "required": False,
                                }
                            ],
                            "criteria": [
                                {
                                    "slot": "shared_rule",
                                    "required": False,
                                }
                            ],
                        },
                    }
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
        compiler_version=WORKFLOW_COMPILER_TEST_VERSION,
        lookup=load_packaged_seed_lookup(),
    )

    child = node_by_key(plan, "implement_change")
    assert child.consumes is not None
    assert [(selector.slot, selector.required) for selector in child.consumes.artifacts] == [
        ("shared_brief", False)
    ]
    assert [(selector.slot, selector.required) for selector in child.consumes.criteria] == [
        ("shared_rule", False)
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
        ("root", "implement_change", "artifact", "shared_brief"),
        ("root", "implement_change", "criteria", "shared_rule"),
    ]


def test_compile_preserves_criteria_owner_for_inherited_and_local_slots() -> None:
    workflow = WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "criteria-owner-preservation",
            "description": "Inherited criteria keep the declaring node as owner.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "implementation_subtree",
                        "role": "planning_lead",
                        "policy": "standard-parent",
                        "description": "Parent subtree.",
                        "criteria": [
                            {
                                "slot": "shared_rules",
                                "description": "Shared subtree rules.",
                                "criteria": ["Child work stays inside the subtree."],
                            }
                        ],
                        "child_defaults": {
                            "criteria": ["shared_rules"],
                        },
                        "children": [
                            {
                                "id": "implement_change",
                                "role": "engineer",
                                "policy": "standard-worker",
                                "description": "Worker child.",
                                "criteria": [
                                    {
                                        "slot": "local_delivery",
                                        "description": "Local worker delivery criteria.",
                                        "criteria": ["Patch and verification stay aligned."],
                                    }
                                ],
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
        compiler_version=WORKFLOW_COMPILER_TEST_VERSION,
        lookup=load_packaged_seed_lookup(),
    )

    child = node_by_key(plan, "implement_change")
    assert [(criteria.slot, criteria.owner_node_key) for criteria in child.criteria] == [
        ("shared_rules", "implementation_subtree"),
        ("local_delivery", "implement_change"),
    ]
    parent = node_by_key(plan, "implementation_subtree")
    assert [(criteria.slot, criteria.owner_node_key) for criteria in parent.criteria] == [
        ("shared_rules", "implementation_subtree"),
    ]
