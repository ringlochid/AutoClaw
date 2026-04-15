from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApprovalStatus, CheckpointStatus
from app.core.errors import ConflictError
from app.db.models.runtime import NodeAttempt
from app.runtime.approvals import create_approval
from app.runtime.checkpoints import record_checkpoint
from app.runtime.runner import continue_flow, get_flow_with_relations, start_flow_from_workflow
from app.schemas.runtime import (
    ApprovalCreate,
    CheckpointWrite,
    FlowStartFromWorkflowCreate,
    TaskCreate,
)
from app.services.registry_service import bootstrap_registry


async def test_flow_runtime_round_trip_with_real_postgres_session(
    db_session: AsyncSession,
) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()

    flow, revision, _flow_nodes = await start_flow_from_workflow(
        db_session,
        workflow_key="default-bugfix",
        payload=FlowStartFromWorkflowCreate(
            task=TaskCreate(
                title="Flow round-trip test",
                description="Round-trip test",
                input_payload={},
            )
        ),
    )
    assert flow.id is not None
    assert revision.id is not None
    flow_id = flow.id

    await continue_flow(db_session, flow_id)
    fresh_flow = await get_flow_with_relations(db_session, flow_id)
    assert fresh_flow is not None
    assert fresh_flow.active_flow_revision is not None

    flow_node = fresh_flow.active_flow_revision.nodes[0]
    attempt = await db_session.scalar(
        select(NodeAttempt)
        .where(NodeAttempt.flow_node_id == flow_node.id)
        .order_by(NodeAttempt.number.desc())
        .limit(1)
    )
    assert attempt is not None

    with pytest.raises(ConflictError):
        await record_checkpoint(
            db_session,
            CheckpointWrite(
                flow_id=flow_id,
                flow_node_id=flow_node.id,
                node_attempt_id=attempt.id,
                sequence_no=1,
                status=CheckpointStatus.GREEN,
                summary="Task completed successfully",
                payload={"evidence": ["integration-test"]},
                recommended_next_action="continue",
            ),
        )

    approval = await create_approval(
        db_session,
        ApprovalCreate(
            flow_id=flow_id,
            flow_node_id=flow_node.id,
            reason="Need confirmation before sync",
            request_payload={"action": "sync"},
        ),
    )
    assert approval.status == ApprovalStatus.PENDING

    await db_session.commit()

    persisted_flow = await get_flow_with_relations(db_session, flow_id)
    assert persisted_flow is not None
    assert persisted_flow.id == flow_id
    assert any(
        pending_approval.status == ApprovalStatus.PENDING
        for pending_approval in persisted_flow.approvals
    )
