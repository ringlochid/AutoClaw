from __future__ import annotations

from .support import (
    EXPECTED_WORKFLOW_IDS,
    assert_expected_role_and_policy_ids,
    load_definition_tree,
    load_registry_catalog,
    load_workflow_ids,
    resolve_committed_seed_definitions_root,
)


def test_packaged_role_and_policy_seed_definitions_validate() -> None:
    with resolve_committed_seed_definitions_root() as definitions_root:
        roles, policies = load_registry_catalog(definitions_root)

    assert_expected_role_and_policy_ids(roles, policies)


def test_packaged_workflow_seed_definitions_validate_against_packaged_catalog() -> None:
    with resolve_committed_seed_definitions_root() as definitions_root:
        roles, policies = load_registry_catalog(definitions_root)
        workflow_ids = load_workflow_ids(
            definitions_root,
            roles=roles,
            policies=policies,
        )

    assert workflow_ids == EXPECTED_WORKFLOW_IDS


def test_packaged_seed_tree_contains_expected_definition_files() -> None:
    with resolve_committed_seed_definitions_root() as definitions_root:
        packaged_tree = load_definition_tree(definitions_root)

    assert set(packaged_tree) == {
        "policies/standard_parent_planning.yaml",
        "policies/standard_release.yaml",
        "policies/standard_review.yaml",
        "policies/standard_root_planning.yaml",
        "policies/standard_worker.yaml",
        "roles/architect.yaml",
        "roles/engineer.yaml",
        "roles/planner.yaml",
        "roles/planning_lead.yaml",
        "roles/release_operator.yaml",
        "roles/researcher.yaml",
        "roles/reviewer.yaml",
        "roles/root_planning_lead.yaml",
        "workflows/maximal_parent_first_release.yaml",
        "workflows/minimal_implement_change.yaml",
        "workflows/normal_parent_first_release.yaml",
    }
