from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from app.compiler import (
    MappingRolePolicyLookup,
    NormalizedCompiledPlan,
    PolicyRevisionDefinition,
    RoleRevisionDefinition,
    WorkflowRevisionMetadata,
    compile_workflow,
)
from app.runtime import TaskComposeInput
from app.schemas.definitions import (
    PolicyDefinitionFile,
    RoleDefinitionFile,
    WorkflowDefinitionFile,
)
from app.schemas.workflow_definitions import WorkflowDefinitionInput

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFINITIONS_ROOT = REPO_ROOT / "definitions"

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


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def load_seeded_lookup() -> MappingRolePolicyLookup:
    roles = {
        role.id: RoleRevisionDefinition(
            definition=role,
            revision_no=ROLE_REVISIONS[role.id],
        )
        for role in (
            RoleDefinitionFile.model_validate(_load_yaml(path))
            for path in sorted((DEFINITIONS_ROOT / "roles").glob("*.yaml"))
        )
    }
    policies = {
        policy.id: PolicyRevisionDefinition(
            definition=policy,
            revision_no=POLICY_REVISIONS[policy.id],
        )
        for policy in (
            PolicyDefinitionFile.model_validate(_load_yaml(path))
            for path in sorted((DEFINITIONS_ROOT / "policies").glob("*.yaml"))
        )
    }
    return MappingRolePolicyLookup(roles=roles, policies=policies)


def load_workflow_definition(name: str) -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        _load_yaml(DEFINITIONS_ROOT / "workflows" / f"{name}.yaml")
    )


def compile_seeded_workflow(
    workflow_definition: WorkflowDefinitionInput,
    revision_no: int,
    *,
    compiler_version: str = "phase-3-runtime",
) -> NormalizedCompiledPlan:
    return compile_workflow(
        workflow=workflow_definition,
        workflow_revision=WorkflowRevisionMetadata(
            workflow_key=workflow_definition.id,
            definition_revision_no=revision_no,
        ),
        compiler_version=compiler_version,
        lookup=load_seeded_lookup(),
    )


def task_compose_payload(workflow_key: str, **roots: Any) -> TaskComposeInput:
    payload: dict[str, Any] = {
        "task": {
            "key": "auth-refresh-hardening",
            "title": "Harden auth refresh flow",
            "summary": "Investigate and fix the auth refresh regression.",
            "instruction": "Stay scoped to the auth refresh failure path only.",
        },
        "workflow": {"key": workflow_key},
    }
    if roots:
        payload["roots"] = roots
    return TaskComposeInput.model_validate(payload)
