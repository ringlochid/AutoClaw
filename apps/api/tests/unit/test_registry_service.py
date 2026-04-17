from pathlib import Path

from pytest import MonkeyPatch

from app.core.enums import SkillProvider, WorkflowMode
from app.services import registry_service
from app.services.registry_service import (
    iter_definition_files,
    load_policy_seed,
    load_role_seed,
    load_workflow_seed,
)


def test_role_seed_loads() -> None:
    role_files = iter_definition_files("roles")
    assert role_files

    role = load_role_seed(role_files[0])
    assert role.id
    assert (
        WorkflowMode.PLAN in role.allowed_modes
        or WorkflowMode.PERSISTENT_EXECUTE in role.allowed_modes
    )


def test_policy_seed_loads() -> None:
    policy_files = iter_definition_files("policies")
    assert policy_files

    policy = load_policy_seed(policy_files[0])
    assert policy.id
    assert isinstance(policy.rules, dict)


def test_workflow_seed_loads_and_skill_refs_parse() -> None:
    workflow_files = iter_definition_files("workflows")
    assert workflow_files

    base_workflow_file = next(
        path for path in workflow_files if Path(path.name).stem == "default-bugfix"
    )
    workflow = load_workflow_seed(base_workflow_file)

    assert workflow.id == "default-bugfix"
    assert workflow.nodes
    assert workflow.skill_refs
    assert workflow.skill_refs[0].provider is SkillProvider.OPENCLAW


def test_packaged_definition_resources_work_without_repo_root(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(registry_service, "DEFINITIONS_ROOT", Path("/tmp/definitely-missing"))
    monkeypatch.delenv(registry_service.DEFINITIONS_ROOT_ENV, raising=False)

    role_files = iter_definition_files("roles")
    assert role_files

    role = load_role_seed(role_files[0])
    assert role.id
