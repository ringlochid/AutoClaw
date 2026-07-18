from __future__ import annotations

import logging
import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.config import get_settings
from autoclaw.persistence.session import get_session_factory
from autoclaw.runtime import FlowStatus, RuntimeLaunchInput
from autoclaw.runtime.contracts import TaskStartRequest, TaskStartResponse, WorkflowManifestRef
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.flow import WORKFLOW_MANIFEST_REF_DESCRIPTION
from autoclaw.runtime.ids import compiled_plan_id_for_task, flow_id_for_task, flow_revision_id
from autoclaw.runtime.launch.service import StagedRuntimeLaunch, launch_task_runtime
from autoclaw.runtime.node_operations.follow_on import SupportProjectionPublisher
from autoclaw.runtime.post_commit import FlowStartCommitted, RuntimeEffectPublisher

logger = logging.getLogger(__name__)


async def start_task_from_definition(
    request: TaskStartRequest,
    *,
    data_dir: Path | None = None,
    session: AsyncSession | None = None,
    runtime_effect_publisher: RuntimeEffectPublisher | None = None,
    support_projection_publisher: SupportProjectionPublisher | None = None,
) -> TaskStartResponse:
    task_data_dir = data_dir if data_dir is not None else get_settings().data_dir
    if session is not None:
        return await _start_task_from_definition(
            session,
            request,
            data_dir=task_data_dir,
            runtime_effect_publisher=runtime_effect_publisher,
            support_projection_publisher=support_projection_publisher,
        )
    async with get_session_factory()() as owned_session:
        return await _start_task_from_definition(
            owned_session,
            request,
            data_dir=task_data_dir,
            runtime_effect_publisher=runtime_effect_publisher,
            support_projection_publisher=support_projection_publisher,
        )


async def _start_task_from_definition(
    session: AsyncSession,
    request: TaskStartRequest,
    *,
    data_dir: Path,
    runtime_effect_publisher: RuntimeEffectPublisher | None,
    support_projection_publisher: SupportProjectionPublisher | None,
) -> TaskStartResponse:
    task_id = _mint_task_id(request.task.key)
    task_root = data_dir / "tasks" / task_id
    try:
        try:
            staged_launch = await launch_task_runtime(
                session,
                RuntimeLaunchInput(
                    task_id=task_id,
                    task_root=task_root,
                    task_compose=request,
                    compiler_version="definition-start",
                ),
            )
        except ValueError as exc:
            raise _translate_task_start_error(exc) from exc
        response = _task_start_response(task_id)
        await session.commit()
    except BaseException:
        await session.rollback()
        raise

    _publish_task_start_follow_on(
        task_id=task_id,
        staged_launch=staged_launch,
        runtime_effect_publisher=runtime_effect_publisher,
        support_projection_publisher=support_projection_publisher,
    )
    return response


def _task_start_response(task_id: str) -> TaskStartResponse:
    return TaskStartResponse(
        task_id=task_id,
        compiled_plan_id=compiled_plan_id_for_task(task_id),
        active_flow_revision_id=flow_revision_id(flow_id_for_task(task_id), 1),
        flow_status=FlowStatus.RUNNING,
        workflow_manifest_ref=WorkflowManifestRef(
            path=Path("_runtime/workflow-manifest.md"),
            description=WORKFLOW_MANIFEST_REF_DESCRIPTION,
        ),
    )


def _publish_task_start_follow_on(
    *,
    task_id: str,
    staged_launch: StagedRuntimeLaunch,
    runtime_effect_publisher: RuntimeEffectPublisher | None,
    support_projection_publisher: SupportProjectionPublisher | None,
) -> None:
    if runtime_effect_publisher is not None:
        runtime_signal = FlowStartCommitted(flow_id_for_task(task_id))
        try:
            runtime_effect_publisher.publish(runtime_signal)
        except Exception:
            logger.exception(
                "failed to publish committed task-start runtime hint",
                extra={"flow_id": runtime_signal.flow_id},
            )
    if support_projection_publisher is None:
        return
    for projection_signal in staged_launch.support_projection_signals:
        try:
            support_projection_publisher.publish(projection_signal)
        except Exception:
            logger.exception(
                "failed to publish committed task-start support-projection hint",
                extra={"support_projection_signal": type(projection_signal).__name__},
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
        "host path does not exist" in summary
        or "does not match compiled plan workflow key" in summary
    ):
        return _task_start_invalid_error(summary)
    return exc


__all__ = ["start_task_from_definition"]
