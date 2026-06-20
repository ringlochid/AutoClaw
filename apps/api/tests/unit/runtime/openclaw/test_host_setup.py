from __future__ import annotations

import json
from pathlib import Path

from autoclaw.integrations.openclaw.gateway.discovery import OpenClawResolvedHostState
from autoclaw.integrations.openclaw.gateway.host_setup import (
    AUTOCLAW_WORKER_AGENT_ID,
    WORKER_OPERATOR_TOOL_DENY,
    WORKER_RUNTIME_TOOL_DENY,
    build_autoclaw_agent_entries,
)


def _host_state(config_path: Path) -> OpenClawResolvedHostState:
    return OpenClawResolvedHostState(
        binary_path="/usr/bin/openclaw",
        binary_found=True,
        config_path=str(config_path),
        config_exists=True,
        base_url="http://127.0.0.1:18789",
        ws_url="ws://127.0.0.1:18789",
        loopback=True,
        support_status="supported",
    )


def test_build_autoclaw_agent_entries_replaces_worker_tool_denies_with_operator_deny(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "openclaw.json"
    config_path.write_text(
        json.dumps(
            {
                "agents": {
                    "list": [
                        {
                            "id": AUTOCLAW_WORKER_AGENT_ID,
                            "tools": {"deny": ["existing-deny", "group:ui"]},
                        },
                        {
                            "id": "orin",
                            "tools": {"deny": ["existing-operator-deny"]},
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    entries = build_autoclaw_agent_entries(
        _host_state(config_path),
        worker_agent_id=AUTOCLAW_WORKER_AGENT_ID,
        operator_agent_id="orin",
    )

    worker_tools = entries[AUTOCLAW_WORKER_AGENT_ID]["tools"]
    worker_deny = worker_tools["deny"]

    assert worker_tools["profile"] == "full"
    assert worker_deny == list(WORKER_RUNTIME_TOOL_DENY)
    assert worker_deny.count(WORKER_OPERATOR_TOOL_DENY) == 1
