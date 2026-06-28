from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from autoclaw.persistence import (
    CommandRunModel,
    DispatchContinuityStateModel,
    DispatchTurnModel,
    NodeSessionModel,
    PendingHumanRequestModel,
)
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime import PromptFamily
from autoclaw.runtime.contracts import (
    CommandRunState,
    HumanRequestResolutionKind,
    HumanRequestResolutionSurface,
    HumanRequestStatus,
    TaskEventSource,
)
from autoclaw.runtime.dispatch.gateway import resolve_gateway_session_key
from tests.helpers.runtime_support import runtime_bootstrap_context
from tests.helpers.seeded_runtime_support import launch_seeded_runtime, task_compose_payload
from tests.integration.gateway.dispatch_gateway_support import load_latest_dispatch_snapshot

pytestmark = pytest.mark.requires_openclaw_gateway


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


def terminal_human_request_for_dispatch(
    dispatch: DispatchTurnModel,
) -> PendingHumanRequestModel:
    assert dispatch.task_id is not None
    assert dispatch.flow_id is not None
    assert dispatch.flow_revision_id is not None
    assert dispatch.flow_node_id is not None
    assert dispatch.assignment_id is not None
    assert dispatch.attempt_id is not None
    return PendingHumanRequestModel(
        request_id=f"human-request.{dispatch.dispatch_id}.0001",
        task_id=dispatch.task_id,
        flow_id=dispatch.flow_id,
        flow_revision_id=dispatch.flow_revision_id,
        flow_node_id=dispatch.flow_node_id,
        assignment_id=dispatch.assignment_id,
        attempt_id=dispatch.attempt_id,
        dispatch_id=dispatch.dispatch_id,
        requester_node_key=dispatch.node_key,
        kind="direction",
        title="Choose next step",
        summary="External wait continuation test.",
        items_json=[
            {
                "item_id": "next_step",
                "prompt": "Proceed?",
                "options": [{"id": "proceed", "title": "Proceed"}],
                "recommended_option": "proceed",
                "input_payload_schema": None,
            }
        ],
        timeout_json={"due_at": None, "default_behavior": None},
        suggested_human_instruction="Choose proceed.",
        status=HumanRequestStatus.RESOLVED.value,
        resolution_kind=HumanRequestResolutionKind.ANSWERED.value,
        item_responses_json=[
            {
                "item_id": "next_step",
                "selected_option": "proceed",
                "freeform_answer": None,
                "extra_notes": None,
                "response_payload": None,
            }
        ],
        resolved_at=dispatch.closed_at,
        resolved_by_actor_ref="test",
        resolved_by_surface=HumanRequestResolutionSurface.OPERATOR_MCP.value,
        resolution_policy_basis="test",
        opened_at=dispatch.rendered_at,
        updated_at=dispatch.closed_at or dispatch.rendered_at,
    )


def terminal_command_run_for_dispatch(dispatch: DispatchTurnModel) -> CommandRunModel:
    assert dispatch.task_id is not None
    assert dispatch.flow_id is not None
    assert dispatch.flow_revision_id is not None
    assert dispatch.flow_node_id is not None
    assert dispatch.assignment_id is not None
    assert dispatch.attempt_id is not None
    return CommandRunModel(
        run_id=f"command-run.{dispatch.dispatch_id}.0001",
        task_id=dispatch.task_id,
        flow_id=dispatch.flow_id,
        flow_revision_id=dispatch.flow_revision_id,
        flow_node_id=dispatch.flow_node_id,
        assignment_id=dispatch.assignment_id,
        attempt_id=dispatch.attempt_id,
        dispatch_id=dispatch.dispatch_id,
        requester_node_key=dispatch.node_key,
        command="bash -lc 'true'",
        description="External wait continuation test.",
        workdir=None,
        timeout_seconds=300,
        state=CommandRunState.SUCCEEDED.value,
        terminal_summary="Command succeeded.",
        terminal_exit_code=0,
        terminal_event_source=TaskEventSource.CONTROLLER.value,
        created_at=dispatch.rendered_at,
        started_at=dispatch.rendered_at,
        ended_at=dispatch.closed_at,
        updated_at=dispatch.closed_at or dispatch.rendered_at,
    )


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_skips_parent_dispatch_outside_assignment_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_gateway_assignment_lineage_guard"
    try:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="gateway-assignment-lineage-guard",
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
                original_dispatch.control_state = "fenced"
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at

                resumed_dispatch = build_resumed_dispatch(original_dispatch)
                resumed_dispatch.assignment_key = original_assignment_key
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "autoclaw.runtime.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: f"minted:{dispatch_id}",
                )
                resolved_session_key = await resolve_gateway_session_key(
                    session,
                    dispatch=resumed_dispatch,
                )

        assert resolved_session_key == f"minted:{resumed_dispatch.dispatch_id}"
    finally:
        await dispose_db_engine()


@pytest.mark.parametrize(
    "invalid_basis",
    [
        "unfenced_dispatch",
        "missing_node_session",
        "revoked_node_session",
        "superseded_node_session",
    ],
)
@pytest.mark.asyncio
async def test_resolve_gateway_session_key_falls_back_when_parent_continuity_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_basis: str,
) -> None:
    task_id = f"task_gateway_invalid_parent_continuity_{invalid_basis}"
    try:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="gateway-invalid-parent-continuity",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                original_dispatch.closed_at = original_dispatch.rendered_at
                if invalid_basis == "unfenced_dispatch":
                    original_dispatch.control_state = "live"
                else:
                    original_dispatch.control_state = "fenced"
                    original_dispatch.fenced_at = original_dispatch.rendered_at
                    node_session = await session.get(
                        NodeSessionModel,
                        f"node-session.{original_dispatch.dispatch_id}",
                    )
                    assert node_session is not None
                    if invalid_basis == "missing_node_session":
                        await session.delete(node_session)
                    else:
                        node_session.closed_at = original_dispatch.fenced_at
                        node_session.session_status = (
                            "revoked" if invalid_basis == "revoked_node_session" else "superseded"
                        )

                resumed_dispatch = build_resumed_dispatch(original_dispatch)
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "autoclaw.runtime.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: f"minted:{dispatch_id}",
                )
                resolved_session_key = await resolve_gateway_session_key(
                    session,
                    dispatch=resumed_dispatch,
                )
        assert resolved_session_key == f"minted:{resumed_dispatch.dispatch_id}"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_ignores_missing_continuity_row(
    # Continuity observability must not veto lawful session/dispatch reuse.
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_gateway_missing_continuity_row"
    try:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="gateway-missing-parent-continuity-basis",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                original_dispatch.control_state = "fenced"
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at
                node_session = await session.get(
                    NodeSessionModel,
                    f"node-session.{original_dispatch.dispatch_id}",
                )
                assert node_session is not None
                node_session.session_status = "fenced"
                node_session.closed_at = original_dispatch.fenced_at
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
                    "autoclaw.runtime.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: f"unexpected-fresh:{dispatch_id}",
                )
                resolved_session_key = await resolve_gateway_session_key(
                    session,
                    dispatch=resumed_dispatch,
                )
        assert resolved_session_key == original_dispatch.gateway_session_key
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_falls_back_when_newest_parent_continuity_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_gateway_invalid_parent_continuity_chain"
    try:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="gateway-invalid-parent-continuity-chain",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                original_dispatch.control_state = "fenced"
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at

                middle_dispatch = build_resumed_dispatch(original_dispatch)
                middle_dispatch.gateway_session_key = original_dispatch.gateway_session_key
                middle_dispatch.control_state = "fenced"
                middle_dispatch.fenced_at = middle_dispatch.rendered_at
                middle_dispatch.closed_at = middle_dispatch.rendered_at
                session.add(middle_dispatch)
                await session.flush()

                resumed_dispatch = build_resumed_dispatch(middle_dispatch)
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "autoclaw.runtime.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: f"minted:{dispatch_id}",
                )
                resolved_session_key = await resolve_gateway_session_key(
                    session,
                    dispatch=resumed_dispatch,
                )
        assert resolved_session_key == f"minted:{resumed_dispatch.dispatch_id}"
    finally:
        await dispose_db_engine()


@pytest.mark.asyncio
async def test_resolve_gateway_session_key_reuses_latest_lawful_parent_continuity_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = "task_gateway_latest_lawful_parent_continuity"
    try:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="gateway-latest-lawful-parent-continuity",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                assert original_dispatch.gateway_session_key is not None
                original_dispatch.control_state = "fenced"
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at

                invalid_dispatch = build_resumed_dispatch(
                    original_dispatch,
                    suffix="invalid",
                    offset_seconds=1,
                )
                invalid_dispatch.gateway_session_key = original_dispatch.gateway_session_key
                invalid_dispatch.control_state = "fenced"
                invalid_dispatch.fenced_at = invalid_dispatch.rendered_at
                invalid_dispatch.closed_at = invalid_dispatch.rendered_at
                session.add(invalid_dispatch)
                await session.flush()

                lawful_dispatch = build_resumed_dispatch(
                    invalid_dispatch,
                    suffix="lawful",
                    offset_seconds=1,
                )
                lawful_dispatch.gateway_session_key = original_dispatch.gateway_session_key
                lawful_dispatch.control_state = "fenced"
                lawful_dispatch.fenced_at = lawful_dispatch.rendered_at
                lawful_dispatch.closed_at = lawful_dispatch.rendered_at
                session.add(lawful_dispatch)
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
                    "autoclaw.runtime.dispatch.gateway.session.mint_gateway_session_key",
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
    task_id = "task_gateway_worker_dispatch_fresh_session"
    try:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="gateway-worker-dispatch-fresh-session",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                original_dispatch.prompt_name = PromptFamily.WORKER_DISPATCH.value
                original_dispatch.control_state = "fenced"
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
                    "autoclaw.runtime.dispatch.gateway.session.mint_gateway_session_key",
                    lambda dispatch_id: f"minted:{dispatch_id}",
                )
                resolved_session_key = await resolve_gateway_session_key(
                    session,
                    dispatch=resumed_dispatch,
                )

        assert resolved_session_key == f"minted:{resumed_dispatch.dispatch_id}"
    finally:
        await dispose_db_engine()


@pytest.mark.parametrize("external_wait_source", ["human_request", "command_run"])
@pytest.mark.asyncio
async def test_resolve_gateway_session_key_reuses_worker_session_after_external_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    external_wait_source: str,
) -> None:
    task_id = f"task_gateway_worker_external_wait_session_{external_wait_source}"
    try:
        async with runtime_bootstrap_context(tmp_path) as runtime:
            async with runtime.session_factory() as session:
                await launch_seeded_runtime(
                    session,
                    task_id=task_id,
                    task_root=runtime.paths.task_root,
                    task_compose=task_compose_payload("minimal-implement-change"),
                    compiler_version="gateway-worker-external-wait-session",
                )
                snapshot = await load_latest_dispatch_snapshot(session, task_id=task_id)
                original_dispatch = await session.get(
                    DispatchTurnModel,
                    snapshot.dispatch.dispatch_id,
                )
                assert original_dispatch is not None
                assert original_dispatch.gateway_session_key is not None
                original_dispatch.prompt_name = PromptFamily.WORKER_DISPATCH.value
                original_dispatch.control_state = "fenced"
                original_dispatch.fenced_at = original_dispatch.rendered_at
                original_dispatch.closed_at = original_dispatch.rendered_at
                node_session = await session.get(
                    NodeSessionModel,
                    f"node-session.{original_dispatch.dispatch_id}",
                )
                assert node_session is not None
                node_session.session_status = "fenced"
                node_session.closed_at = original_dispatch.fenced_at
                if external_wait_source == "human_request":
                    session.add(terminal_human_request_for_dispatch(original_dispatch))
                else:
                    session.add(terminal_command_run_for_dispatch(original_dispatch))

                resumed_dispatch = build_resumed_dispatch(
                    original_dispatch,
                    suffix=f"{external_wait_source}-resume",
                    offset_seconds=1,
                )
                resumed_dispatch.prompt_name = PromptFamily.WORKER_DISPATCH.value
                session.add(resumed_dispatch)
                await session.flush()

                monkeypatch.setattr(
                    "autoclaw.runtime.dispatch.gateway.session.mint_gateway_session_key",
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
