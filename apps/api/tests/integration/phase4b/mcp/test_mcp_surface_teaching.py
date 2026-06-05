from __future__ import annotations

from autoclaw.interfaces.mcp.node.server import create_node_mcp_server
from autoclaw.interfaces.mcp.operator.server import create_operator_mcp_server
from tests.integration.phase4b.mcp.support import default_transport_security


async def test_phase4b_operator_mcp_server_instructions_teach_observe_vs_mutate() -> None:
    server = create_operator_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1")
    )
    instructions = server.instructions
    assert instructions is not None
    assert "Observe first" in instructions
    assert "Mutating controls" in instructions
    assert "Support-state refs" in instructions
    assert "Phase boundary" in instructions
    assert "Definition/task-start writes" in instructions


async def test_phase4b_node_mcp_server_instructions_teach_lookup_and_mutation() -> None:
    server = create_node_mcp_server(
        transport_security=default_transport_security(host="127.0.0.1"),
    )
    instructions = server.instructions
    assert instructions is not None
    assert "Lookup" in instructions
    assert "Persist progress" in instructions
    assert "Close the current turn" in instructions
    assert "Not for operator control" in instructions
