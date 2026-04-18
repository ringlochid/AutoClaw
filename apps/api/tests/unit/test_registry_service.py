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
from app.core.errors import InvalidDefinitionError


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


def test_load_role_seed_rejects_filename_id_mismatch(tmp_path: Path) -> None:
    mismatched = tmp_path / "wrong-name.yaml"
    mismatched.write_text(
        """
id: planner-supervisor
kind: supervisor
description: mismatch
allowed_modes:
  - plan
default_policy: default
checkpoint_schema: supervisor_status_v1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    try:
        load_role_seed(mismatched)
    except InvalidDefinitionError as exc:
        assert "filename stem" in str(exc)
    else:
        raise AssertionError("Expected filename/id mismatch to be rejected")


def test_iter_definition_files_uses_configured_definitions_root(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    definitions_root = tmp_path / "defs"
    role_dir = definitions_root / "roles"
    role_dir.mkdir(parents=True, exist_ok=True)
    role_file = role_dir / "custom-role.yaml"
    role_file.write_text(
        """
id: custom-role
kind: supervisor
description: custom role
allowed_modes:
  - plan
default_policy: default
checkpoint_schema: supervisor_status_v1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    config_path = tmp_path / "autoclaw-config.toml"
    config_path.write_text(
        f"""
[paths]
definitions_root = {str(definitions_root)!r}

[security]
api_key = "config-api-key"
internal_api_key = "config-internal-key"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("AUTOCLAW_CONFIG", str(config_path))
    monkeypatch.delenv(registry_service.DEFINITIONS_ROOT_ENV, raising=False)
    files = iter_definition_files("roles")
    names = [Path(path.name).name for path in files]

    assert "custom-role.yaml" in names
    assert names[-1] == "custom-role.yaml"
    assert len(names) > 1
    assert load_role_seed(files[-1]).id == "custom-role"
