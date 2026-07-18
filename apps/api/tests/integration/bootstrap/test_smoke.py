from __future__ import annotations

from autoclaw.runtime import TaskComposeInput


def test_task_compose_payload_smoke() -> None:
    payload = TaskComposeInput.model_validate(
        {
            "task": {
                "key": "settings-loader-cleanup",
                "title": "Clean up settings loader",
                "summary": "Make one scoped settings-loader change and publish evidence.",
                "instruction": "Stay scoped to the settings-loader path only.",
            },
            "workflow": {"key": "bounded-change"},
        }
    )

    assert payload.workflow.key == "bounded-change"
    assert payload.task.key == "settings-loader-cleanup"
