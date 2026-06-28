from __future__ import annotations

from .support import (
    EXPECTED_WORKFLOW_IDS,
    REFERENCE_DEFINITIONS_ROOT,
    assert_expected_role_and_policy_ids,
    load_definition_tree,
    load_first_yaml_fence,
    load_registry_catalog,
    load_workflow_ids,
    resolve_committed_seed_definitions_root,
)


def _normalize_definition_payload(payload: object) -> object:
    if isinstance(payload, dict):
        return {key: _normalize_definition_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_normalize_definition_payload(value) for value in payload]
    if isinstance(payload, str):
        return payload.rstrip("\n")
    return payload


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
        "policies/standard_long_command_worker.yaml",
        "policies/standard_marketing_planning.yaml",
        "policies/standard_parent_planning.yaml",
        "policies/standard_product_planning.yaml",
        "policies/standard_project_management.yaml",
        "policies/standard_release.yaml",
        "policies/standard_review.yaml",
        "policies/standard_root_planning.yaml",
        "policies/standard_scope_review.yaml",
        "policies/standard_failure_analysis.yaml",
        "policies/standard_verification.yaml",
        "policies/standard_worker.yaml",
        "policies/standard_delivery_planning.yaml",
        "roles/architect.yaml",
        "roles/bug_fix_engineer.yaml",
        "roles/bug_triage.yaml",
        "roles/code_reviewer.yaml",
        "roles/core_architect.yaml",
        "roles/engineer.yaml",
        "roles/failure_analyst.yaml",
        "roles/market_researcher.yaml",
        "roles/marketing_strategist.yaml",
        "roles/planner.yaml",
        "roles/planning_lead.yaml",
        "roles/product_planner.yaml",
        "roles/product_reviewer.yaml",
        "roles/project_manager.yaml",
        "roles/release_operator.yaml",
        "roles/replan_planner.yaml",
        "roles/researcher.yaml",
        "roles/reviewer.yaml",
        "roles/root_planning_lead.yaml",
        "roles/scope_reviewer.yaml",
        "roles/test_verifier.yaml",
        "roles/delivery_planner.yaml",
        "workflows/bugfix_review_release.yaml",
        "workflows/core_only_build.yaml",
        "workflows/feature_implementation.yaml",
        "workflows/idea_discovery.yaml",
        "workflows/maximal_parent_first_release.yaml",
        "workflows/minimal_implement_change.yaml",
        "workflows/marketing_campaign.yaml",
        "workflows/mvp_build.yaml",
        "workflows/normal_parent_first_release.yaml",
        "workflows/delivery_batch.yaml",
        "workflows/planning_only.yaml",
        "workflows/project_management_delivery.yaml",
    }


def test_reference_definition_pages_mirror_packaged_seed_definitions() -> None:
    workflow_page_stems_by_seed_stem = {
        "maximal_parent_first_release": "maximal",
        "minimal_implement_change": "minimal",
        "normal_parent_first_release": "normal",
    }

    with resolve_committed_seed_definitions_root() as definitions_root:
        packaged_tree = load_definition_tree(definitions_root)

    for relative_path, seed_payload in packaged_tree.items():
        category, file_name = relative_path.split("/")
        seed_stem = file_name.removesuffix(".yaml")
        if category == "workflows":
            page_stem = workflow_page_stems_by_seed_stem.get(
                seed_stem,
                seed_payload["id"],
            )
        else:
            page_stem = seed_payload["id"].replace("_", "-")

        reference_payload = load_first_yaml_fence(
            REFERENCE_DEFINITIONS_ROOT / category / f"{page_stem}.md"
        )

        assert _normalize_definition_payload(reference_payload) == _normalize_definition_payload(
            seed_payload
        )
