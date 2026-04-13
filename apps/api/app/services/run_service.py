from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import (
    ApprovalStatus,
    AttemptStatus,
    CheckpointStatus,
    FlowNodeState,
    FlowStatus,
    RunStatus,
    TaskStatus,
)
from app.core.errors import ConflictError, NotFoundError
from app.db.models.runtime import (
    Approval,
    Attempt,
    CompiledPlan,
    Flow,
    FlowNode,
    NodeCheckpoint,
    Run,
    Task,
)
from app.schemas.runtime import (
    ApprovalCreate,
    ApprovalResolve,
    AttemptCreate,
    CheckpointWrite,
    FlowCreate,
    FlowNodeCreate,
    RunCreate,
    RunStartFromWorkflowCreate,
    TaskCreate,
)
from app.services.compiler_service import compile_published_workflow


async def create_task(session: AsyncSession, payload: TaskCreate) -> Task:
    task = Task(
        title=payload.title,
        description=payload.description,
        input_payload=payload.input_payload,
        status=TaskStatus.PENDING,
    )
    session.add(task)
    await session.flush()
    return task


async def create_run(session: AsyncSession, payload: RunCreate) -> Run:
    run = Run(
        task_id=payload.task_id,
        workflow_version_id=payload.workflow_version_id,
        compiled_plan_id=payload.compiled_plan_id,
        status=RunStatus.PENDING,
        current_attempt_number=0,
    )
    session.add(run)
    await session.flush()
    return run


async def create_attempt(session: AsyncSession, payload: AttemptCreate) -> Attempt:
    attempt = Attempt(
        run_id=payload.run_id,
        number=payload.number,
        retry_of_attempt_id=payload.retry_of_attempt_id,
        status=AttemptStatus.PENDING,
    )
    session.add(attempt)
    await session.flush()
    return attempt


async def create_flow(session: AsyncSession, payload: FlowCreate) -> Flow:
    flow = Flow(
        attempt_id=payload.attempt_id,
        compiled_plan_id=payload.compiled_plan_id,
        status=FlowStatus.PENDING,
    )
    session.add(flow)
    await session.flush()
    return flow


async def create_flow_node(session: AsyncSession, payload: FlowNodeCreate) -> FlowNode:
    flow_node = FlowNode(
        flow_id=payload.flow_id,
        compiled_plan_node_id=payload.compiled_plan_node_id,
        parent_flow_node_id=payload.parent_flow_node_id,
        node_key=payload.node_key,
        state=FlowNodeState.READY,
        iteration_index=payload.iteration_index,
        status_payload=payload.status_payload,
    )
    session.add(flow_node)
    await session.flush()
    return flow_node


async def create_flow_nodes_for_compiled_plan(
    session: AsyncSession,
    *,
    flow: Flow,
    compiled_plan: CompiledPlan,
) -> list[FlowNode]:
    node_by_key: dict[str, FlowNode] = {}
    flow_nodes: list[FlowNode] = []

    for compiled_node in compiled_plan.nodes:
        parent_flow_node_id = None
        if compiled_node.parent_node_key is not None:
            parent = node_by_key.get(compiled_node.parent_node_key)
            parent_flow_node_id = parent.id if parent is not None else None

        flow_node = await create_flow_node(
            session,
            FlowNodeCreate(
                flow_id=flow.id,
                compiled_plan_node_id=compiled_node.id,
                parent_flow_node_id=parent_flow_node_id,
                node_key=compiled_node.node_key,
                iteration_index=compiled_node.order_index,
                status_payload={"mode": compiled_node.mode.value},
            ),
        )
        node_by_key[compiled_node.node_key] = flow_node
        flow_nodes.append(flow_node)

    return flow_nodes


async def _get_flow_node_with_context(session: AsyncSession, flow_node_id: UUID) -> FlowNode | None:
    stmt = (
        select(FlowNode)
        .options(
            selectinload(FlowNode.flow)
            .selectinload(Flow.attempt)
            .selectinload(Attempt.run)
            .selectinload(Run.task),
            selectinload(FlowNode.flow).selectinload(Flow.nodes),
        )
        .where(FlowNode.id == flow_node_id)
    )
    return cast(FlowNode | None, await session.scalar(stmt))


def _require_current_execution_chain(run: Run) -> tuple[Attempt, Flow]:
    if not run.attempts:
        raise ConflictError(f"Run has no attempts: {run.id}")

    attempt = run.attempts[-1]
    if not attempt.flows:
        raise ConflictError(f"Run has no flows: {run.id}")

    return attempt, attempt.flows[-1]


def _set_chain_status(
    *,
    run: Run,
    attempt: Attempt,
    flow: Flow,
    task_status: TaskStatus,
    run_status: RunStatus,
    attempt_status: AttemptStatus,
    flow_status: FlowStatus,
) -> None:
    run.task.status = task_status
    run.status = run_status
    attempt.status = attempt_status
    flow.status = flow_status


def _mark_blocked(run: Run, attempt: Attempt, flow: Flow) -> None:
    _set_chain_status(
        run=run,
        attempt=attempt,
        flow=flow,
        task_status=TaskStatus.BLOCKED,
        run_status=RunStatus.BLOCKED,
        attempt_status=AttemptStatus.BLOCKED,
        flow_status=FlowStatus.BLOCKED,
    )


def _mark_running(run: Run, attempt: Attempt, flow: Flow) -> None:
    _set_chain_status(
        run=run,
        attempt=attempt,
        flow=flow,
        task_status=TaskStatus.RUNNING,
        run_status=RunStatus.RUNNING,
        attempt_status=AttemptStatus.RUNNING,
        flow_status=FlowStatus.RUNNING,
    )


def _mark_failed(run: Run, attempt: Attempt, flow: Flow) -> None:
    _set_chain_status(
        run=run,
        attempt=attempt,
        flow=flow,
        task_status=TaskStatus.FAILED,
        run_status=RunStatus.FAILED,
        attempt_status=AttemptStatus.FAILED,
        flow_status=FlowStatus.FAILED,
    )


def _mark_succeeded(run: Run, attempt: Attempt, flow: Flow) -> None:
    _set_chain_status(
        run=run,
        attempt=attempt,
        flow=flow,
        task_status=TaskStatus.SUCCEEDED,
        run_status=RunStatus.SUCCEEDED,
        attempt_status=AttemptStatus.SUCCEEDED,
        flow_status=FlowStatus.SUCCEEDED,
    )


def _mark_cancelled(run: Run, attempt: Attempt, flow: Flow) -> None:
    _set_chain_status(
        run=run,
        attempt=attempt,
        flow=flow,
        task_status=TaskStatus.CANCELLED,
        run_status=RunStatus.CANCELLED,
        attempt_status=AttemptStatus.CANCELLED,
        flow_status=FlowStatus.CANCELLED,
    )


def _pause_open_nodes(flow: Flow) -> None:
    for flow_node in flow.nodes:
        if flow_node.state in {
            FlowNodeState.READY,
            FlowNodeState.RUNNING,
            FlowNodeState.WAITING,
        }:
            flow_node.state = FlowNodeState.PAUSED


def _flow_node_ids(flow: Flow) -> set[UUID]:
    return {flow_node.id for flow_node in flow.nodes}


def _relevant_approvals(run: Run, flow: Flow) -> list[Approval]:
    flow_node_ids = _flow_node_ids(flow)
    return [
        approval
        for approval in run.approvals
        if approval.flow_node_id is None or approval.flow_node_id in flow_node_ids
    ]


async def record_checkpoint(session: AsyncSession, payload: CheckpointWrite) -> NodeCheckpoint:
    flow_node = await _get_flow_node_with_context(session, payload.flow_node_id)
    if flow_node is None:
        raise NotFoundError(f"No flow node found: {payload.flow_node_id}")
    if flow_node.flow_id != payload.flow_id:
        raise ConflictError("flow_id does not match flow_node_id")

    flow = flow_node.flow
    attempt = flow.attempt
    run = attempt.run

    checkpoint = NodeCheckpoint(
        flow_id=payload.flow_id,
        flow_node_id=payload.flow_node_id,
        sequence_no=payload.sequence_no,
        status=payload.status,
        summary=payload.summary,
        payload=payload.payload,
        failure_signature=payload.failure_signature,
        recommended_next_action=payload.recommended_next_action,
    )
    session.add(checkpoint)

    if payload.status == CheckpointStatus.GREEN:
        flow_node.state = FlowNodeState.DONE
        if all(node.state == FlowNodeState.DONE for node in flow.nodes):
            _mark_succeeded(run, attempt, flow)
        else:
            _mark_running(run, attempt, flow)
    elif payload.status == CheckpointStatus.RETRY:
        flow_node.state = FlowNodeState.READY
        _mark_running(run, attempt, flow)
    else:
        flow_node.state = FlowNodeState.WAITING
        _mark_blocked(run, attempt, flow)

    await session.flush()
    return checkpoint


async def create_approval(session: AsyncSession, payload: ApprovalCreate) -> Approval:
    run = await get_run_with_relations(session, payload.run_id)
    if run is None:
        raise NotFoundError(f"No run found: {payload.run_id}")

    attempt, flow = _require_current_execution_chain(run)

    if payload.attempt_id is not None and payload.attempt_id != attempt.id:
        raise ConflictError("attempt_id does not match the current run attempt")

    flow_node_id = payload.flow_node_id
    if flow_node_id is not None:
        flow_node = next((node for node in flow.nodes if node.id == flow_node_id), None)
        if flow_node is None:
            raise ConflictError("flow_node_id does not belong to the current flow")
        flow_node.state = FlowNodeState.WAITING

    approval = Approval(
        run_id=payload.run_id,
        attempt_id=payload.attempt_id or attempt.id,
        flow_node_id=flow_node_id,
        reason=payload.reason,
        request_payload=payload.request_payload,
    )
    session.add(approval)

    _mark_blocked(run, attempt, flow)

    await session.flush()
    return approval


async def get_approval(session: AsyncSession, approval_id: UUID) -> Approval | None:
    stmt = (
        select(Approval)
        .options(
            selectinload(Approval.run).selectinload(Run.task),
            selectinload(Approval.run)
            .selectinload(Run.attempts)
            .selectinload(Attempt.flows)
            .selectinload(Flow.nodes),
            selectinload(Approval.flow_node),
        )
        .where(Approval.id == approval_id)
    )
    return cast(Approval | None, await session.scalar(stmt))


async def resolve_approval(
    session: AsyncSession,
    approval_id: UUID,
    payload: ApprovalResolve,
) -> Approval:
    approval = await get_approval(session, approval_id)
    if approval is None:
        raise NotFoundError(f"No approval found: {approval_id}")

    approval.status = payload.status
    approval.resolution_payload = payload.resolution_payload

    if payload.status in {ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED}:
        attempt, flow = _require_current_execution_chain(approval.run)
        if approval.flow_node is not None:
            approval.flow_node.state = FlowNodeState.FAILED
        _mark_failed(approval.run, attempt, flow)

    await session.flush()
    return approval


async def start_run_from_workflow(
    session: AsyncSession,
    *,
    workflow_key: str,
    payload: RunStartFromWorkflowCreate,
) -> tuple[Task, Run, Attempt, Flow, list[FlowNode]]:
    compiled_plan = await compile_published_workflow(session, workflow_key)

    task = await create_task(session, payload.task)
    run = await create_run(
        session,
        RunCreate(
            task_id=task.id,
            workflow_version_id=compiled_plan.workflow_version_id,
            compiled_plan_id=compiled_plan.id,
        ),
    )

    attempt_number = payload.attempt_number or 1
    attempt = await create_attempt(
        session,
        AttemptCreate(run_id=run.id, number=attempt_number, retry_of_attempt_id=None),
    )
    run.current_attempt_number = attempt_number

    flow = await create_flow(
        session,
        FlowCreate(
            attempt_id=attempt.id,
            compiled_plan_id=compiled_plan.id,
        ),
    )

    flow_nodes = await create_flow_nodes_for_compiled_plan(
        session,
        flow=flow,
        compiled_plan=compiled_plan,
    )
    _mark_running(run, attempt, flow)
    return task, run, attempt, flow, flow_nodes


async def get_run_with_relations(session: AsyncSession, run_id: UUID) -> Run | None:
    stmt = (
        select(Run)
        .options(
            selectinload(Run.task),
            selectinload(Run.attempts).selectinload(Attempt.flows).selectinload(Flow.nodes),
            selectinload(Run.approvals),
        )
        .where(Run.id == run_id)
    )
    return cast(Run | None, await session.scalar(stmt))


async def continue_run(session: AsyncSession, run_id: UUID) -> Run:
    run = await get_run_with_relations(session, run_id)
    if run is None:
        raise NotFoundError(f"No run found: {run_id}")
    if run.status in {RunStatus.CANCELLED, RunStatus.FAILED, RunStatus.SUCCEEDED}:
        raise ConflictError(f"Run is already terminal: {run.status.value}")

    attempt, flow = _require_current_execution_chain(run)
    approvals = _relevant_approvals(run, flow)

    pending_approvals = [a for a in approvals if a.status == ApprovalStatus.PENDING]
    if pending_approvals:
        for approval in pending_approvals:
            if approval.flow_node_id is not None:
                flow_node = next(
                    (node for node in flow.nodes if node.id == approval.flow_node_id), None
                )
                if flow_node is not None:
                    flow_node.state = FlowNodeState.WAITING
        _mark_blocked(run, attempt, flow)
        raise ConflictError("Run is waiting on pending approvals")

    rejected_approvals = [
        approval
        for approval in approvals
        if approval.status in {ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED}
    ]
    if rejected_approvals:
        for approval in rejected_approvals:
            if approval.flow_node_id is not None:
                flow_node = next(
                    (node for node in flow.nodes if node.id == approval.flow_node_id), None
                )
                if flow_node is not None:
                    flow_node.state = FlowNodeState.FAILED
        _mark_failed(run, attempt, flow)
        await session.flush()
        return run

    approved_node_ids = {
        approval.flow_node_id
        for approval in approvals
        if approval.status in {ApprovalStatus.APPROVED, ApprovalStatus.NOT_REQUIRED}
        and approval.flow_node_id is not None
    }
    for flow_node in flow.nodes:
        if flow_node.id in approved_node_ids and flow_node.state == FlowNodeState.WAITING:
            flow_node.state = FlowNodeState.READY

    if all(flow_node.state == FlowNodeState.DONE for flow_node in flow.nodes):
        _mark_succeeded(run, attempt, flow)
        await session.flush()
        return run

    running_node = next((node for node in flow.nodes if node.state == FlowNodeState.RUNNING), None)
    if running_node is None:
        ready_node = next((node for node in flow.nodes if node.state == FlowNodeState.READY), None)
        if ready_node is None:
            raise ConflictError("Run has no runnable nodes")
        ready_node.state = FlowNodeState.RUNNING

    _mark_running(run, attempt, flow)
    await session.flush()
    return run


async def cancel_run(session: AsyncSession, run_id: UUID) -> Run:
    run = await get_run_with_relations(session, run_id)
    if run is None:
        raise NotFoundError(f"No run found: {run_id}")
    if run.status == RunStatus.CANCELLED:
        return run
    if run.status in {RunStatus.FAILED, RunStatus.SUCCEEDED}:
        raise ConflictError(f"Run is already terminal: {run.status.value}")

    attempt, flow = _require_current_execution_chain(run)
    _pause_open_nodes(flow)
    _mark_cancelled(run, attempt, flow)
    await session.flush()
    return run


async def list_run_checkpoints(session: AsyncSession, run_id: UUID) -> list[NodeCheckpoint]:
    result = await session.scalars(
        select(NodeCheckpoint)
        .join(Flow, NodeCheckpoint.flow_id == Flow.id)
        .join(Attempt, Flow.attempt_id == Attempt.id)
        .where(Attempt.run_id == run_id)
        .order_by(NodeCheckpoint.sequence_no.asc(), NodeCheckpoint.created_at.asc())
    )
    return list(result.all())


__all__ = [
    "cancel_run",
    "continue_run",
    "create_approval",
    "create_attempt",
    "create_flow",
    "create_flow_node",
    "create_flow_nodes_for_compiled_plan",
    "create_run",
    "create_task",
    "get_approval",
    "get_run_with_relations",
    "list_run_checkpoints",
    "record_checkpoint",
    "resolve_approval",
    "start_run_from_workflow",
]
