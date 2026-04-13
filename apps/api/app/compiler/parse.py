from app.schemas.registry import (
    PolicyDefinitionSeed,
    RoleDefinitionSeed,
    WorkflowDefinitionSeed,
)


def parse_role_content(content: dict) -> RoleDefinitionSeed:
    return RoleDefinitionSeed.model_validate(content)


def parse_policy_content(content: dict) -> PolicyDefinitionSeed:
    return PolicyDefinitionSeed.model_validate(content)


def parse_workflow_content(content: dict) -> WorkflowDefinitionSeed:
    return WorkflowDefinitionSeed.model_validate(content)
