from __future__ import annotations

from autoclaw.definitions.contracts.workflow import WorkflowDefinitionFile


def root_blocked_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "root-blocked-release-review",
            "description": "Validate whole-flow blocked release semantics.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "investigate_blocker",
                        "role": "researcher",
                        "description": (
                            "Investigate the blocker and report whether work is blocked."
                        ),
                    }
                ],
            },
        }
    )


def parent_blocked_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "parent-blocked-review",
            "description": "Validate non-root parent blocked boundary propagation.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "investigate_parent",
                        "role": "planning_lead",
                        "policy": "standard-parent-planning",
                        "description": (
                            "Coordinate the investigation subtree and report blockers."
                        ),
                        "children": [
                            {
                                "id": "blocked_child",
                                "role": "researcher",
                                "description": (
                                    "Optional child work that should not be required "
                                    "before the parent can return blocked."
                                ),
                            }
                        ],
                    }
                ],
            },
        }
    )


def root_replan_publication_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "root-replan-publication-review",
            "description": "Validate same-attempt checkpoint and publication rebinding.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "produces": {
                    "artifacts": [
                        {
                            "slot": "decision_note",
                            "description": "Root decision note for the current turn.",
                        }
                    ]
                },
                "children": [
                    {
                        "id": "review_step",
                        "role": "researcher",
                        "description": "Review the current subtree state.",
                    }
                ],
            },
        }
    )


def root_budget_rebind_workflow() -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        {
            "kind": "workflow",
            "id": "root-budget-rebind-review",
            "description": "Validate child-assignment budget rebinding after structural adopt.",
            "root": {
                "id": "root",
                "role": "root_planning_lead",
                "policy": "standard-root-planning",
                "description": "Root coordinator.",
                "children": [
                    {
                        "id": "implement_change",
                        "role": "researcher",
                        "description": "Implement the bounded change.",
                        "produces": {
                            "artifacts": [
                                {
                                    "slot": "change_patch",
                                    "description": "Bounded code patch for the task.",
                                },
                                {
                                    "slot": "verification_report",
                                    "description": "Verification report for the patch.",
                                },
                            ]
                        },
                    }
                ],
            },
        }
    )
