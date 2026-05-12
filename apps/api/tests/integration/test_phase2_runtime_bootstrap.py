from __future__ import annotations

from tests.integration.test_phase2_runtime_bootstrap_fixtures import (
    compile_workflow_fixture,
    load_seeded_lookup,
    load_workflow_definition,
    persist_bootstrap_runtime,
    seed_child_terminal_retry_checkpoint,
    seed_dispatch,
    task_compose_payload,
)

__all__ = [
    "compile_workflow_fixture",
    "load_seeded_lookup",
    "load_workflow_definition",
    "persist_bootstrap_runtime",
    "seed_child_terminal_retry_checkpoint",
    "seed_dispatch",
    "task_compose_payload",
]


def test_task_compose_payload_smoke() -> None:
    payload = task_compose_payload("minimal-implement-change")

    assert payload.workflow.key == "minimal-implement-change"
    assert payload.task.key == "auth-refresh-hardening"
