from __future__ import annotations

from autoclaw.definitions.contracts import PolicyDefinitionInput
from autoclaw.runtime.capabilities import (
    capability_rejection_for_command_run,
    capability_rejection_for_human_request,
    denied_effective_capabilities,
    resolve_effective_capabilities_from_policy_content,
)
from autoclaw.runtime.contracts import CapabilityDecision, OperationFailureCode


def test_effective_capabilities_deny_when_policy_is_missing() -> None:
    capabilities = resolve_effective_capabilities_from_policy_content(
        None,
        execution_scope="dispatch",
    )

    assert capabilities.human_request.direction == CapabilityDecision.DENY
    assert capabilities.human_request.approval == CapabilityDecision.DENY
    assert capabilities.human_request.input == CapabilityDecision.DENY
    assert capabilities.human_request.review == CapabilityDecision.DENY
    assert capabilities.command_run == CapabilityDecision.DENY


def test_effective_capabilities_ignore_stale_allowed_kinds_under_deny() -> None:
    capabilities = resolve_effective_capabilities_from_policy_content(
        {
            "id": "quiet-worker",
            "description": "Policy with stale request kinds under deny.",
            "applies_to": ["worker"],
            "capabilities": {
                "human_request": {
                    "mode": "deny",
                    "allowed_kinds": ["review"],
                },
                "command_run": "deny",
            },
        },
        execution_scope="dispatch",
    )

    assert capabilities.human_request.review == CapabilityDecision.DENY
    assert capabilities.command_run == CapabilityDecision.DENY


def test_effective_capabilities_allow_only_listed_human_request_kinds() -> None:
    capabilities = resolve_effective_capabilities_from_policy_content(
        {
            "id": "interactive-worker",
            "description": "Policy that grants selected human request kinds.",
            "applies_to": ["worker"],
            "capabilities": {
                "human_request": {
                    "mode": "allow",
                    "allowed_kinds": ["direction", "input"],
                },
            },
        },
        execution_scope="dispatch",
    )

    assert capabilities.human_request.direction == CapabilityDecision.ALLOW
    assert capabilities.human_request.input == CapabilityDecision.ALLOW
    assert capabilities.human_request.approval == CapabilityDecision.DENY
    assert capabilities.human_request.review == CapabilityDecision.DENY
    assert capabilities.command_run == CapabilityDecision.DENY


def test_effective_capabilities_resolve_command_run_allow() -> None:
    policy = PolicyDefinitionInput.model_validate(
        {
            "id": "command-worker",
            "description": "Policy that grants the controller-managed command-run lane.",
            "applies_to": ["worker"],
            "capabilities": {
                "human_request": {
                    "mode": "allow",
                    "allowed_kinds": ["approval"],
                },
                "command_run": "allow",
            },
        }
    )

    capabilities = resolve_effective_capabilities_from_policy_content(
        policy,
        execution_scope="command_run_start",
    )

    assert capabilities.execution_scope == "command_run_start"
    assert capabilities.human_request.approval == CapabilityDecision.ALLOW
    assert capabilities.command_run == CapabilityDecision.ALLOW


def test_capability_rejection_names_target_and_next_action() -> None:
    capabilities = denied_effective_capabilities(execution_scope="human_request_open")
    human_request_rejection = capability_rejection_for_human_request(capabilities, "review")
    command_run_rejection = capability_rejection_for_command_run(capabilities)

    assert human_request_rejection is not None
    assert human_request_rejection.code == OperationFailureCode.CAPABILITY_REJECTED
    assert human_request_rejection.capability == "human_request.review"
    assert "does not allow human_request.review" in human_request_rejection.message
    assert human_request_rejection.next_legal_action is None
    assert command_run_rejection is not None
    assert command_run_rejection.code == OperationFailureCode.CAPABILITY_REJECTED
    assert command_run_rejection.capability == "command_run"
    assert "controller-managed command_run" in command_run_rejection.message
    assert command_run_rejection.next_legal_action == (
        "avoid long command; for example, run focused tests one by one rather than the whole "
        "test suite"
    )
