import asyncio
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app import config as config_module
from app.core.enums import (
    DefinitionVersionStatus,
    FlowNodeState,
    NodeAttemptStatus,
    NodeSessionStatus,
)
from app.db.models.registry import WorkflowDefinition, WorkflowVersion
from app.db.models.runtime import (
    Flow,
    FlowNode,
    NodeAttempt,
    NodeCheckpoint,
    NodeSession,
    TaskCompose,
)
from app.db.session import get_db_session
from app.integrations.openclaw import (
    OpenClawIntegrationError,
    OpenClawRequest,
    OpenClawResponse,
    OpenClawTimeoutError,
)
from app.main import app
from tests.helpers import internal_api_key_headers, operator_api_key_headers


def _set_db_override(test_engine: AsyncEngine) -> None:
    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session


def _find_node_state(nodes: Sequence[dict[str, Any]], flow_node_id: str) -> str | None:
    for node in nodes:
        if node["id"] == flow_node_id:
            return cast(str, node["state"])
    return None


def _find_node(nodes: Sequence[dict[str, Any]], flow_node_id: str) -> dict[str, Any] | None:
    for node in nodes:
        if node["id"] == flow_node_id:
            return node
    return None


def _with_extra_uuid_hyphen(value: str) -> str:
    compact = value.replace("-", "")
    return (
        f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-"
        f"{compact[16:20]}-{compact[20:24]}-{compact[24:]}"
    )


def _manifest_binding(manifest: dict[str, Any]) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "manifest_id": cast(str, manifest["id"]),
        "manifest_hash": cast(str, manifest["manifest_hash"]),
        "node_session_key": cast(str, manifest["node_session_key"]),
    }
    ack_checkpoint_id = manifest.get("ack_checkpoint_id")
    if ack_checkpoint_id is not None:
        binding["ack_checkpoint_id"] = cast(str, ack_checkpoint_id)
    return binding


async def _ack_manifest_via_api(
    client: AsyncClient,
    manifest: dict[str, Any],
    *,
    manifest_id: str | None = None,
):
    return await client.post(
        f"/internal/flows/context-manifests/{manifest_id or manifest['id']}/ack",
        json={
            "manifest_hash": manifest["manifest_hash"],
            "node_session_key": manifest["node_session_key"],
        },
    )


class _FakeOpenClawClient:
    def __init__(self, capture: dict[str, object]) -> None:
        self.capture = capture

    async def create_response(self, request: OpenClawRequest) -> OpenClawResponse:
        self.capture.update(
            {
                "session_key": request.session_key,
                "input": request.input,
                "instructions": request.instructions,
                "tools": request.tools,
                "tool_choice": request.tool_choice,
            }
        )
        return OpenClawResponse(
            response_id="resp_test",
            output_text="OK",
            raw={"id": "resp_test"},
        )


class _EventfulFakeOpenClawClient(_FakeOpenClawClient):
    def __init__(self, capture: dict[str, object], called: asyncio.Event) -> None:
        super().__init__(capture)
        self.called = called

    async def create_response(self, request: OpenClawRequest) -> OpenClawResponse:
        response = await super().create_response(request)
        self.called.set()
        return response


class _RaisingOpenClawClient:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def create_response(self, _request: OpenClawRequest) -> OpenClawResponse:
        raise self.exc


class _RaisingFakeOpenClawClient:
    async def create_response(self, request: OpenClawRequest) -> OpenClawResponse:
        del request
        raise OpenClawIntegrationError("simulated wake dispatch failure")


def _resourceful_workflow_content() -> dict[str, Any]:
    return {
        "id": "resourceful-workflow",
        "description": "workflow with explicit task resources",
        "task_defaults": {
            "workspace": {"mode": "ensure_task_primary"},
            "context": {
                "mode": "ensure_task_primary",
                "seed_from": ["task_input", "workspace_docs"],
            },
            "manifests": {"mode": "ensure_task_root"},
        },
        "nodes": [
            {
                "id": "root",
                "role": "planner-supervisor",
                "mode": "plan",
                "resources": {
                    "workspace": {
                        "mounts": [{"ref": "task.primary_workspace", "access": "read_only"}]
                    },
                    "context": {"refs": [{"ref": "task.primary_context"}]},
                },
            },
            {
                "id": "loop",
                "role": "main-loop-worker",
                "mode": "persistent_execute",
                "resources": {
                    "workspace": {
                        "mounts": [{"ref": "task.primary_workspace", "access": "read_write"}]
                    },
                    "context": {"refs": [{"ref": "task.primary_context"}]},
                },
            },
        ],
        "edges": [{"from": "root", "to": "loop"}],
    }


async def _insert_workflow_version(
    test_engine: AsyncEngine,
    *,
    key: str,
    content: dict[str, Any],
) -> None:
    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        definition = WorkflowDefinition(key=key, description=content.get("description"))
        session.add(definition)
        await session.flush()
        session.add(
            WorkflowVersion(
                workflow_definition_id=definition.id,
                version=1,
                status=DefinitionVersionStatus.PUBLISHED,
                description=content.get("description"),
                content=content,
                published_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        await session.commit()


async def _bootstrap_compile_start(client: AsyncClient) -> tuple[str, str, str, str]:
    bootstrap_response = await client.post("/internal/registry/bootstrap")
    assert bootstrap_response.status_code == 200
    bootstrap_payload = bootstrap_response.json()
    assert bootstrap_payload["workflows"] == 4

    compile_response = await client.post("/internal/workflows/default-bugfix/compile")
    assert compile_response.status_code == 201

    compile_payload = compile_response.json()
    compiled_plan_id = compile_payload["id"]
    assert len(compile_payload["nodes"]) == 4

    compiled_plan_read_response = await client.get(
        f"/internal/workflows/compiled-plans/{compiled_plan_id}"
    )
    assert compiled_plan_read_response.status_code == 200
    compiled_plan_read_payload = compiled_plan_read_response.json()
    assert compiled_plan_read_payload["id"] == compiled_plan_id
    assert len(compiled_plan_read_payload["edges"]) == 4

    start_response = await client.post(
        "/flows/from-workflow/default-bugfix",
        json={
            "task": {
                "title": "kernel api flow",
                "description": "phase three api flow",
                "input_payload": {"source": "test"},
            }
        },
    )
    assert start_response.status_code == 201
    start_payload = start_response.json()
    return (
        start_payload["flow_id"],
        start_payload["active_flow_revision_id"],
        start_payload["first_flow_node_id"],
        compiled_plan_id,
    )


async def _age_attempt_started_at(
    test_engine: AsyncEngine,
    node_attempt_id: str,
    *,
    minutes: int = 10,
) -> None:
    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        attempt = await session.get(NodeAttempt, UUID(node_attempt_id))
        assert attempt is not None
        attempt.started_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=minutes)
        await session.commit()


async def _age_latest_checkpoint_created_at(
    test_engine: AsyncEngine,
    node_attempt_id: str,
    *,
    minutes: int = 10,
) -> None:
    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        checkpoint = await session.scalar(
            select(NodeCheckpoint)
            .where(NodeCheckpoint.node_attempt_id == UUID(node_attempt_id))
            .order_by(NodeCheckpoint.sequence_no.desc())
            .limit(1)
        )
        assert checkpoint is not None
        checkpoint.created_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=minutes)
        await session.commit()


async def _read_flow_node_record(
    test_engine: AsyncEngine,
    flow_node_id: str,
) -> FlowNode:
    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        flow_node = await session.get(FlowNode, UUID(flow_node_id))
        assert flow_node is not None
        return flow_node


async def _seed_competing_running_attempt(
    test_engine: AsyncEngine,
    flow_id: str,
    excluded_flow_node_id: str,
) -> tuple[str, str]:
    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        flow = await session.get(Flow, UUID(flow_id))
        assert flow is not None
        assert flow.active_flow_revision_id is not None

        sibling_node = await session.scalar(
            select(FlowNode)
            .where(FlowNode.flow_id == flow.id)
            .where(FlowNode.flow_revision_id == flow.active_flow_revision_id)
            .where(FlowNode.id != UUID(excluded_flow_node_id))
            .order_by(FlowNode.order_index.asc())
            .limit(1)
        )
        assert sibling_node is not None

        sibling_node.state = FlowNodeState.RUNNING
        sibling_attempt = NodeAttempt(
            flow_id=flow.id,
            flow_revision_id=flow.active_flow_revision_id,
            flow_node_id=sibling_node.id,
            number=1,
            status=NodeAttemptStatus.RUNNING,
            started_at=datetime.now(UTC).replace(tzinfo=None),
        )
        session.add(sibling_attempt)
        await session.flush()
        session.add(
            NodeSession(
                flow_id=flow.id,
                flow_node_id=sibling_node.id,
                node_attempt_id=sibling_attempt.id,
                provider_session_key="competing-running-session",
                status=NodeSessionStatus.ACTIVE,
                last_seen_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        await session.commit()
        return str(sibling_node.id), str(sibling_attempt.id)


async def test_runtime_control_flow_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            flow_id, _, first_flow_node_id, compiled_plan_id = await _bootstrap_compile_start(
                client
            )

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200
            continue_payload = continue_response.json()
            assert continue_payload["status"] == "blocked"
            assert _find_node_state(continue_payload["nodes"], first_flow_node_id) == "waiting"

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_payload = inspect_response.json()
            assert inspect_payload["status"] == "blocked"
            assert inspect_payload["seed_compiled_plan_id"] == compiled_plan_id
            assert _find_node_state(inspect_payload["nodes"], first_flow_node_id) == "waiting"

            manifest_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifest_response.status_code == 200
            manifests_payload = manifest_response.json()
            assert len(manifests_payload) == 1
            manifest = manifests_payload[0]
            manifest_id = manifest["id"]
            assert manifest["status"] == "projected"

            blocked_continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert blocked_continue_response.status_code == 409

            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            ack_payload = ack_response.json()
            assert ack_payload["status"] == "running"
            assert _find_node_state(ack_payload["nodes"], first_flow_node_id) == "running"
            first_node = _find_node(ack_payload["nodes"], first_flow_node_id)
            assert first_node is not None
            assert first_node["current_manifest"]["status"] == "acked"
            assert first_node["current_manifest"]["node_session_key"] is not None
            assert first_node["current_manifest"]["ack_checkpoint_id"] is not None

            approval_response = await client.post(
                "/internal/approvals",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": first_node["current_attempt"]["id"],
                    "reason": "need human confirmation",
                    "request_payload": {"action": "sync"},
                    **_manifest_binding(first_node["current_manifest"]),
                },
            )
            assert approval_response.status_code == 201
            approval_payload = approval_response.json()
            assert approval_payload["status"] == "pending"

            approval_bundle_response = await client.get(
                f"/internal/flows/{flow_id}/worker-bundle",
                params=_manifest_binding(first_node["current_manifest"]),
            )
            assert approval_bundle_response.status_code == 200
            assert approval_bundle_response.json()["runtime_container"]["status"] == "blocked"

            resolve_response = await client.post(
                f"/approvals/{approval_payload['id']}/resolve",
                json={
                    "status": "approved",
                    "resolution_payload": {"by": "tester"},
                },
            )
            assert resolve_response.status_code == 200

            blocked_checkpoint_response = await client.post(
                "/internal/flows/checkpoints",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": first_node["current_attempt"]["id"],
                    "sequence_no": 1,
                    "status": "green",
                    "summary": "should require explicit continue",
                    "payload": {"result": "not-yet"},
                    **_manifest_binding(first_node["current_manifest"]),
                },
            )
            assert blocked_checkpoint_response.status_code == 201

            post_checkpoint_response = await client.get(f"/flows/{flow_id}")
            assert post_checkpoint_response.status_code == 200
            post_checkpoint_payload = post_checkpoint_response.json()
            assert post_checkpoint_payload["status"] in {"running", "succeeded", "blocked"}
            assert _find_node_state(post_checkpoint_payload["nodes"], first_flow_node_id) == "done"

            next_manifest_response = await client.get(
                f"/internal/flows/{flow_id}/context-manifests"
            )
            assert next_manifest_response.status_code == 200
            next_manifests_payload = next_manifest_response.json()
            assert any(manifest["status"] == "projected" for manifest in next_manifests_payload)

            cancel_response = await client.post(f"/flows/{flow_id}/cancel")
            assert cancel_response.status_code == 200
            cancel_payload = cancel_response.json()
            assert cancel_payload["status"] == "cancelled"
            paused_nodes = [node for node in cancel_payload["nodes"] if node["state"] == "paused"]
            assert paused_nodes

            checkpoints_response = await client.get(f"/internal/flows/{flow_id}/checkpoints")
            assert checkpoints_response.status_code == 200
            checkpoints_payload = checkpoints_response.json()
            assert len(checkpoints_payload) == 1
            assert checkpoints_payload[0]["summary"] == "should require explicit continue"
    finally:
        app.dependency_overrides.clear()


async def test_checkpoint_accepts_long_recommended_next_action_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            flow_id, _, first_flow_node_id, _compiled_plan_id = await _bootstrap_compile_start(
                client
            )

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            projected_manifest = next(
                manifest
                for manifest in manifests_response.json()
                if manifest["status"] == "projected"
            )

            ack_response = await _ack_manifest_via_api(client, projected_manifest)
            assert ack_response.status_code == 200
            ack_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert ack_node is not None
            attempt_id = ack_node["current_attempt"]["id"]

            long_next_action = (
                "Inspect AutoClaw internal checkpoint callback handling and bridge logs for this "
                "flow/node attempt because manifest acknowledgement succeeded but the checkpoint "
                "write failed unexpectedly during delegated execution."
            )
            assert len(long_next_action) > 128

            checkpoint_response = await client.post(
                "/internal/flows/checkpoints",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": attempt_id,
                    "sequence_no": 1,
                    "status": "blocked",
                    "summary": "worker hit a downstream callback issue",
                    "payload": {"result": "inspect-callbacks"},
                    "recommended_next_action": long_next_action,
                    "wait_reason": "operator",
                    **_manifest_binding(ack_node["current_manifest"]),
                },
            )
            assert checkpoint_response.status_code == 201
            checkpoint_payload = checkpoint_response.json()
            assert checkpoint_payload["recommended_next_action"] == long_next_action

            checkpoints_response = await client.get(f"/internal/flows/{flow_id}/checkpoints")
            assert checkpoints_response.status_code == 200
            checkpoints_payload = checkpoints_response.json()
            assert checkpoints_payload[0]["recommended_next_action"] == long_next_action
    finally:
        app.dependency_overrides.clear()


async def _advance_flow_node_via_api(
    client: AsyncClient,
    *,
    flow_id: str,
    expected_node_key: str,
) -> None:
    continue_response = await client.post(f"/flows/{flow_id}/continue")
    if continue_response.status_code == 200:
        continue_payload = continue_response.json()
    elif continue_response.status_code == 409:
        inspect_response = await client.get(f"/flows/{flow_id}")
        assert inspect_response.status_code == 200
        continue_payload = inspect_response.json()
    else:
        raise AssertionError(f"unexpected continue response: {continue_response.status_code}")
    assert continue_payload["status"] in {
        "blocked",
        "running",
        "pending",
        "succeeded",
        "failed",
        "paused",
    }

    manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
    assert manifests_response.status_code == 200
    projected_manifest = next(
        manifest for manifest in manifests_response.json() if manifest["status"] == "projected"
    )

    projected_node = _find_node(continue_payload["nodes"], projected_manifest["flow_node_id"])
    assert projected_node is not None
    assert projected_node["node_key"] == expected_node_key

    ack_response = await _ack_manifest_via_api(client, projected_manifest)
    assert ack_response.status_code == 200
    ack_payload = ack_response.json()
    running_node = _find_node(ack_payload["nodes"], projected_manifest["flow_node_id"])
    assert running_node is not None
    assert running_node["state"] == "running"
    assert running_node["current_attempt"] is not None

    checkpoint_response = await client.post(
        "/internal/flows/checkpoints",
        json={
            "flow_id": flow_id,
            "flow_node_id": projected_manifest["flow_node_id"],
            "node_attempt_id": running_node["current_attempt"]["id"],
            "sequence_no": 1,
            "status": "green",
            "summary": f"{expected_node_key} done",
            "payload": {"node": expected_node_key},
            **_manifest_binding(running_node["current_manifest"]),
        },
    )
    assert checkpoint_response.status_code == 201


async def test_rejected_approval_fails_flow_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifest_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifest_response.status_code == 200
            manifests_payload = manifest_response.json()
            assert len(manifests_payload) == 1

            ack_response = await _ack_manifest_via_api(client, manifests_payload[0])
            assert ack_response.status_code == 200
            ack_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert ack_node is not None

            approval_response = await client.post(
                "/internal/approvals",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": ack_node["current_attempt"]["id"],
                    "reason": "operator rejection path",
                    "request_payload": {"action": "review"},
                    **_manifest_binding(ack_node["current_manifest"]),
                },
            )
            assert approval_response.status_code == 201
            approval_id = approval_response.json()["id"]

            sibling_approval_response = await client.post(
                "/internal/approvals",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": ack_node["current_attempt"]["id"],
                    "reason": "second approval should expire on rejection",
                    "request_payload": {"action": "double-check"},
                    **_manifest_binding(ack_node["current_manifest"]),
                },
            )
            assert sibling_approval_response.status_code == 201
            sibling_approval_id = sibling_approval_response.json()["id"]

            reject_response = await client.post(
                f"/approvals/{approval_id}/resolve",
                json={
                    "status": "rejected",
                    "resolution_payload": {"by": "tester"},
                },
            )
            assert reject_response.status_code == 200
            assert reject_response.json()["status"] == "rejected"

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_payload = inspect_response.json()
            assert inspect_payload["status"] == "failed"
            assert _find_node_state(inspect_payload["nodes"], first_flow_node_id) == "failed"

            sibling_read_response = await client.get(f"/approvals/{sibling_approval_id}")
            assert sibling_read_response.status_code == 200
            assert sibling_read_response.json()["status"] == "expired"

            manifests_after_reject = await client.get(
                f"/internal/flows/{flow_id}/context-manifests"
            )
            assert manifests_after_reject.status_code == 200
            assert all(
                manifest["status"] != "projected" for manifest in manifests_after_reject.json()
            )

            ack_after_reject = await _ack_manifest_via_api(client, manifests_payload[0])
            assert ack_after_reject.status_code == 200
            assert ack_after_reject.json()["status"] == "failed"

            continue_after_reject = await client.post(f"/flows/{flow_id}/continue")
            assert continue_after_reject.status_code == 409
    finally:
        app.dependency_overrides.clear()


async def test_ack_missing_context_manifest_returns_404_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            response = await client.post(
                "/internal/flows/context-manifests/00000000-0000-0000-0000-000000000000/ack",
                json={
                    "manifest_hash": "missing",
                    "node_session_key": "ocl_missing",
                },
            )
            assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_flow_audit_read_models_and_pause_retry_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            list_response = await client.get("/flows")
            assert list_response.status_code == 200
            list_payload = list_response.json()
            assert len(list_payload) == 1
            assert list_payload[0]["id"] == flow_id
            assert list_payload[0]["task"]["title"] == "kernel api flow"

            first_continue = await client.post(f"/flows/{flow_id}/continue")
            assert first_continue.status_code == 200

            operator_response = await client.get(f"/flows/{flow_id}/operator")
            assert operator_response.status_code == 200
            operator_payload = operator_response.json()
            assert operator_payload["task"]["title"] == "kernel api flow"
            assert operator_payload["pending_approval_count"] == 0
            assert operator_payload["projected_manifest_count"] == 1
            audit_response = await client.get(f"/internal/flows/{flow_id}/audit")
            assert audit_response.status_code == 200
            audit_payload = audit_response.json()
            assert len(audit_payload["manifests"]) == 1
            assert audit_payload["manifests"][0]["status"] == "projected"
            assert len(audit_payload["sessions"]) == 1
            assert audit_payload["sessions"][0]["status"] == "idle"
            assert isinstance(audit_payload.get("events"), list)
            assert any(
                event["type"] == "context_manifest_projected" for event in audit_payload["events"]
            )

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            manifest = manifests_response.json()[0]
            manifest_id = manifest["id"]
            assert manifest["node_session_key"] is not None

            pause_response = await client.post(f"/flows/{flow_id}/pause")
            assert pause_response.status_code == 200
            pause_payload = pause_response.json()
            assert pause_payload["flow"]["status"] == "paused"
            assert first_flow_node_id in pause_payload["paused_node_ids"]

            continue_after_pause = await client.post(f"/flows/{flow_id}/continue")
            assert continue_after_pause.status_code == 409

            ack_after_pause = await _ack_manifest_via_api(client, manifest)
            assert ack_after_pause.status_code == 409

            (
                retry_flow_id,
                _retry_revision_id,
                retry_flow_node_id,
                _retry_compiled_plan_id,
            ) = await _bootstrap_compile_start(client)
            retry_first_continue = await client.post(f"/flows/{retry_flow_id}/continue")
            assert retry_first_continue.status_code == 200

            retry_manifests_response = await client.get(
                f"/internal/flows/{retry_flow_id}/context-manifests"
            )
            retry_manifest = retry_manifests_response.json()[0]
            retry_manifest_id = retry_manifest["id"]
            retry_ack_response = await _ack_manifest_via_api(client, retry_manifest)
            assert retry_ack_response.status_code == 200
            retry_node = _find_node(retry_ack_response.json()["nodes"], retry_flow_node_id)
            assert retry_node is not None

            retry_checkpoint_response = await client.post(
                "/internal/flows/checkpoints",
                json={
                    "flow_id": retry_flow_id,
                    "flow_node_id": retry_flow_node_id,
                    "node_attempt_id": retry_node["current_attempt"]["id"],
                    "sequence_no": 1,
                    "status": "blocked",
                    "summary": "operator asked to retry",
                    "payload": {"result": "retry-soon"},
                    "recommended_next_action": "retry",
                    "wait_reason": "operator",
                    **_manifest_binding(retry_node["current_manifest"]),
                },
            )
            assert retry_checkpoint_response.status_code == 201

            retry_response = await client.post(
                f"/flows/{retry_flow_id}/nodes/{retry_flow_node_id}/retry"
            )
            assert retry_response.status_code == 200
            retry_payload = retry_response.json()
            assert retry_payload["flow"]["status"] == "blocked"
            assert retry_payload["retried_node_attempt_id"] != retry_node["current_attempt"]["id"]
            retried_node = _find_node(retry_payload["flow"]["nodes"], retry_flow_node_id)
            assert retried_node is not None
            assert retried_node["current_attempt"] is not None
            assert retried_node["current_attempt"]["id"] == retry_payload["retried_node_attempt_id"]
            assert retried_node["current_manifest"] is not None
            assert (
                retried_node["current_manifest"]["node_attempt_id"]
                == retry_payload["retried_node_attempt_id"]
            )

            audit_after_retry = await client.get(f"/internal/flows/{retry_flow_id}/audit")
            assert audit_after_retry.status_code == 200
            retry_audit_payload = audit_after_retry.json()
            retry_ack_events = [
                event
                for event in retry_audit_payload["events"]
                if event["type"] == "context_manifest_acknowledged"
            ]
            assert retry_ack_events
            assert retry_ack_events[-1]["data"]["ack_checkpoint_id"] is not None
            assert retry_ack_events[-1]["data"]["node_session_key"] is not None
            retry_attempts = [
                attempt
                for attempt in retry_audit_payload["attempts"]
                if attempt["flow_node_id"] == retry_flow_node_id
            ]
            assert len(retry_attempts) == 2
    finally:
        app.dependency_overrides.clear()


async def test_operator_and_audit_surface_include_task_resource_truth_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        await _insert_workflow_version(
            test_engine,
            key="resourceful-workflow",
            content=_resourceful_workflow_content(),
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            bootstrap_response = await client.post("/internal/registry/bootstrap")
            assert bootstrap_response.status_code == 200

            start_response = await client.post(
                "/flows/from-workflow/resourceful-workflow",
                json={
                    "task": {
                        "title": "resource api flow",
                        "description": "operator surface",
                        "input_payload": {"ticket": "A-3"},
                    }
                },
            )
            assert start_response.status_code == 201
            flow_id = start_response.json()["flow_id"]

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            operator_response = await client.get(f"/flows/{flow_id}/operator")
            assert operator_response.status_code == 200
            operator_payload = operator_response.json()

            resource_bindings = operator_payload["task"]["resource_bindings"]
            assert len(resource_bindings) == 3
            workspace_binding = next(
                binding
                for binding in resource_bindings
                if binding["binding_role"] == "primary_workspace"
            )
            manifest_binding = next(
                binding
                for binding in resource_bindings
                if binding["binding_role"] == "manifest_root"
            )
            assert workspace_binding["workspace_root"]["key"] == (
                f"task.{operator_payload['task']['id']}.workspace"
            )
            assert manifest_binding["manifest_root"]["storage_uri"] == (
                f"task://{operator_payload['task']['id']}/manifests"
            )

            root_node = next(
                node for node in operator_payload["flow"]["nodes"] if node["node_key"] == "root"
            )
            assert root_node["current_manifest"] is not None
            assert root_node["current_manifest"]["manifest_root_id"] == (
                manifest_binding["manifest_root_id"]
            )
            assert root_node["current_manifest"]["manifest_payload"]["task_defaults"]["context"][
                "seed_from"
            ] == ["task_input", "workspace_docs"]
            workspace_mount = root_node["current_manifest"]["manifest_payload"]["resources"][
                "workspace"
            ]["mounts"][0]
            assert workspace_mount["ref"] == "task.primary_workspace"
            assert workspace_mount["key"] == workspace_binding["workspace_root"]["key"]

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifests_payload = manifests_response.json()
            assert len(manifests_payload) == 1
            assert manifests_payload[0]["manifest_root_id"] == manifest_binding["manifest_root_id"]
            assert manifests_payload[0]["manifest_payload"]["node"]["node_key"] == "root"

            audit_response = await client.get(f"/internal/flows/{flow_id}/audit")
            assert audit_response.status_code == 200
            audit_payload = audit_response.json()
            assert len(audit_payload["task"]["resource_bindings"]) == 3
            assert audit_payload["manifests"][0]["manifest_root_id"] == (
                manifest_binding["manifest_root_id"]
            )
            assert audit_payload["manifests"][0]["manifest_payload"]["resources"]["workspace"][
                "mounts"
            ][0]["key"] == workspace_binding["workspace_root"]["key"]
    finally:
        app.dependency_overrides.clear()


async def test_replan_api_preserves_task_resource_truth_in_active_operator_view(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        await _insert_workflow_version(
            test_engine,
            key="resourceful-workflow",
            content=_resourceful_workflow_content(),
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            bootstrap_response = await client.post("/internal/registry/bootstrap")
            assert bootstrap_response.status_code == 200

            start_response = await client.post(
                "/flows/from-workflow/resourceful-workflow",
                json={
                    "task": {
                        "title": "resourceful replan api flow",
                        "description": "operator replan truth",
                        "input_payload": {"ticket": "A-4"},
                    }
                },
            )
            assert start_response.status_code == 201
            flow_id = start_response.json()["flow_id"]

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200
            root_node = next(
                node for node in continue_response.json()["nodes"] if node["node_key"] == "root"
            )
            assert root_node["current_attempt"] is not None

            replan_response = await client.post(
                f"/flows/{flow_id}/replans",
                json={
                    "requesting_flow_node_id": root_node["id"],
                    "requesting_node_attempt_id": root_node["current_attempt"]["id"],
                    "reason": "tighten task resource truth",
                    "patch": {
                        "task_defaults": {
                            "context": {
                                "mode": "ensure_task_primary",
                                "seed_from": ["task_input"],
                            }
                        },
                        "nodes": [
                            {
                                "id": "root",
                                "role": "planner-supervisor",
                                "mode": "plan",
                                "resources": {
                                    "workspace": {
                                        "mounts": [
                                            {
                                                "ref": "task.primary_workspace",
                                                "access": "read_write",
                                            }
                                        ]
                                    },
                                    "context": {"refs": [{"ref": "task.primary_context"}]},
                                },
                            },
                            {
                                "id": "loop",
                                "role": "main-loop-worker",
                                "mode": "persistent_execute",
                                "resources": {
                                    "workspace": {
                                        "mounts": [
                                            {
                                                "ref": "task.primary_workspace",
                                                "access": "read_only",
                                            }
                                        ]
                                    },
                                    "context": {"refs": [{"ref": "task.primary_context"}]},
                                },
                            },
                        ],
                        "edges": [{"from": "root", "to": "loop"}],
                    },
                },
            )
            assert replan_response.status_code == 201
            replan_payload = replan_response.json()
            assert replan_payload["status"] == "adopted"
            assert replan_payload["patch_payload"]["task_defaults"]["context"]["seed_from"] == [
                "task_input"
            ]
            assert replan_payload["patch_payload"]["nodes"][0]["resources"]["workspace"][
                "mounts"
            ][0]["access"] == "read_write"

            operator_response = await client.get(f"/flows/{flow_id}/operator")
            assert operator_response.status_code == 200
            operator_payload = operator_response.json()
            replanned_root = next(
                node for node in operator_payload["flow"]["nodes"] if node["node_key"] == "root"
            )
            replanned_root_payload = replanned_root["effective_payload"]
            assert replanned_root_payload["task_defaults"]["context"]["seed_from"] == [
                "task_input"
            ]
            assert replanned_root_payload["resources"]["workspace"]["mounts"][0][
                "access"
            ] == "read_write"

            replanned_loop = next(
                node for node in operator_payload["flow"]["nodes"] if node["node_key"] == "loop"
            )
            assert replanned_loop["effective_payload"]["resources"]["workspace"]["mounts"][0][
                "access"
            ] == "read_only"

            session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
            async with session_factory() as db_session:
                flow_row = await db_session.scalar(select(Flow).where(Flow.id == UUID(flow_id)))
                assert flow_row is not None
                task_compose = await db_session.scalar(
                    select(TaskCompose).where(TaskCompose.task_id == flow_row.task_id)
                )
                assert task_compose is not None
                assert task_compose.compose_payload["task_defaults"]["context"]["seed_from"] == [
                    "task_input"
                ]

            replans_response = await client.get(f"/internal/flows/{flow_id}/replans")
            assert replans_response.status_code == 200
            assert replans_response.json()[0]["patch_payload"]["task_defaults"]["context"][
                "seed_from"
            ] == ["task_input"]
    finally:
        app.dependency_overrides.clear()


async def test_review_manifest_includes_upstream_checkpoint_evidence_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            bootstrap_response = await client.post("/internal/registry/bootstrap")
            assert bootstrap_response.status_code == 200

            start_response = await client.post(
                "/flows/from-workflow/max-complexity-review",
                json={
                    "task": {
                        "title": "max complexity evidence flow",
                        "description": "phase eight evidence propagation",
                        "input_payload": {"source": "test"},
                    }
                },
            )
            assert start_response.status_code == 201
            flow_id = start_response.json()["flow_id"]

            for node_key in [
                "root",
                "root.discovery",
                "root.product",
                "root.implementation_loop",
                "root.implementation_loop.cycle",
            ]:
                await _advance_flow_node_via_api(
                    client,
                    flow_id=flow_id,
                    expected_node_key=node_key,
                )

            audit_response = await client.get(f"/internal/flows/{flow_id}/audit")
            assert audit_response.status_code == 200
            audit_payload = audit_response.json()
            projected_manifest = next(
                manifest
                for manifest in audit_payload["manifests"]
                if manifest["status"] == "projected"
                and manifest["manifest_payload"]["node"]["node_key"] == "root.review_and_governance"
            )
            evidence_items = [
                item
                for item in projected_manifest["manifest_payload"]["required_items"]
                if item["storage_uri"].startswith("checkpoint://")
            ]
            assert evidence_items
            implementation_cycle_evidence = next(
                item
                for item in evidence_items
                if item["inline_content"]["flow_node_key"] == "root.implementation_loop.cycle"
            )
            assert implementation_cycle_evidence["kind"] == "summary"
            assert implementation_cycle_evidence["inline_content"]["status"] == "green"
            assert implementation_cycle_evidence["inline_content"]["summary"] == (
                "root.implementation_loop.cycle done"
            )
    finally:
        app.dependency_overrides.clear()


async def test_max_complexity_workflow_runs_to_completion_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            bootstrap_response = await client.post("/internal/registry/bootstrap")
            assert bootstrap_response.status_code == 200
            assert bootstrap_response.json()["workflows"] == 4

            start_response = await client.post(
                "/flows/from-workflow/max-complexity-review",
                json={
                    "task": {
                        "title": "max complexity flow",
                        "description": "phase six api flow",
                        "input_payload": {"source": "test"},
                    }
                },
            )
            assert start_response.status_code == 201
            flow_id = start_response.json()["flow_id"]

            for node_key in [
                "root",
                "root.discovery",
                "root.product",
                "root.implementation_loop",
                "root.implementation_loop.cycle",
                "root.review_and_governance",
                "root.review_and_governance.security",
                "root.sync",
            ]:
                await _advance_flow_node_via_api(
                    client,
                    flow_id=flow_id,
                    expected_node_key=node_key,
                )

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_payload = inspect_response.json()
            assert inspect_payload["status"] == "succeeded"
            assert all(node["state"] == "done" for node in inspect_payload["nodes"])
    finally:
        app.dependency_overrides.clear()


async def test_create_approval_requires_matching_node_attempt_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            await _advance_flow_node_via_api(
                client,
                flow_id=flow_id,
                expected_node_key="root",
            )

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            projected_manifest = next(
                manifest
                for manifest in manifests_response.json()
                if manifest["status"] == "projected"
            )

            ack_response = await _ack_manifest_via_api(client, projected_manifest)
            assert ack_response.status_code == 200
            second_node = _find_node(
                ack_response.json()["nodes"],
                projected_manifest["flow_node_id"],
            )
            assert second_node is not None
            assert second_node["current_attempt"] is not None

            mismatch_response = await client.post(
                "/internal/approvals",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": second_node["current_attempt"]["id"],
                    "reason": "mismatched binding",
                    "request_payload": {"action": "should-fail"},
                    **_manifest_binding(second_node["current_manifest"]),
                },
            )
            assert mismatch_response.status_code == 409
    finally:
        app.dependency_overrides.clear()


async def test_runtime_routes_require_api_key_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            public_response = await client.get("/flows")
            assert public_response.status_code == 401

            internal_response = await client.post("/internal/registry/bootstrap")
            assert internal_response.status_code == 401

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=operator_api_key_headers(),
        ) as client:
            public_response = await client.get("/flows")
            assert public_response.status_code == 200

            internal_response = await client.post("/internal/registry/bootstrap")
            assert internal_response.status_code == 401

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-AutoClaw-API-Key": "wrong-key"},
        ) as client:
            public_response = await client.get("/flows")
            assert public_response.status_code == 401

            internal_response = await client.post("/internal/registry/bootstrap")
            assert internal_response.status_code == 401
    finally:
        app.dependency_overrides.clear()


async def test_create_approval_requires_target_binding_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                _first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            response = await client.post(
                "/internal/approvals",
                json={
                    "flow_id": flow_id,
                    "reason": "missing target binding",
                    "request_payload": {"action": "review"},
                },
            )
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


async def test_resolve_approval_rejects_invalid_status_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            manifest = manifests_response.json()[0]
            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            ack_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert ack_node is not None

            approval_response = await client.post(
                "/internal/approvals",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": ack_node["current_attempt"]["id"],
                    "reason": "invalid resolve status",
                    "request_payload": {"action": "review"},
                    **_manifest_binding(ack_node["current_manifest"]),
                },
            )
            assert approval_response.status_code == 201

            resolve_response = await client.post(
                f"/approvals/{approval_response.json()['id']}/resolve",
                json={
                    "status": "expired",
                    "resolution_payload": {"by": "tester"},
                },
            )
            assert resolve_response.status_code == 422
    finally:
        app.dependency_overrides.clear()


async def test_acknowledged_manifest_is_idempotent_after_cancel_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                _first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]

            first_ack_response = await _ack_manifest_via_api(client, manifest)
            assert first_ack_response.status_code == 200
            assert first_ack_response.json()["status"] == "running"

            cancel_response = await client.post(f"/flows/{flow_id}/cancel")
            assert cancel_response.status_code == 200
            assert cancel_response.json()["status"] == "cancelled"

            second_ack_response = await _ack_manifest_via_api(client, manifest)
            assert second_ack_response.status_code == 200
            assert second_ack_response.json()["status"] == "cancelled"
    finally:
        app.dependency_overrides.clear()


async def test_not_required_approval_is_terminal_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            manifest = manifests_response.json()[0]
            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            ack_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert ack_node is not None

            approval_response = await client.post(
                "/internal/approvals",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": ack_node["current_attempt"]["id"],
                    "reason": "no operator action needed",
                    "request_payload": {"action": "review"},
                    **_manifest_binding(ack_node["current_manifest"]),
                },
            )
            assert approval_response.status_code == 201
            approval_id = approval_response.json()["id"]

            first_resolution = await client.post(
                f"/approvals/{approval_id}/resolve",
                json={
                    "status": "not_required",
                    "resolution_payload": {"by": "tester"},
                },
            )
            assert first_resolution.status_code == 200
            assert first_resolution.json()["status"] == "not_required"

            second_resolution = await client.post(
                f"/approvals/{approval_id}/resolve",
                json={
                    "status": "approved",
                    "resolution_payload": {"by": "tester"},
                },
            )
            assert second_resolution.status_code == 409
    finally:
        app.dependency_overrides.clear()


async def test_replan_requires_requesting_attempt_boundary_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            await _advance_flow_node_via_api(
                client,
                flow_id=flow_id,
                expected_node_key="root",
            )

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            root_node = _find_node(inspect_response.json()["nodes"], first_flow_node_id)
            assert root_node is not None
            assert root_node["current_attempt"] is not None

            missing_attempt_response = await client.post(
                f"/flows/{flow_id}/replans",
                json={
                    "requesting_flow_node_id": first_flow_node_id,
                    "reason": "should fail without attempt provenance",
                    "patch": {
                        "nodes": [
                            {"id": "root", "role": "planner-supervisor", "mode": "plan"},
                            {
                                "id": "root.discovery",
                                "role": "main-loop-worker",
                                "mode": "persistent_execute",
                            },
                        ],
                        "edges": [{"from": "root", "to": "root.discovery"}],
                    },
                },
            )
            assert missing_attempt_response.status_code == 422

            valid_response = await client.post(
                f"/flows/{flow_id}/replans",
                json={
                    "requesting_flow_node_id": first_flow_node_id,
                    "requesting_node_attempt_id": root_node["current_attempt"]["id"],
                    "reason": "replan from completed root attempt",
                    "patch": {
                        "nodes": [
                            {"id": "root", "role": "planner-supervisor", "mode": "plan"},
                            {
                                "id": "root.discovery",
                                "role": "main-loop-worker",
                                "mode": "persistent_execute",
                            },
                        ],
                        "edges": [{"from": "root", "to": "root.discovery"}],
                    },
                },
            )
            assert valid_response.status_code == 201
            assert (
                valid_response.json()["requesting_node_attempt_id"]
                == root_node["current_attempt"]["id"]
            )
    finally:
        app.dependency_overrides.clear()


async def test_context_manifest_ack_accepts_uuid_with_extra_hyphen_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]
            manifest_id = manifest["id"]

            malformed_manifest_id = _with_extra_uuid_hyphen(manifest_id)
            assert malformed_manifest_id != manifest_id

            ack_response = await _ack_manifest_via_api(
                client,
                manifest,
                manifest_id=malformed_manifest_id,
            )
            assert ack_response.status_code == 200
            ack_payload = ack_response.json()
            first_node = _find_node(ack_payload["nodes"], first_flow_node_id)
            assert first_node is not None
            assert first_node["current_manifest"]["status"] == "acked"
    finally:
        app.dependency_overrides.clear()


async def test_internal_openclaw_dispatch_bootstrap_is_routable(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            first_continue = await client.post(f"/flows/{flow_id}/continue")
            assert first_continue.status_code == 200
            first_payload = first_continue.json()
            assert first_payload["status"] == "blocked"
            assert _find_node_state(first_payload["nodes"], first_flow_node_id) == "waiting"

            captured: dict[str, object] = {}
            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _FakeOpenClawClient(captured),
            )

            dispatch_response = await client.post(
                f"/internal/flows/{flow_id}/dispatch-openclaw?wait_for_response=true"
            )
            assert dispatch_response.status_code == 200
            dispatch_payload = dispatch_response.json()
            assert dispatch_payload["delivery_status"] == "completed"
            assert dispatch_payload["phase"] == "bootstrap"
            assert dispatch_payload["openclaw_response_id"] == "resp_test"
            assert dispatch_payload["openclaw_output"] == "OK"
            assert captured["session_key"] is not None
            assert isinstance(captured["input"], str)
            assert "ack the manifest" in captured["input"]
            assert "inline_content" in captured["input"]
            assert '"source":"test"' in captured["input"]
            assert captured["tool_choice"] is None
            assert captured["tools"] is None
            assert dispatch_payload["manifest_id"] is not None
            assert dispatch_payload["manifest_hash"] is not None

            # optional sanity: node/session are echoed back in flow snapshot
            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_payload = inspect_response.json()
            assert isinstance(inspect_payload["nodes"], list)

    finally:
        app.dependency_overrides.clear()


async def test_internal_openclaw_dispatch_returns_accepted_and_runs_detached_by_default(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            first_continue = await client.post(f"/flows/{flow_id}/continue")
            assert first_continue.status_code == 200
            assert first_continue.json()["status"] == "blocked"

            captured: dict[str, object] = {}
            called = asyncio.Event()
            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _EventfulFakeOpenClawClient(captured, called),
            )

            dispatch_response = await client.post(f"/internal/flows/{flow_id}/dispatch-openclaw")
            assert dispatch_response.status_code == 202
            dispatch_payload = dispatch_response.json()
            assert dispatch_payload["delivery_status"] == "accepted"
            assert dispatch_payload["phase"] == "bootstrap"
            assert dispatch_payload["openclaw_response_id"] is None
            assert dispatch_payload["openclaw_output"] is None
            assert dispatch_payload["flow_node_id"] == first_flow_node_id
            assert dispatch_payload["manifest_id"] is not None
            assert dispatch_payload["manifest_hash"] is not None

            await asyncio.wait_for(called.wait(), timeout=1.0)
            assert captured["session_key"] == dispatch_payload["node_session_key"]
            assert isinstance(captured["input"], str)
            assert "ack the manifest" in captured["input"]

    finally:
        app.dependency_overrides.clear()


async def test_internal_watchdog_recover_dispatches_same_session_wake_via_api(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]

            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            running_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert running_node is not None
            node_attempt_id = running_node["current_attempt"]["id"]

            await _age_attempt_started_at(test_engine, node_attempt_id)

            watchdog_response = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert watchdog_response.status_code == 200
            assert watchdog_response.json()["stalled_node_attempt_ids"] == [node_attempt_id]

            captured: dict[str, object] = {}
            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _FakeOpenClawClient(captured),
            )

            recover_response = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert recover_response.status_code == 200
            recover_payload = recover_response.json()
            assert recover_payload["recovery_action"] == "wake"
            assert recover_payload["recovery_reason"] == "wake-dispatched"
            assert recover_payload["flow_node_id"] == first_flow_node_id
            assert recover_payload["node_attempt_id"] == node_attempt_id
            assert recover_payload["openclaw_response_id"] == "resp_test"
            assert recover_payload["openclaw_output"] == "OK"
            assert captured["session_key"] == recover_payload["node_session_key"]
            assert isinstance(captured["input"], str)
            assert "Watchdog recovery wake-up" in captured["input"]
            assert "Do not restart from scratch" in captured["input"]

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_node = _find_node(inspect_response.json()["nodes"], first_flow_node_id)
            assert inspect_node is not None
            assert inspect_node["state"] == "running"
            assert inspect_node["current_attempt"]["id"] == node_attempt_id

            flow_node_record = await _read_flow_node_record(test_engine, first_flow_node_id)
            assert flow_node_record.status_payload["watchdog_recovery"]["auto_wake_count"] == 1
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["last_action"]
                == "wake-dispatched"
            )
    finally:
        app.dependency_overrides.clear()


async def test_internal_watchdog_recover_targets_watchdog_attempt_even_with_other_running_node(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]

            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            running_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert running_node is not None
            node_attempt_id = running_node["current_attempt"]["id"]

            await _age_attempt_started_at(test_engine, node_attempt_id)
            watchdog_response = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert watchdog_response.status_code == 200

            await _seed_competing_running_attempt(test_engine, flow_id, first_flow_node_id)

            captured: dict[str, object] = {}
            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _FakeOpenClawClient(captured),
            )

            recover_response = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert recover_response.status_code == 200
            recover_payload = recover_response.json()
            assert recover_payload["recovery_action"] == "wake"
            assert recover_payload["flow_node_id"] == first_flow_node_id
            assert recover_payload["node_attempt_id"] == node_attempt_id
            assert captured["session_key"] == recover_payload["node_session_key"]
            assert captured["session_key"] != "competing-running-session"
    finally:
        app.dependency_overrides.clear()


async def test_internal_watchdog_recover_reverts_to_safe_blocked_state_on_dispatch_failure(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]

            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            running_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert running_node is not None
            node_attempt_id = running_node["current_attempt"]["id"]

            await _age_attempt_started_at(test_engine, node_attempt_id)
            watchdog_response = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert watchdog_response.status_code == 200

            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _RaisingFakeOpenClawClient(),
            )

            recover_response = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert recover_response.status_code == 200
            recover_payload = recover_response.json()
            assert recover_payload["recovery_action"] == "escalate"
            assert recover_payload["recovery_reason"] == "wake-dispatch-failed"
            assert "simulated wake dispatch failure" in recover_payload["detail"]

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_node = _find_node(inspect_response.json()["nodes"], first_flow_node_id)
            assert inspect_node is not None
            assert inspect_node["state"] == "waiting"
            assert inspect_node["current_attempt"]["id"] == node_attempt_id

            flow_node_record = await _read_flow_node_record(test_engine, first_flow_node_id)
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["node_attempt_id"]
                == node_attempt_id
            )
            assert flow_node_record.status_payload["watchdog_recovery"]["auto_wake_count"] == 1
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["last_action"]
                == "escalate:wake-dispatch-failed"
            )
    finally:
        app.dependency_overrides.clear()


async def test_internal_watchdog_recover_escalates_on_wake_timeout_via_api(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]

            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            running_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert running_node is not None
            node_attempt_id = running_node["current_attempt"]["id"]

            await _age_attempt_started_at(test_engine, node_attempt_id)

            watchdog_response = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert watchdog_response.status_code == 200

            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _RaisingOpenClawClient(OpenClawTimeoutError("OpenClaw request timed out")),
            )

            recover_response = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert recover_response.status_code == 200
            recover_payload = recover_response.json()
            assert recover_payload["recovery_action"] == "escalate"
            assert recover_payload["recovery_reason"] == "wake-dispatch-timeout"
            assert recover_payload["flow_node_id"] == first_flow_node_id
            assert recover_payload["node_attempt_id"] == node_attempt_id
            assert "inspect" in recover_payload["operator_next_step"].lower()
            assert "ambiguous" in recover_payload["detail"].lower()

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_node = _find_node(inspect_response.json()["nodes"], first_flow_node_id)
            assert inspect_node is not None
            assert inspect_node["state"] == "running"
            assert inspect_node["current_attempt"]["status"] == "running"

            flow_node_record = await _read_flow_node_record(test_engine, first_flow_node_id)
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["node_attempt_id"]
                == node_attempt_id
            )
            assert flow_node_record.status_payload["watchdog_recovery"]["auto_wake_count"] == 1
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["last_action"]
                == "escalate:wake-dispatch-timeout"
            )
    finally:
        app.dependency_overrides.clear()


async def test_internal_watchdog_recover_timeout_keeps_attempt_open_for_late_callbacks(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]

            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            running_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert running_node is not None
            node_attempt_id = running_node["current_attempt"]["id"]

            await _age_attempt_started_at(test_engine, node_attempt_id)
            watchdog_response = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert watchdog_response.status_code == 200

            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _RaisingOpenClawClient(OpenClawTimeoutError("OpenClaw request timed out")),
            )

            recover_response = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert recover_response.status_code == 200
            assert recover_response.json()["recovery_reason"] == "wake-dispatch-timeout"

            checkpoint_response = await client.post(
                "/internal/flows/checkpoints",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": node_attempt_id,
                    "sequence_no": 2,
                    "status": "green",
                    "summary": "late callback after ambiguous wake timeout",
                    "payload": {},
                    **_manifest_binding(running_node["current_manifest"]),
                },
            )
            assert checkpoint_response.status_code == 201

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_node = _find_node(inspect_response.json()["nodes"], first_flow_node_id)
            assert inspect_node is not None
            assert inspect_node["state"] == "done"
            assert inspect_node["current_attempt"]["status"] == "succeeded"
    finally:
        app.dependency_overrides.clear()


async def test_internal_watchdog_recover_escalates_on_wake_failure_via_api(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]

            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            running_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert running_node is not None
            node_attempt_id = running_node["current_attempt"]["id"]

            await _age_attempt_started_at(test_engine, node_attempt_id)

            watchdog_response = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert watchdog_response.status_code == 200

            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _RaisingOpenClawClient(
                    OpenClawIntegrationError("worker callback rejected")
                ),
            )

            recover_response = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert recover_response.status_code == 200
            recover_payload = recover_response.json()
            assert recover_payload["recovery_action"] == "escalate"
            assert recover_payload["recovery_reason"] == "wake-dispatch-failed"
            assert recover_payload["flow_node_id"] == first_flow_node_id
            assert recover_payload["node_attempt_id"] == node_attempt_id
            assert "worker callback rejected" in recover_payload["detail"]

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_node = _find_node(inspect_response.json()["nodes"], first_flow_node_id)
            assert inspect_node is not None
            assert inspect_node["state"] == "waiting"
            assert inspect_node["current_attempt"]["status"] == "blocked"

            flow_node_record = await _read_flow_node_record(test_engine, first_flow_node_id)
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["node_attempt_id"]
                == node_attempt_id
            )
            assert flow_node_record.status_payload["watchdog_recovery"]["auto_wake_count"] == 1
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["last_action"]
                == "escalate:wake-dispatch-failed"
            )
    finally:
        app.dependency_overrides.clear()


async def test_internal_watchdog_recover_escalates_after_auto_wake_budget_via_api(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]

            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            running_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert running_node is not None
            node_attempt_id = running_node["current_attempt"]["id"]

            await _age_attempt_started_at(test_engine, node_attempt_id)
            watchdog_response = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert watchdog_response.status_code == 200

            captured: dict[str, object] = {}
            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _FakeOpenClawClient(captured),
            )
            first_recover = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert first_recover.status_code == 200
            assert first_recover.json()["recovery_action"] == "wake"

            await _age_latest_checkpoint_created_at(test_engine, node_attempt_id)
            second_watchdog = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert second_watchdog.status_code == 200

            second_recover = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert second_recover.status_code == 200
            second_payload = second_recover.json()
            assert second_payload["recovery_action"] == "escalate"
            assert second_payload["recovery_reason"] == "wake-budget-exhausted"
            assert second_payload["flow_node_id"] == first_flow_node_id
            assert second_payload["node_attempt_id"] == node_attempt_id
            assert second_payload["openclaw_response_id"] is None
            assert "budget exhausted" in second_payload["detail"]

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            inspect_node = _find_node(inspect_response.json()["nodes"], first_flow_node_id)
            assert inspect_node is not None
            assert inspect_node["state"] == "waiting"

            flow_node_record = await _read_flow_node_record(test_engine, first_flow_node_id)
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["node_attempt_id"]
                == node_attempt_id
            )
            assert flow_node_record.status_payload["watchdog_recovery"]["auto_wake_count"] == 1
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["last_action"]
                == "escalate:wake-budget-exhausted"
            )
    finally:
        app.dependency_overrides.clear()


async def test_watchdog_auto_wake_budget_resets_for_new_retry_attempt_via_api(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            first_manifest = manifests_response.json()[0]

            ack_response = await _ack_manifest_via_api(client, first_manifest)
            assert ack_response.status_code == 200
            first_attempt_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert first_attempt_node is not None
            first_attempt_id = first_attempt_node["current_attempt"]["id"]

            await _age_attempt_started_at(test_engine, first_attempt_id)
            watchdog_response = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert watchdog_response.status_code == 200

            captured: dict[str, object] = {}
            monkeypatch.setattr(
                "app.services.openclaw_bridge.create_openclaw_client",
                lambda: _FakeOpenClawClient(captured),
            )
            first_recover = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert first_recover.status_code == 200
            assert first_recover.json()["recovery_action"] == "wake"

            await _age_latest_checkpoint_created_at(test_engine, first_attempt_id)
            second_watchdog = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert second_watchdog.status_code == 200

            second_recover = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert second_recover.status_code == 200
            assert second_recover.json()["recovery_action"] == "escalate"

            retry_response = await client.post(f"/flows/{flow_id}/nodes/{first_flow_node_id}/retry")
            assert retry_response.status_code == 200
            retried_node = _find_node(retry_response.json()["flow"]["nodes"], first_flow_node_id)
            assert retried_node is not None
            second_attempt_id = retried_node["current_attempt"]["id"]
            assert second_attempt_id != first_attempt_id

            second_manifest = retried_node["current_manifest"]
            assert second_manifest is not None
            second_ack = await _ack_manifest_via_api(client, second_manifest)
            assert second_ack.status_code == 200

            await _age_attempt_started_at(test_engine, second_attempt_id)
            third_watchdog = await client.post(f"/internal/flows/{flow_id}/watchdog")
            assert third_watchdog.status_code == 200

            third_recover = await client.post(f"/internal/flows/{flow_id}/watchdog/recover")
            assert third_recover.status_code == 200
            third_payload = third_recover.json()
            assert third_payload["recovery_action"] == "wake"
            assert third_payload["node_attempt_id"] == second_attempt_id

            flow_node_record = await _read_flow_node_record(test_engine, first_flow_node_id)
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["node_attempt_id"]
                == second_attempt_id
            )
            assert flow_node_record.status_payload["watchdog_recovery"]["auto_wake_count"] == 1
            assert (
                flow_node_record.status_payload["watchdog_recovery"]["last_action"]
                == "wake-dispatched"
            )
    finally:
        app.dependency_overrides.clear()


async def test_internal_replan_endpoint_is_available(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200
            first_payload = continue_response.json()
            first_node = _find_node(first_payload["nodes"], first_flow_node_id)
            assert first_node is not None
            assert first_node["current_attempt"] is not None

            ack_response = await _ack_manifest_via_api(client, first_node["current_manifest"])
            assert ack_response.status_code == 200
            ack_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert ack_node is not None

            internal_replan_response = await client.post(
                f"/internal/flows/{flow_id}/replans/internal",
                json={
                    "requesting_flow_node_id": first_flow_node_id,
                    "requesting_node_attempt_id": ack_node["current_attempt"]["id"],
                    "reason": "internal plugin request",
                    "patch": {
                        "nodes": [
                            {
                                "id": "root",
                                "role": "planner-supervisor",
                                "mode": "plan",
                            },
                            {
                                "id": "root.discovery",
                                "role": "main-loop-worker",
                                "mode": "persistent_execute",
                            },
                        ],
                        "edges": [{"from": "root", "to": "root.discovery"}],
                    },
                    **_manifest_binding(ack_node["current_manifest"]),
                },
            )
            assert internal_replan_response.status_code == 201
            assert internal_replan_response.json()["requesting_flow_node_id"] == first_flow_node_id

            stale_bundle_response = await client.get(
                f"/internal/flows/{flow_id}/worker-bundle",
                params=_manifest_binding(ack_node["current_manifest"]),
            )
            assert stale_bundle_response.status_code == 200
            stale_bundle_payload = stale_bundle_response.json()
            compiled_node_keys = {
                node["node_key"] for node in stale_bundle_payload["compiled_plan"]["nodes"]
            }
            assert "review" in compiled_node_keys
            assert "root.discovery" not in compiled_node_keys
            assert stale_bundle_payload["runtime_container"]["status"] == "aborted"

    finally:
        app.dependency_overrides.clear()


async def test_operator_view_marks_retryable_waiting_node_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                retry_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            retry_first_continue = await client.post(f"/flows/{flow_id}/continue")
            assert retry_first_continue.status_code == 200

            retry_manifests_response = await client.get(
                f"/internal/flows/{flow_id}/context-manifests"
            )
            retry_manifest = retry_manifests_response.json()[0]
            retry_ack_response = await _ack_manifest_via_api(client, retry_manifest)
            assert retry_ack_response.status_code == 200
            retry_node = _find_node(retry_ack_response.json()["nodes"], retry_flow_node_id)
            assert retry_node is not None

            retry_node_attempt_id = retry_node["current_attempt"]["id"]
            retry_checkpoint_response = await client.post(
                "/internal/flows/checkpoints",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": retry_flow_node_id,
                    "node_attempt_id": retry_node_attempt_id,
                    "sequence_no": 1,
                    "status": "blocked",
                    "summary": "operator asked to retry",
                    "payload": {"result": "retry-soon"},
                    "recommended_next_action": "retry",
                    "wait_reason": "operator",
                    **_manifest_binding(retry_node["current_manifest"]),
                },
            )
            assert retry_checkpoint_response.status_code == 201

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=operator_api_key_headers(),
        ) as operator_client:
            operator_response = await operator_client.get(f"/flows/{flow_id}/operator")
            assert operator_response.status_code == 200
            operator_node = _find_node(
                operator_response.json()["flow"]["nodes"],
                retry_flow_node_id,
            )
            assert operator_node is not None
            assert operator_node["state"] == "waiting"
            assert operator_node["retryable"] is True
            assert operator_node["current_wait_reason"] == "operator"
    finally:
        app.dependency_overrides.clear()


async def test_retry_rejects_never_started_node_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                _first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            inspect_response = await client.get(f"/flows/{flow_id}")
            assert inspect_response.status_code == 200
            unstarted_node = next(
                node for node in inspect_response.json()["nodes"] if node["current_attempt"] is None
            )
            assert unstarted_node["current_attempt"] is None

            retry_response = await client.post(
                f"/flows/{flow_id}/nodes/{unstarted_node['id']}/retry"
            )
            assert retry_response.status_code == 409
    finally:
        app.dependency_overrides.clear()


async def test_operator_view_marks_context_wait_and_non_retryable_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=operator_api_key_headers(),
        ) as operator_client:
            operator_response = await operator_client.get(f"/flows/{flow_id}/operator")
            assert operator_response.status_code == 200
            operator_node = _find_node(
                operator_response.json()["flow"]["nodes"],
                first_flow_node_id,
            )
            assert operator_node is not None
            assert operator_node["current_wait_reason"] == "context"
            assert operator_node["retryable"] is False
    finally:
        app.dependency_overrides.clear()


async def test_retry_rejects_approval_blocked_node_after_stale_retry_hint_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            manifest = manifests_response.json()[0]
            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200
            ack_node = _find_node(ack_response.json()["nodes"], first_flow_node_id)
            assert ack_node is not None
            node_attempt_id = ack_node["current_attempt"]["id"]

            checkpoint_response = await client.post(
                "/internal/flows/checkpoints",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": node_attempt_id,
                    "sequence_no": 1,
                    "status": "blocked",
                    "summary": "operator suggested retry",
                    "payload": {"result": "retry-later"},
                    "recommended_next_action": "retry",
                    "wait_reason": "operator",
                    **_manifest_binding(ack_node["current_manifest"]),
                },
            )
            assert checkpoint_response.status_code == 201

            approval_response = await client.post(
                "/internal/approvals",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": node_attempt_id,
                    "reason": "human approval now required",
                    "request_payload": {"action": "review"},
                    **_manifest_binding(ack_node["current_manifest"]),
                },
            )
            assert approval_response.status_code == 201

            retry_response = await client.post(f"/flows/{flow_id}/nodes/{first_flow_node_id}/retry")
            assert retry_response.status_code == 409

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=operator_api_key_headers(),
        ) as operator_client:
            operator_response = await operator_client.get(f"/flows/{flow_id}/operator")
            assert operator_response.status_code == 200
            operator_node = _find_node(
                operator_response.json()["flow"]["nodes"],
                first_flow_node_id,
            )
            assert operator_node is not None
            assert operator_node["current_wait_reason"] == "approval"
            assert operator_node["retryable"] is False
    finally:
        app.dependency_overrides.clear()


async def test_worker_bundle_and_publish_context_item_surface_via_api(
    test_engine: AsyncEngine,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_db_override(test_engine)
    data_dir = tmp_path / "autoclaw-data"
    monkeypatch.setenv("AUTOCLAW_DATA_DIR", str(data_dir))
    config_module.get_settings.cache_clear()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            flow_id, _revision_id, _first_flow_node_id, _compiled_plan_id = await _bootstrap_compile_start(
                client
            )

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_response.status_code == 200
            manifest = manifests_response.json()[0]

            bundle_response = await client.get(
                f"/internal/flows/{flow_id}/worker-bundle",
                params=_manifest_binding(manifest),
            )
            assert bundle_response.status_code == 200
            bundle_payload = bundle_response.json()
            assert bundle_payload["task_compose"] is not None
            assert bundle_payload["runtime_container"] is not None
            task_id = bundle_payload["task"]["id"]
            materialized_paths = bundle_payload["task_compose"]["compose_payload"]["materialized_paths"]
            assert Path(materialized_paths["workspace"]) == data_dir / "tasks" / task_id / "workspace"
            assert Path(materialized_paths["context"]) == data_dir / "tasks" / task_id / "context"
            assert Path(materialized_paths["manifests"]) == data_dir / "tasks" / task_id / "manifests"
            assert Path(materialized_paths["workspace"]).is_dir()
            assert Path(materialized_paths["context"]).is_dir()
            assert Path(materialized_paths["manifests"]).is_dir()
            assert bundle_payload["runtime_container"]["status"] == "bootstrap_blocked"

            projected_publish = await client.post(
                "/internal/flows/context-items",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": manifest["flow_node_id"],
                    "node_attempt_id": manifest["node_attempt_id"],
                    **_manifest_binding(manifest),
                    "ack_checkpoint_id": manifest["id"],
                    "title": "projected-note",
                    "content": {"note": "should fail"},
                    "kind": "note",
                    "scope": "flow_shared",
                },
            )
            assert projected_publish.status_code == 409

            ack_response = await _ack_manifest_via_api(client, manifest)
            assert ack_response.status_code == 200

            acked_manifests_response = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert acked_manifests_response.status_code == 200
            acked_manifest = next(
                item for item in acked_manifests_response.json() if item["id"] == manifest["id"]
            )

            missing_ack_bundle_response = await client.get(
                f"/internal/flows/{flow_id}/worker-bundle",
                params={
                    "manifest_id": acked_manifest["id"],
                    "manifest_hash": acked_manifest["manifest_hash"],
                    "node_session_key": acked_manifest["node_session_key"],
                },
            )
            assert missing_ack_bundle_response.status_code == 409

            stale_checkpoint_response = await client.post(
                "/internal/flows/checkpoints",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": acked_manifest["flow_node_id"],
                    "node_attempt_id": acked_manifest["node_attempt_id"],
                    **_manifest_binding(acked_manifest),
                    "ack_checkpoint_id": acked_manifest["id"],
                    "sequence_no": 1,
                    "status": "green",
                    "summary": "stale lineage",
                },
            )
            assert stale_checkpoint_response.status_code == 409

            flow_shared_response = await client.post(
                "/internal/flows/context-items",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": acked_manifest["flow_node_id"],
                    "node_attempt_id": acked_manifest["node_attempt_id"],
                    **_manifest_binding(acked_manifest),
                    "title": "operator-note",
                    "content": {"note": "hello world"},
                    "kind": "note",
                    "scope": "flow_shared",
                },
            )
            assert flow_shared_response.status_code == 201
            assert flow_shared_response.json()["metadata"]["inline_content"]["note"] == "hello world"

            node_private_response = await client.post(
                "/internal/flows/context-items",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": acked_manifest["flow_node_id"],
                    "node_attempt_id": acked_manifest["node_attempt_id"],
                    **_manifest_binding(acked_manifest),
                    "title": "node-private-note",
                    "content": {"note": "keep local"},
                    "kind": "note",
                    "scope": "node_private",
                },
            )
            assert node_private_response.status_code == 201

            attempt_scratch_response = await client.post(
                "/internal/flows/context-items",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": acked_manifest["flow_node_id"],
                    "node_attempt_id": acked_manifest["node_attempt_id"],
                    **_manifest_binding(acked_manifest),
                    "title": "attempt-scratch-note",
                    "content": {"note": "ephemeral"},
                    "kind": "note",
                    "scope": "attempt_scratch",
                },
            )
            assert attempt_scratch_response.status_code == 201

            checkpoint_response = await client.post(
                "/internal/flows/checkpoints",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": acked_manifest["flow_node_id"],
                    "node_attempt_id": acked_manifest["node_attempt_id"],
                    **_manifest_binding(acked_manifest),
                    "sequence_no": 1,
                    "status": "green",
                    "summary": "root completed",
                    "payload": {"result": "ok"},
                },
            )
            assert checkpoint_response.status_code == 201

            manifests_after_green = await client.get(f"/internal/flows/{flow_id}/context-manifests")
            assert manifests_after_green.status_code == 200
            projected_manifests = [
                item
                for item in manifests_after_green.json()
                if item["status"] == "projected" and item["id"] != acked_manifest["id"]
            ]
            assert projected_manifests
            next_manifest = projected_manifests[-1]
            required_titles = {
                item["title"] for item in next_manifest["manifest_payload"]["required_items"]
            }
            assert "operator-note" in required_titles
            assert "node-private-note" not in required_titles
            assert "attempt-scratch-note" not in required_titles
            published_item = next(
                item
                for item in next_manifest["manifest_payload"]["required_items"]
                if item["title"] == "operator-note"
            )
            assert published_item["inline_content"]["note"] == "hello world"

            next_bundle_response = await client.get(
                f"/internal/flows/{flow_id}/worker-bundle",
                params=_manifest_binding(next_manifest),
            )
            assert next_bundle_response.status_code == 200
            next_bundle_payload = next_bundle_response.json()
            assert next_bundle_payload["current_manifest"]["id"] == next_manifest["id"]
            assert next_bundle_payload["runtime_container"]["flow_node_id"] == next_manifest["flow_node_id"]
            next_titles = {item["title"] for item in next_bundle_payload["context_items"]}
            assert "operator-note" in next_titles
            assert "node-private-note" not in next_titles
            assert "attempt-scratch-note" not in next_titles
    finally:
        config_module.get_settings.cache_clear()
        app.dependency_overrides.clear()
