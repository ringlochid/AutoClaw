from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import yaml

from app.schemas.registry_definitions import (
    PolicyDefinitionFile,
    PolicyDefinitionInput,
    RoleDefinitionFile,
    RoleDefinitionInput,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFINITIONS_ROOT = REPO_ROOT / "definitions"


class ResolvedRole(NamedTuple):
    definition: RoleDefinitionInput
    revision_no: int


class ResolvedPolicy(NamedTuple):
    definition: PolicyDefinitionInput
    revision_no: int


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping content in {path}")
    return data


def load_role_definition(role_key: str) -> RoleDefinitionInput:
    path = DEFINITIONS_ROOT / "roles" / f"{role_key}.yaml"
    return RoleDefinitionFile.model_validate(_load_yaml(path))


def load_policy_definition(policy_key: str) -> PolicyDefinitionInput:
    path = DEFINITIONS_ROOT / "policies" / f"{policy_key}.yaml"
    return PolicyDefinitionFile.model_validate(_load_yaml(path))


def resolve_role(role_key: str, known_revision_no: int | None = None) -> ResolvedRole:
    return ResolvedRole(
        definition=load_role_definition(role_key),
        revision_no=known_revision_no or 1,
    )


def resolve_policy(policy_key: str, known_revision_no: int | None = None) -> ResolvedPolicy:
    return ResolvedPolicy(
        definition=load_policy_definition(policy_key),
        revision_no=known_revision_no or 1,
    )
