"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.fixtures as _owner

agent_accepted_fixture = _owner.agent_accepted_fixture
agent_wait_fixture = _owner.agent_wait_fixture
auth_token_mismatch_fixture = _owner.auth_token_mismatch_fixture
connect_challenge_fixture = _owner.connect_challenge_fixture
hello_ok_fixture = _owner.hello_ok_fixture
sessions_abort_fixture = _owner.sessions_abort_fixture

__all__ = [
    "agent_accepted_fixture",
    "agent_wait_fixture",
    "auth_token_mismatch_fixture",
    "connect_challenge_fixture",
    "hello_ok_fixture",
    "sessions_abort_fixture",
]
