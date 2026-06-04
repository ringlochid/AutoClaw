from __future__ import annotations

from autoclaw.schemas.definitions.workflow import WorkflowDefinitionFile


def child_defaults_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "child-defaults-consumes-review",
            "description": "Validate runtime structural replan inheritance.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "produces": {
                    "artifacts": [
                        {
                            "slot": "brief",
                            "description": "Shared briefing artifact.",
                        }
                    ]
                },
                "children": [
                    {
                        "id": "subtree",
                        "role": "planning_lead",
                        "policy": "standard-parent-planning",
                        "description": "Parent subtree.",
                        "child_defaults": {
                            "consumes": {"artifacts": [{"slot": "brief"}]},
                        },
                        "children": [
                            {
                                "id": "existing_child",
                                "role": "researcher",
                                "description": "Existing worker child.",
                            }
                        ],
                    }
                ],
            },
        }
    )


def optional_artifact_selector_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "optional-artifact-selector-review",
            "description": "Validate optional artifact selector currentness behavior.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "produces": {
                    "artifacts": [
                        {
                            "slot": "brief",
                            "description": "Optional shared brief for downstream work.",
                        }
                    ]
                },
                "children": [
                    {
                        "id": "optional_child",
                        "role": "researcher",
                        "description": "Worker with an optional briefing dependency.",
                        "consumes": {
                            "artifacts": [
                                {
                                    "slot": "brief",
                                    "required": False,
                                }
                            ]
                        },
                    }
                ],
            },
        }
    )


def criteria_defaults_refresh_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "criteria-defaults-refresh-review",
            "description": "Validate inherited criteria refresh during runtime replan.",
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
                                "slot": "review_gate",
                                "description": "Original review gate.",
                                "criteria": ["Child work must satisfy the current review gate."],
                            }
                        ],
                        "child_defaults": {
                            "criteria": ["review_gate"],
                        },
                        "children": [
                            {
                                "id": "collect_cases",
                                "role": "researcher",
                                "description": "Collect QA cases.",
                            }
                        ],
                    }
                ],
            },
        }
    )


def dependency_dedupe_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "dependency-dedupe-review",
            "description": "Validate manifest dependency dedupe during rematerialization.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "criteria": [
                    {
                        "slot": "acceptance_gate",
                        "description": "Acceptance gate.",
                        "criteria": ["Child work must satisfy the shared acceptance gate."],
                    }
                ],
                "produces": {
                    "artifacts": [
                        {
                            "slot": "brief",
                            "description": "Shared brief.",
                        }
                    ]
                },
                "children": [
                    {
                        "id": "implement_change",
                        "role": "engineer",
                        "description": "Implement the change.",
                        "consumes": {
                            "artifacts": [{"slot": "brief"}],
                            "criteria": [{"slot": "acceptance_gate"}],
                        },
                    }
                ],
            },
        }
    )


def root_descendant_replan_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "root-descendant-replan-review",
            "description": "Validate root whole-tree replan breadth without widening parent scope.",
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
                        "children": [
                            {
                                "id": "nested_parent",
                                "role": "planning_lead",
                                "policy": "standard-parent-planning",
                                "description": "Nested subtree.",
                                "children": [
                                    {
                                        "id": "existing_leaf",
                                        "role": "researcher",
                                        "description": "Leaf worker.",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        }
    )
