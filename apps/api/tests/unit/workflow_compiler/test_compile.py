from __future__ import annotations

import pytest

from .support import (
    POLICY_REVISIONS,
    ROLE_REVISIONS,
    WORKFLOW_COMPILER_TEST_VERSION,
    compile_packaged_workflow_fixture,
    node_by_key,
)


def test_compile_minimal_workflow_smoke() -> None:
    plan = compile_packaged_workflow_fixture("minimal_implement_change", revision_no=4)

    assert plan.workflow_key == "minimal-implement-change"
    assert plan.definition_revision_no == 4
    assert plan.compiler_version == WORKFLOW_COMPILER_TEST_VERSION
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
    plan = compile_packaged_workflow_fixture("normal_parent_first_release", revision_no=7)

    assert plan.workflow_key == "normal-parent-first-release"
    assert plan.definition_revision_no == 7
    assert plan.compiler_version == WORKFLOW_COMPILER_TEST_VERSION

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
    plan = compile_packaged_workflow_fixture("maximal_parent_first_release", revision_no=11)

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


def test_compile_bugfix_review_release_workflow_normalizes_specialist_edges() -> None:
    plan = compile_packaged_workflow_fixture("bugfix_review_release", revision_no=13)

    assert plan.workflow_key == "bugfix-review-release"
    assert [node.node_key for node in plan.nodes] == [
        "root",
        "triage_defect",
        "plan_fix",
        "implement_fix",
        "verify_fix",
        "review_fix",
        "analyze_failure",
        "release_closure",
    ]
    assert {node.node_key: node.structural_kind.value for node in plan.nodes} == {
        "root": "root",
        "triage_defect": "worker",
        "plan_fix": "worker",
        "implement_fix": "worker",
        "verify_fix": "worker",
        "review_fix": "worker",
        "analyze_failure": "worker",
        "release_closure": "worker",
    }

    triage_defect = node_by_key(plan, "triage_defect")
    assert triage_defect.role_revision_no == ROLE_REVISIONS["bug_triage"]
    assert triage_defect.policy_revision_no == POLICY_REVISIONS["standard-worker"]

    plan_fix = node_by_key(plan, "plan_fix")
    assert plan_fix.role_revision_no == ROLE_REVISIONS["delivery_planner"]
    assert plan_fix.policy_revision_no == POLICY_REVISIONS["standard-delivery-planning"]

    verify_fix = node_by_key(plan, "verify_fix")
    assert verify_fix.role_revision_no == ROLE_REVISIONS["test_verifier"]
    assert verify_fix.policy_revision_no == POLICY_REVISIONS["standard-verification"]

    analyze_failure = node_by_key(plan, "analyze_failure")
    assert analyze_failure.role_revision_no == ROLE_REVISIONS["failure_analyst"]
    assert analyze_failure.policy_revision_no == POLICY_REVISIONS["standard-failure-analysis"]

    assert [
        (
            edge.provider_node_key,
            edge.consumer_node_key,
            edge.kind.value,
            edge.slot,
        )
        for edge in plan.dependency_edges
    ] == [
        ("triage_defect", "plan_fix", "artifact", "triage_report"),
        ("triage_defect", "implement_fix", "artifact", "triage_report"),
        ("plan_fix", "implement_fix", "artifact", "fix_plan"),
        ("triage_defect", "verify_fix", "artifact", "triage_report"),
        ("implement_fix", "verify_fix", "artifact", "change_patch"),
        ("implement_fix", "verify_fix", "criteria", "fix_implementation_criteria"),
        ("implement_fix", "review_fix", "artifact", "change_patch"),
        ("verify_fix", "review_fix", "artifact", "verification_report"),
        ("root", "review_fix", "criteria", "root_bugfix_release_criteria"),
        ("triage_defect", "analyze_failure", "artifact", "triage_report"),
        ("verify_fix", "analyze_failure", "artifact", "verification_report"),
        ("review_fix", "analyze_failure", "artifact", "review_report"),
        ("triage_defect", "release_closure", "artifact", "triage_report"),
        ("implement_fix", "release_closure", "artifact", "change_patch"),
        ("verify_fix", "release_closure", "artifact", "verification_report"),
        ("review_fix", "release_closure", "artifact", "review_report"),
        ("root", "release_closure", "criteria", "root_bugfix_release_criteria"),
    ]


def test_compile_delivery_batch_workflow_normalizes_parent_and_worker_edges() -> None:
    plan = compile_packaged_workflow_fixture("delivery_batch", revision_no=17)

    assert plan.workflow_key == "delivery-batch"
    assert [node.node_key for node in plan.nodes] == [
        "root",
        "plan_packages",
        "execute_package",
        "implement_package",
        "verify_package",
        "review_package",
        "release_closure",
    ]
    assert {node.node_key: node.structural_kind.value for node in plan.nodes} == {
        "root": "root",
        "plan_packages": "worker",
        "execute_package": "parent",
        "implement_package": "worker",
        "verify_package": "worker",
        "review_package": "worker",
        "release_closure": "worker",
    }

    plan_packages = node_by_key(plan, "plan_packages")
    assert plan_packages.role_revision_no == ROLE_REVISIONS["delivery_planner"]
    assert plan_packages.policy_revision_no == POLICY_REVISIONS["standard-delivery-planning"]

    execute_package = node_by_key(plan, "execute_package")
    assert execute_package.role_revision_no == ROLE_REVISIONS["planning_lead"]
    assert execute_package.policy_revision_no == POLICY_REVISIONS["standard-parent-planning"]

    review_package = node_by_key(plan, "review_package")
    assert review_package.role_revision_no == ROLE_REVISIONS["code_reviewer"]
    assert review_package.policy_revision_no == POLICY_REVISIONS["standard-review"]

    assert [
        (
            edge.provider_node_key,
            edge.consumer_node_key,
            edge.kind.value,
            edge.slot,
        )
        for edge in plan.dependency_edges
    ] == [
        ("plan_packages", "execute_package", "artifact", "package_plan"),
        ("plan_packages", "implement_package", "artifact", "package_plan"),
        ("plan_packages", "verify_package", "artifact", "package_plan"),
        ("implement_package", "verify_package", "artifact", "package_patch"),
        ("implement_package", "review_package", "artifact", "package_patch"),
        (
            "verify_package",
            "review_package",
            "artifact",
            "package_verification_report",
        ),
        ("execute_package", "review_package", "criteria", "package_subtree_criteria"),
        ("plan_packages", "release_closure", "artifact", "package_plan"),
        ("implement_package", "release_closure", "artifact", "package_patch"),
        (
            "verify_package",
            "release_closure",
            "artifact",
            "package_verification_report",
        ),
        (
            "review_package",
            "release_closure",
            "artifact",
            "package_review_report",
        ),
        ("root", "release_closure", "criteria", "package_release_criteria"),
    ]


@pytest.mark.parametrize(
    ("fixture_name", "workflow_key", "node_keys"),
    [
        (
            "idea_discovery",
            "idea-discovery",
            [
                "root",
                "gather_context",
                "shape_options",
                "critique_options",
                "recommend_direction",
            ],
        ),
        (
            "planning_only",
            "planning-only",
            [
                "root",
                "define_scope",
                "map_work",
                "review_plan_scope",
                "publish_final_plan",
            ],
        ),
        (
            "mvp_build",
            "mvp-build",
            [
                "root",
                "discover_mvp_value",
                "implement_mvp_slice",
                "verify_demo_path",
                "review_mvp_code",
                "review_product_fit",
                "release_closure",
            ],
        ),
        (
            "core_only_build",
            "core-only-build",
            [
                "root",
                "design_core_contracts",
                "implement_core",
                "verify_core_contracts",
                "review_core_design",
                "release_closure",
            ],
        ),
        (
            "feature_implementation",
            "feature-implementation",
            [
                "root",
                "inspect_existing_context",
                "plan_feature_integration",
                "review_feature_scope",
                "implement_feature",
                "verify_feature",
                "review_feature",
                "release_closure",
            ],
        ),
        (
            "marketing_campaign",
            "marketing-campaign",
            [
                "root",
                "research_audience",
                "shape_positioning",
                "review_campaign_risk",
                "prepare_campaign_package",
            ],
        ),
        (
            "project_management_delivery",
            "project-management-delivery",
            [
                "root",
                "capture_objectives",
                "decompose_work",
                "review_delivery_risks",
                "publish_delivery_plan",
            ],
        ),
    ],
)
def test_compile_new_workflow_archetype_seed_smoke(
    fixture_name: str,
    workflow_key: str,
    node_keys: list[str],
) -> None:
    plan = compile_packaged_workflow_fixture(fixture_name, revision_no=23)

    assert plan.workflow_key == workflow_key
    assert [node.node_key for node in plan.nodes] == node_keys
    assert node_by_key(plan, "root").role_revision_no == ROLE_REVISIONS["root_planning_lead"]
    assert (
        node_by_key(plan, "root").policy_revision_no == POLICY_REVISIONS["standard-root-planning"]
    )
    assert plan.dependency_edges
