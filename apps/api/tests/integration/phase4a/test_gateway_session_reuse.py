from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from app.db import DispatchTurnModel
from app.runtime.control.dispatch.gateway import resolve_gateway_session_key
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase2.bootstrap.support import phase2_runtime_context
from tests.integration.phase4a.dispatch_gateway_support import load_latest_dispatch_snapshot


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_skips_parent_dispatch_outside_assignment_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_phase4a_gateway_assignment_lineage_guard"

    async with phase2_runtime_context(tmp_path) as runtime:
        async with runtime.session_factory() as session:
            await launch_seeded_runtime(
                session,
                task_id=task_id,
                task_root=runtime.paths.task_root,
                task_compose=task_compose_payload("minimal-implement-change"),
                compiler_version="phase-4a-assignment-lineage-guard",
            )
            snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
            original_dispatch = snapshot.dispatch
            assert original_dispatch.gateway_session_key is not None
            assert original_dispatch.assignment_id is not None
            assert original_dispatch.assignment_key is not None
            original_assignment_key = original_dispatch.assignment_key
            original_dispatch.assignment_key = f"{original_assignment_key}.stale"
            original_dispatch.fenced_at = original_dispatch.rendered_at

            resumed_dispatch = DispatchTurnModel(
                dispatch_id=f"{original_dispatch.dispatch_id}.resume",
                flow_id=original_dispatch.flow_id,
                flow_revision_id=original_dispatch.flow_revision_id,
                flow_node_id=original_dispatch.flow_node_id,
                task_id=original_dispatch.task_id,
                node_key=original_dispatch.node_key,
                assignment_id=original_dispatch.assignment_id,
                assignment_key=original_assignment_key,
                attempt_id=original_dispatch.attempt_id,
                prompt_name=original_dispatch.prompt_name,
                delivery_status="prepared",
                control_state="launching",
                prompt_path="",
                content_hash="",
                previous_dispatch_id=original_dispatch.dispatch_id,
                relevant_checkpoint_attempt_id=original_dispatch.relevant_checkpoint_attempt_id,
                rendered_at=original_dispatch.rendered_at + timedelta(seconds=1),
                opened_at=original_dispatch.opened_at + timedelta(seconds=1),
            )
            session.add(resumed_dispatch)
            await session.flush()

            monkeypatch.setattr(
                "app.runtime.control.dispatch.gateway.mint_gateway_session_key",
                lambda dispatch_id: f"minted:{dispatch_id}",
            )
            resolved_session_key = await resolve_gateway_session_key(
                session,
                dispatch=resumed_dispatch,
            )

    assert resolved_session_key == f"minted:{resumed_dispatch.dispatch_id}"
