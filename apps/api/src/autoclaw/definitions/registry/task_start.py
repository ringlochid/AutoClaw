from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.interfaces.http.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime import FlowStatus, RuntimeLaunchInput, launch_task_runtime
from autoclaw.runtime.contracts import TaskStartRequest, TaskStartResponse, WorkflowManifestRef
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.flow import WORKFLOW_MANIFEST_REF_DESCRIPTION
from autoclaw.runtime.ids import compiled_plan_id_for_task, flow_id_for_task, flow_revision_id


async def start_task_from_definition_service(
    session: AsyncSession,
    request: TaskStartRequest,
    *,
    data_dir: Path,
) -> TaskStartResponse:
    task_id = _mint_task_id(request.task.key)
    task_root = data_dir / "tasks" / task_id
    try:
        result = await launch_task_runtime(
            session,
            RuntimeLaunchInput(
                task_id=task_id,
                task_root=task_root,
                task_compose=request,
                compiler_version="phase-5a-public-http",
            ),
        )
    except ValueError as exc:
        raise _translate_task_start_error(exc) from exc
    return TaskStartResponse(
        task_id=task_id,
        compiled_plan_id=compiled_plan_id_for_task(task_id),
        active_flow_revision_id=flow_revision_id(flow_id_for_task(task_id), 1),
        flow_status=FlowStatus.RUNNING,
        workflow_manifest_ref=WorkflowManifestRef(
            path=result.paths.runtime_path / "workflow-manifest.md",
            description=WORKFLOW_MANIFEST_REF_DESCRIPTION,
        ),
    )


def _task_start_invalid_error(summary: str) -> RuntimeOperationError:
    return RuntimeOperationError(
        code=OperationFailureCode.INVALID_REQUEST_SHAPE,
        summary=summary,
        is_retryable=False,
        suggested_next_step=(
            "Reread the canonical task-start request and resend it with a legal workflow key "
            "and root-binding shape."
        ),
        status_code_override=422,
    )


def _mint_task_id(task_key: str) -> str:
    normalized_key = re.sub(r"[^a-z0-9]+", "-", task_key.casefold()).strip("-")
    return f"task_{normalized_key or 'task'}_{uuid4().hex[:12]}"


def _translate_task_start_error(
    exc: ValueError,
) -> RuntimeOperationError | FileNotFoundError | ValueError:
    summary = str(exc)
    if "unknown definition key" in summary:
        return FileNotFoundError(summary)
    if (
        "workspace host path already held by live task" in summary
        or "host path does not exist" in summary
        or "does not match compiled plan workflow key" in summary
    ):
        return _task_start_invalid_error(summary)
    return exc


__all__ = ["start_task_from_definition_service"]
