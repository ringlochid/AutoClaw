from pydantic import ValidationError as PydanticValidationError

from app.core.errors import InvalidDefinitionError
from app.schemas.registry import (
    PolicyDefinitionSeed,
    RoleDefinitionSeed,
    WorkflowDefinitionSeed,
)


def parse_role_content(content: dict) -> RoleDefinitionSeed:
    try:
        return RoleDefinitionSeed.model_validate(content)
    except PydanticValidationError as exc:
        raise InvalidDefinitionError(f"Invalid role definition content: {exc}") from exc


def parse_policy_content(content: dict) -> PolicyDefinitionSeed:
    try:
        return PolicyDefinitionSeed.model_validate(content)
    except PydanticValidationError as exc:
        raise InvalidDefinitionError(f"Invalid policy definition content: {exc}") from exc


def parse_workflow_content(content: dict) -> WorkflowDefinitionSeed:
    try:
        return WorkflowDefinitionSeed.model_validate(content)
    except PydanticValidationError as exc:
        raise InvalidDefinitionError(f"Invalid workflow definition content: {exc}") from exc
