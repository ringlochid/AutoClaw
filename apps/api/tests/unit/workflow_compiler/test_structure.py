from __future__ import annotations

from typing import Any

from autoclaw.compiler import WorkflowRevisionMetadata, compile_workflow
from autoclaw.schemas.definitions import WorkflowDefinitionFile

from .support import load_packaged_seed_lookup, node_by_key


def _edge_tuples(plan: Any) -> list[tuple[str, str, str, str]]:
    return [
        (
            edge.provider_node_key,
            edge.consumer_node_key,
            edge.kind.value,
            edge.slot,
        )
        for edge in plan.dependency_edges
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
        lookup=load_packaged_seed_lookup(),
    )

    assert [node.node_key for node in plan.nodes] == ["root", "implementation", "qa.sweep", "qa"]

    implementation = node_by_key(plan, "implementation")
    qa_sweep = node_by_key(plan, "qa.sweep")
    qa = node_by_key(plan, "qa")

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
        lookup=load_packaged_seed_lookup(),
    )

    parent_branch = node_by_key(plan, "parent_branch")
    direct_worker = node_by_key(plan, "direct_worker")
    grandchild_worker = node_by_key(plan, "grandchild_worker")

    assert [selector.slot for selector in parent_branch.consumes.artifacts] == ["root_brief"]
    assert [criteria.slot for criteria in parent_branch.criteria] == ["root_rule"]

    assert [selector.slot for selector in direct_worker.consumes.artifacts] == ["root_brief"]
    assert [criteria.slot for criteria in direct_worker.criteria] == ["root_rule"]

    assert grandchild_worker.consumes is None
    assert grandchild_worker.criteria == ()

    assert _edge_tuples(plan) == [
        ("root", "parent_branch", "artifact", "root_brief"),
        ("root", "direct_worker", "artifact", "root_brief"),
    ]


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
        lookup=load_packaged_seed_lookup(),
    )

    child = node_by_key(plan, "child_worker")
    assert [criteria.slot for criteria in child.criteria] == ["shared_rules"]
