from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from app.db import DispatchContinuityStateModel, DispatchTurnModel, NodeSessionModel
from app.db.session import dispose_db_engine
from app.runtime.contract_models.prompt import PromptFamily
from app.runtime.control.dispatch.gateway import resolve_gateway_session_key
from app.runtime.control.failures import RuntimeOperationError
from tests.helpers.runtime_seed import launch_seeded_runtime, task_compose_payload
from tests.integration.phase2.bootstrap.support import phase2_runtime_context
from tests.integration.phase4a.dispatch_gateway_support import load_latest_dispatch_snapshot


def build_resumed_dispatch(
    original_dispatch: DispatchTurnModel,
    *,
    suffix: str = "resume",
    offset_seconds: int = 1,
) -> DispatchTurnModel:
    return DispatchTurnModel(
        dispatch_id=f"{original_dispatch.dispatch_id}.{suffix}",
        flow_id=original_dispatch.flow_id,
        flow_revision_id=original_dispatch.flow_revision_id,
        flow_node_id=original_dispatch.flow_node_id,
        task_id=original_dispatch.task_id,
        node_key=original_dispatch.node_key,
        assignment_id=original_dispatch.assignment_id,
        assignment_key=original_dispatch.assignment_key,
        attempt_id=original_dispatch.attempt_id,
        prompt_name=original_dispatch.prompt_name,
        delivery_status="prepared",
        control_state="launching",
        prompt_path="",
        content_hash="",
        previous_dispatch_id=original_dispatch.dispatch_id,
        relevant_checkpoint_attempt_id=original_dispatch.relevant_checkpoint_attempt_id,
        rendered_at=original_dispatch.rendered_at + timedelta(seconds=offset_seconds),
        opened_at=original_dispatch.opened_at + timedelta(seconds=offset_seconds),
    )


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_skips_parent_dispatch_outside_assignment_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_phase4a_gateway_assignment_lineage_guard"
    try:
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
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                assert original_dispatch.gateway_session_key is not None
                assert original_dispatch.assignment_id is not None
                assert original_dispatch.assignment_key is not None
                original_assignment_key = original_dispatch.assignment_key
                original_dispatch.assignment_key = f"{original_assignment_key}.stale"
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at

                resumed_dispatch = build_resumed_dispatch(original_dispatch)
                resumed_dispatch.assignment_key = original_assignment_key
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "app.runtime.control.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: f"minted:{dispatch_id}",
                )
                resolved_session_key = await resolve_gateway_session_key(
                    session,
                    dispatch=resumed_dispatch,
                )

        assert resolved_session_key == f"minted:{resumed_dispatch.dispatch_id}"
    finally:
        await dispose_db_engine()


@pytest.mark.parametrize("invalid_basis", ["continuity", "node_session"])
@pytest.mark.asyncio
async def test_resolve_gateway_session_key_rejects_non_authoritative_parent_continuity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_basis: str,
) -> None:
    task_id = f"task_phase4a_gateway_invalid_parent_continuity_{invalid_basis}"
    try:
        async with phase2_runtime_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-4a-invalid-parent-continuity",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at
                if invalid_basis == "continuity":
                    continuity_state = await session.get(
                        DispatchContinuityStateModel,
                        original_dispatch.dispatch_id,
                    )
                    assert continuity_state is not None
                    continuity_state.invalidation_reason = (
                        "gateway_acceptance_persist_failed:RuntimeError"
                    )
                else:
                    node_session = await session.get(
                        NodeSessionModel,
                        f"node-session.{original_dispatch.dispatch_id}",
                    )
                    assert node_session is not None
                    await session.delete(node_session)

                resumed_dispatch = build_resumed_dispatch(original_dispatch)
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "app.runtime.control.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: pytest.fail(
                        f"unexpected fresh session mint for {dispatch_id}"
                    ),
                )
                with pytest.raises(
                    RuntimeOperationError,
                    match="parent/root same-attempt redispatch lost its continuity basis",
                ):
                    await resolve_gateway_session_key(
                        session,
                        dispatch=resumed_dispatch,
                    )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_rejects_missing_parent_continuity_basis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_phase4a_gateway_missing_parent_continuity_basis"
    try:
        async with phase2_runtime_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-4a-missing-parent-continuity-basis",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at
                continuity_state = await session.get(
                    DispatchContinuityStateModel,
                    original_dispatch.dispatch_id,
                )
                assert continuity_state is not None
                await session.delete(continuity_state)

                resumed_dispatch = build_resumed_dispatch(original_dispatch)
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "app.runtime.control.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: pytest.fail(
                        f"unexpected fresh session mint for {dispatch_id}"
                    ),
                )
                with pytest.raises(
                    RuntimeOperationError,
                    match="parent/root same-attempt redispatch lost its continuity basis",
                ):
                    await resolve_gateway_session_key(
                        session,
                        dispatch=resumed_dispatch,
                    )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_rejects_when_newest_parent_continuity_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_phase4a_gateway_invalid_parent_continuity_chain"
    try:
        async with phase2_runtime_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-4a-invalid-parent-continuity-chain",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at

                middle_dispatch = build_resumed_dispatch(original_dispatch)
                middle_dispatch.gateway_session_key = original_dispatch.gateway_session_key
                middle_dispatch.fenced_at = middle_dispatch.rendered_at
                middle_dispatch.closed_at = middle_dispatch.rendered_at
                session.add(middle_dispatch)
                await session.flush()

                middle_continuity = DispatchContinuityStateModel(
                    dispatch_id=middle_dispatch.dispatch_id,
                    task_id=middle_dispatch.task_id or task_id,
                    attempt_id=middle_dispatch.attempt_id or "",
                    assignment_key=middle_dispatch.assignment_key,
                    node_key=middle_dispatch.node_key,
                    session_key_present=True,
                    invalidation_reason="gateway_acceptance_persist_failed:RuntimeError",
                )
                session.add(middle_continuity)
                await session.flush()

                resumed_dispatch = build_resumed_dispatch(middle_dispatch)
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "app.runtime.control.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: pytest.fail(
                        f"unexpected fresh session mint for {dispatch_id}"
                    ),
                )
                with pytest.raises(
                    RuntimeOperationError,
                    match="parent/root same-attempt redispatch lost its continuity basis",
                ):
                    await resolve_gateway_session_key(
                        session,
                        dispatch=resumed_dispatch,
                    )
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_reuses_latest_lawful_parent_continuity_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_phase4a_gateway_latest_lawful_parent_continuity"
    try:
        async with phase2_runtime_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-4a-latest-lawful-parent-continuity",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                assert original_dispatch.gateway_session_key is not None
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at

                invalid_dispatch = build_resumed_dispatch(
                    original_dispatch,
                    suffix="invalid",
                    offset_seconds=1,
                )
                invalid_dispatch.gateway_session_key = original_dispatch.gateway_session_key
                invalid_dispatch.fenced_at = invalid_dispatch.rendered_at
                invalid_dispatch.closed_at = invalid_dispatch.rendered_at
                session.add(invalid_dispatch)
                session.add(
                    DispatchContinuityStateModel(
                        dispatch_id=invalid_dispatch.dispatch_id,
                        task_id=invalid_dispatch.task_id or task_id,
                        attempt_id=invalid_dispatch.attempt_id or "",
                        assignment_key=invalid_dispatch.assignment_key,
                        node_key=invalid_dispatch.node_key,
                        session_key_present=True,
                        invalidation_reason="gateway_acceptance_persist_failed:RuntimeError",
                    )
                )
                await session.flush()

                lawful_dispatch = build_resumed_dispatch(
                    invalid_dispatch,
                    suffix="lawful",
                    offset_seconds=1,
                )
                lawful_dispatch.gateway_session_key = original_dispatch.gateway_session_key
                lawful_dispatch.fenced_at = lawful_dispatch.rendered_at
                lawful_dispatch.closed_at = lawful_dispatch.rendered_at
                session.add(lawful_dispatch)
                session.add(
                    DispatchContinuityStateModel(
                        dispatch_id=lawful_dispatch.dispatch_id,
                        task_id=lawful_dispatch.task_id or task_id,
                        attempt_id=lawful_dispatch.attempt_id or "",
                        assignment_key=lawful_dispatch.assignment_key,
                        node_key=lawful_dispatch.node_key,
                        session_key_present=True,
                        invalidation_reason=None,
                    )
                )
                session.add(
                    NodeSessionModel(
                        node_session_id=f"node-session.{lawful_dispatch.dispatch_id}",
                        flow_node_id=lawful_dispatch.flow_node_id,
                        assignment_id=lawful_dispatch.assignment_id,
                        attempt_id=lawful_dispatch.attempt_id,
                        dispatch_id=lawful_dispatch.dispatch_id,
                        session_key=lawful_dispatch.gateway_session_key,
                        session_status="fenced",
                        opened_at=lawful_dispatch.opened_at,
                        closed_at=lawful_dispatch.fenced_at,
                    )
                )
                await session.flush()

                resumed_dispatch = build_resumed_dispatch(
                    lawful_dispatch,
                    suffix="reopened",
                    offset_seconds=1,
                )
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "app.runtime.control.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: pytest.fail(
                        f"unexpected fresh session mint for {dispatch_id}"
                    ),
                )
                resolved_session_key = await resolve_gateway_session_key(
                    session,
                    dispatch=resumed_dispatch,
                )

        assert resolved_session_key == original_dispatch.gateway_session_key
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_keeps_worker_dispatches_on_fresh_session_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_phase4a_worker_dispatch_fresh_session"
    try:
        async with phase2_runtime_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="phase-4a-worker-dispatch-fresh-session",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                original_dispatch.prompt_name = PromptFamily.WORKER_DISPATCH.value
                original_dispatch.fenced_at = original_dispatch.rendered_at

                resumed_dispatch = build_resumed_dispatch(
                    original_dispatch,
                    suffix="worker-retry",
                    offset_seconds=1,
                )
                resumed_dispatch.prompt_name = PromptFamily.WORKER_DISPATCH.value
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "app.runtime.control.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: f"minted:{dispatch_id}",
                )
                resolved_session_key = await resolve_gateway_session_key(
                    session,
                    dispatch=resumed_dispatch,
                )

        assert resolved_session_key == f"minted:{resumed_dispatch.dispatch_id}"
    finally:
        await dispose_db_engine()
