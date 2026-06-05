from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from autoclaw.definitions.compiler import (
    MappingRolePolicyLookup,
    PolicyRevisionDefinition,
    RoleRevisionDefinition,
    WorkflowRevisionMetadata,
    compile_workflow,
)
from autoclaw.definitions.contracts import (
    PolicyDefinitionFile,
    RoleDefinitionFile,
    WorkflowDefinitionFile,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
AUTHORED_DEFINITIONS_ROOT = REPO_ROOT / "definitions"
PACKAGED_SEED_DEFINITIONS_ROOT = resources.files("autoclaw.definitions.seeds")

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


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def load_packaged_seed_lookup() -> MappingRolePolicyLookup:
    with resources.as_file(PACKAGED_SEED_DEFINITIONS_ROOT) as packaged_seed_root:
        roles = {
            role.id: RoleRevisionDefinition(
                definition=role,
                revision_no=ROLE_REVISIONS[role.id],
            )
            for role in (
                RoleDefinitionFile.model_validate(load_yaml(path))
                for path in sorted((packaged_seed_root / "roles").glob("*.yaml"))
            )
        }
        policies = {
            policy.id: PolicyRevisionDefinition(
                definition=policy,
                revision_no=POLICY_REVISIONS[policy.id],
            )
            for policy in (
                PolicyDefinitionFile.model_validate(load_yaml(path))
                for path in sorted((packaged_seed_root / "policies").glob("*.yaml"))
            )
        }

    return MappingRolePolicyLookup(roles=roles, policies=policies)


def load_authored_workflow_fixture(name: str) -> WorkflowDefinitionFile:
    path = AUTHORED_DEFINITIONS_ROOT / "workflows" / f"{name}.yaml"
    return WorkflowDefinitionFile.model_validate(load_yaml(path))


def compile_authored_workflow_fixture(name: str, revision_no: int) -> Any:
    workflow = load_authored_workflow_fixture(name)
    return compile_workflow(
        workflow=workflow,
        workflow_revision=WorkflowRevisionMetadata(
            workflow_key=workflow.id,
            definition_revision_no=revision_no,
        ),
        compiler_version="phase-1-wave-2",
        lookup=load_packaged_seed_lookup(),
    )


def node_by_key(plan: Any, node_key: str) -> Any:
    return next(node for node in plan.nodes if node.node_key == node_key)
