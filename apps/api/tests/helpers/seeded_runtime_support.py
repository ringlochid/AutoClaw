from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from autoclaw.definitions.contracts import (
    WorkflowDefinitionFile,
)
from autoclaw.definitions.contracts.workflow import WorkflowDefinitionInput
from autoclaw.definitions.registry import upsert_workflow_definition
from autoclaw.definitions.seeds import resolve_packaged_seed_definitions_root
from autoclaw.runtime import RuntimeLaunchInput, TaskComposeInput, launch_task_runtime
from sqlalchemy.ext.asyncio import AsyncSession


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def load_workflow_definition(name: str) -> WorkflowDefinitionFile:
    with resolve_packaged_seed_definitions_root() as definitions_root:
        return WorkflowDefinitionFile.model_validate(
            _load_yaml(definitions_root / "workflows" / f"{name}.yaml")
        )


async def launch_seeded_runtime(
    session: AsyncSession,
    *,
    task_id: str,
    task_root: Path,
    task_compose: TaskComposeInput,
    compiler_version: str = "runtime-seeded-test",
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
