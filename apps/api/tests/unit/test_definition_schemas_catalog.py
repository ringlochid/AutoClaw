from __future__ import annotations

from importlib import resources

from tests.unit.definition_schema_test_support import (
    AUTHORED_DEFINITIONS_ROOT,
    EXPECTED_WORKFLOW_IDS,
    PACKAGED_SEED_DEFINITIONS_ROOT,
    assert_expected_role_and_policy_ids,
    load_definition_tree,
    load_registry_catalog,
    load_workflow_ids,
)


def test_authored_role_and_policy_fixtures_validate() -> None:
    roles, policies = load_registry_catalog(AUTHORED_DEFINITIONS_ROOT)

    assert_expected_role_and_policy_ids(roles, policies)


def test_packaged_role_and_policy_seed_definitions_validate() -> None:
    with resources.as_file(PACKAGED_SEED_DEFINITIONS_ROOT) as packaged_seed_root:
        roles, policies = load_registry_catalog(packaged_seed_root)

    assert_expected_role_and_policy_ids(roles, policies)


def test_authored_workflow_fixtures_validate_against_authored_catalog() -> None:
    roles, policies = load_registry_catalog(AUTHORED_DEFINITIONS_ROOT)
    workflow_ids = load_workflow_ids(
        AUTHORED_DEFINITIONS_ROOT,
        roles=roles,
        policies=policies,
    )

    assert workflow_ids == EXPECTED_WORKFLOW_IDS


def test_packaged_workflow_seed_definitions_validate_against_packaged_catalog() -> None:
    with resources.as_file(PACKAGED_SEED_DEFINITIONS_ROOT) as packaged_seed_root:
        roles, policies = load_registry_catalog(packaged_seed_root)
        workflow_ids = load_workflow_ids(
            packaged_seed_root,
            roles=roles,
            policies=policies,
        )

    assert workflow_ids == EXPECTED_WORKFLOW_IDS


def test_packaged_seed_tree_matches_repo_authored_definition_fixtures() -> None:
    authored_tree = load_definition_tree(AUTHORED_DEFINITIONS_ROOT)

    with resources.as_file(PACKAGED_SEED_DEFINITIONS_ROOT) as packaged_seed_root:
        packaged_tree = load_definition_tree(packaged_seed_root)

    assert packaged_tree == authored_tree
