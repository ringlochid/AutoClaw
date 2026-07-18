from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from autoclaw.persistence.models import CommandRunModel, FlowWaitModel, HumanRequestModel
from autoclaw.runtime.clock import utc_now
from autoclaw.runtime.contracts import (
    CommandRunStartResponse,
    CommandRunState,
    HumanRequestOpenResponse,
)
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime.dispatch.authority import NodeOperationAuthority
from autoclaw.runtime.errors import RuntimeOperationError
from autoclaw.runtime.node_operations.contracts import (
    OpenHumanRequestRequest,
    StartCommandRunRequest,
)
from autoclaw.runtime.node_operations.source_transitions import close_source_dispatch
from autoclaw.runtime.task_root.logical_paths import normalize_logical_task_path


async def open_human_request(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    request: OpenHumanRequestRequest,
) -> HumanRequestOpenResponse:
    request_id = f"human-request.{authority.task_id}.{uuid4().hex}"
    body = request.request
    context_refs = [
        {
            "path": normalize_logical_task_path(context_ref.path),
            "description": context_ref.description,
        }
        for context_ref in body.context_refs
    ]
    now = utc_now()
    await close_source_dispatch(
        session,
        authority,
        now=now,
        closed_reason="human_request_wait",
        waiting_cause="human_request",
        waiting_source_id=request_id,
    )
    session.add(
        HumanRequestModel(
            request_id=request_id,
            task_id=authority.task_id,
            flow_id=authority.flow_id,
            assignment_id=authority.assignment_id,
            attempt_id=authority.attempt_id,
            source_dispatch_id=authority.dispatch_id,
            request_kind=body.kind.value,
            request_summary=body.summary,
            request_items_json=[item.model_dump(mode="json") for item in body.items],
            context_refs_json=context_refs or None,
            suggested_human_instruction=body.suggested_human_instruction,
            capability_basis_json={"decision": "allow", "kind": body.kind.value},
            due_at=body.timeout.due_at,
            timeout_policy_json=({"kind": "deadline"} if body.timeout.due_at is not None else None),
            default_behavior_json=(
                {"value": body.timeout.default_behavior}
                if body.timeout.default_behavior is not None
                else None
            ),
            status="open",
        )
    )
    session.add(
        FlowWaitModel(
            flow_id=authority.flow_id,
            task_id=authority.task_id,
            source_dispatch_id=authority.dispatch_id,
            human_request_id=request_id,
            command_run_id=None,
        )
    )
    await session.commit()
    return HumanRequestOpenResponse(request_id=request_id, task_id=authority.task_id)


async def start_command_run(
    session: AsyncSession,
    authority: NodeOperationAuthority,
    request: StartCommandRunRequest,
) -> CommandRunStartResponse:
    run_id = f"command-run.{authority.task_id}.{uuid4().hex}"
    body = request.request
    now = utc_now()
    due_at = now + timedelta(seconds=body.timeout_seconds) if body.timeout_seconds else None
    cwd = _normalize_command_cwd(body.cwd)
    expected_outputs = [
        {
            "path": normalize_logical_task_path(output.path),
            "description": output.description,
        }
        for output in body.expected_outputs
    ]
    await close_source_dispatch(
        session,
        authority,
        now=now,
        closed_reason="command_run_wait",
        waiting_cause="command_run",
        waiting_source_id=run_id,
    )
    session.add(
        CommandRunModel(
            run_id=run_id,
            task_id=authority.task_id,
            flow_id=authority.flow_id,
            assignment_id=authority.assignment_id,
            attempt_id=authority.attempt_id,
            source_dispatch_id=authority.dispatch_id,
            command_spec_json=body.command.model_dump(mode="json"),
            cwd_policy_json={"logical_path": cwd} if cwd is not None else None,
            environment_refs_json=list(body.environment) or None,
            summary=body.summary,
            expected_outputs_json=expected_outputs or None,
            timeout_seconds=body.timeout_seconds,
            due_at=due_at,
            state=CommandRunState.PENDING_START,
            ownership_revision=0,
        )
    )
    session.add(
        FlowWaitModel(
            flow_id=authority.flow_id,
            task_id=authority.task_id,
            source_dispatch_id=authority.dispatch_id,
            human_request_id=None,
            command_run_id=run_id,
        )
    )
    await session.commit()
    return CommandRunStartResponse(
        run_id=run_id,
        task_id=authority.task_id,
        state=CommandRunState.PENDING_START,
    )


def _normalize_command_cwd(cwd: str | None) -> str | None:
    if cwd is None:
        return None
    normalized = normalize_logical_task_path(cwd)
    if normalized != "workspace" and not normalized.startswith("workspace/"):
        raise RuntimeOperationError(
            code=OperationFailureCode.INVALID_TASK_PATH,
            summary="command cwd must be inside the task workspace",
            is_retryable=False,
        )
    return normalized


__all__ = ["open_human_request", "start_command_run"]
