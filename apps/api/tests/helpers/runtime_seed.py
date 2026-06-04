from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from autoclaw.registry import upsert_workflow_definition
from autoclaw.runtime import RuntimeLaunchInput, TaskComposeInput, launch_task_runtime
from autoclaw.schemas.definitions import (
    WorkflowDefinitionFile,
)
from autoclaw.schemas.definitions.workflow import WorkflowDefinitionInput
from sqlalchemy.ext.asyncio import AsyncSession

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFINITIONS_ROOT = REPO_ROOT / "definitions"


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def load_workflow_definition(name: str) -> WorkflowDefinitionFile:
    return WorkflowDefinitionFile.model_validate(
        _load_yaml(DEFINITIONS_ROOT / "workflows" / f"{name}.yaml")
    )


async def launch_seeded_runtime(
    session: AsyncSession,
    *,
    task_id: str,
    task_root: Path,
    task_compose: TaskComposeInput,
    compiler_version: str = "phase-3-runtime",
    workflow_definition: WorkflowDefinitionInput | None = None,
) -> None:
    if workflow_definition is not None:
        await upsert_workflow_definition(session, workflow_definition)
    await launch_task_runtime(
        session,
        RuntimeLaunchInput(
            task_id=task_id,
            task_root=task_root,
            task_compose=task_compose,
            compiler_version=compiler_version,
        ),
    )


def task_compose_payload(workflow_key: str, **roots: Any) -> TaskComposeInput:
    payload: dict[str, Any] = {
        "task": {
            "key": "auth-refresh-hardening",
            "title": "Harden auth refresh flow",
            "summary": "Investigate and fix the auth refresh regression.",
            "instruction": "Stay scoped to the auth refresh failure path only.",
        },
        "workflow": {"key": workflow_key},
    }
    if roots:
        payload["roots"] = roots
    return TaskComposeInput.model_validate(payload)
