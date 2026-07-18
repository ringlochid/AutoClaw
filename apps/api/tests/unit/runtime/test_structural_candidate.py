from autoclaw.definitions.contracts.workflow import NodeKind
from autoclaw.runtime.node_operations.structural_candidate.models import (
    StructuralNodeCandidate,
)
from autoclaw.runtime.node_operations.structural_candidate.validation import (
    build_structural_revision_candidate,
)


def test_structural_candidate_accepts_a_nonliteral_root_node_key() -> None:
    root = StructuralNodeCandidate(
        node_key="primary",
        parent_node_key=None,
        structural_kind=NodeKind.ROOT,
        role_key="role.root",
        role_revision_no=1,
        role_description="Root role.",
        role_instruction=None,
        policy_key="policy.root",
        policy_revision_no=1,
        policy_description="Root policy.",
        policy_instruction=None,
        description="Coordinate the task.",
        node_instruction=None,
        local_consumes=None,
        consumes=None,
        produces=None,
        own_criteria=(),
        criteria=(),
        child_defaults=None,
        child_node_keys=(),
        state="ready",
        current_assignment_id=None,
        order_index=0,
    )

    candidate = build_structural_revision_candidate(
        {root.node_key: root},
        previous_criteria={},
    )

    assert [node.node_key for node in candidate.nodes] == ["primary"]
