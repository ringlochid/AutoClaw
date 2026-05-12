from __future__ import annotations

from tests.unit.test_workflow_compiler_support import (
    POLICY_REVISIONS,
    ROLE_REVISIONS,
    compile_authored_workflow_fixture,
    node_by_key,
)


def test_compile_minimal_workflow_smoke() -> None:
    plan = compile_authored_workflow_fixture("minimal_implement_change", revision_no=4)

    assert plan.workflow_key == "minimal-implement-change"
    assert plan.definition_revision_no == 4
    assert plan.compiler_version == "phase-1-wave-2"
    assert [node.node_key for node in plan.nodes] == ["root", "implement_change"]
    assert {node.node_key: node.structural_kind.value for node in plan.nodes} == {
        "root": "root",
        "implement_change": "worker",
    }

    root = node_by_key(plan, "root")
    assert root.role_revision_no == ROLE_REVISIONS["planning_lead"]
    assert root.policy is None
    assert root.policy_revision_no is None
    assert [criteria.slot for criteria in root.criteria] == ["implementation_rules"]

    implement_change = node_by_key(plan, "implement_change")
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
    plan = compile_authored_workflow_fixture("normal_parent_first_release", revision_no=7)

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

    implement_change = node_by_key(plan, "implement_change")
    assert [criteria.slot for criteria in implement_change.criteria] == [
        "implementation_subtree_requirements",
        "implement_change_delivery_criteria",
    ]
    assert implement_change.role_revision_no == ROLE_REVISIONS["engineer"]
    assert implement_change.policy_revision_no == POLICY_REVISIONS["standard-worker"]

    investigate_issue = node_by_key(plan, "investigate_issue")
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
    plan = compile_authored_workflow_fixture("maximal_parent_first_release", revision_no=11)

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

    plan_iteration = node_by_key(plan, "plan_iteration")
    assert [criteria.slot for criteria in plan_iteration.criteria] == [
        "implementation_loop_requirements"
    ]
    assert plan_iteration.policy is None
    assert plan_iteration.policy_revision_no is None
    assert plan_iteration.role_revision_no == ROLE_REVISIONS["planner"]

    qa_sweep = node_by_key(plan, "qa_sweep")
    assert [criteria.slot for criteria in qa_sweep.criteria] == ["implementation_loop_requirements"]
    assert qa_sweep.policy is None
    assert qa_sweep.policy_revision_no is None
    assert qa_sweep.role_revision_no == ROLE_REVISIONS["architect"]

    root = node_by_key(plan, "root")
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
