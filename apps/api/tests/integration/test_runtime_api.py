from collections.abc import AsyncIterator, Sequence
from typing import Any, cast

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.session import get_db_session
from app.main import app


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


async def _bootstrap_compile_start(client: AsyncClient) -> tuple[str, str, str, str]:
    bootstrap_response = await client.post("/registry/bootstrap")
    assert bootstrap_response.status_code == 200
    bootstrap_payload = bootstrap_response.json()
    assert bootstrap_payload["workflows"] == 4

    compile_response = await client.post("/workflows/default-bugfix/compile")
    assert compile_response.status_code == 201

    compile_payload = compile_response.json()
    compiled_plan_id = compile_payload["id"]
    assert len(compile_payload["nodes"]) == 4

    compiled_plan_read_response = await client.get(f"/workflows/compiled-plans/{compiled_plan_id}")
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


async def test_runtime_control_flow_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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

            manifest_response = await client.get(f"/flows/{flow_id}/context-manifests")
            assert manifest_response.status_code == 200
            manifests_payload = manifest_response.json()
            assert len(manifests_payload) == 1
            manifest_id = manifests_payload[0]["id"]
            assert manifests_payload[0]["status"] == "projected"

            blocked_continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert blocked_continue_response.status_code == 409

            ack_response = await client.post(f"/flows/context-manifests/{manifest_id}/ack")
            assert ack_response.status_code == 200
            ack_payload = ack_response.json()
            assert ack_payload["status"] == "running"
            assert _find_node_state(ack_payload["nodes"], first_flow_node_id) == "running"

            approval_response = await client.post(
                "/approvals",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "reason": "need human confirmation",
                    "request_payload": {"action": "sync"},
                },
            )
            assert approval_response.status_code == 201
            approval_payload = approval_response.json()
            assert approval_payload["status"] == "pending"

            resolve_response = await client.post(
                f"/approvals/{approval_payload['id']}/resolve",
                json={
                    "status": "approved",
                    "resolution_payload": {"by": "tester"},
                },
            )
            assert resolve_response.status_code == 200

            resumed_response = await client.post(f"/flows/{flow_id}/continue")
            assert resumed_response.status_code == 200
            resumed_payload = resumed_response.json()
            assert resumed_payload["status"] == "running"
            assert _find_node_state(resumed_payload["nodes"], first_flow_node_id) == "running"

            checkpoint_response = await client.post(
                "/flows/checkpoints",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "node_attempt_id": resumed_payload["nodes"][0]["current_attempt"]["id"],
                    "sequence_no": 1,
                    "status": "green",
                    "summary": "first node executed",
                    "payload": {"result": "ok"},
                },
            )
            assert checkpoint_response.status_code == 201
            checkpoint_payload = checkpoint_response.json()
            assert checkpoint_payload["status"] == "green"

            post_checkpoint_response = await client.get(f"/flows/{flow_id}")
            assert post_checkpoint_response.status_code == 200
            post_checkpoint_payload = post_checkpoint_response.json()
            assert post_checkpoint_payload["status"] in {"running", "succeeded", "blocked"}
            assert _find_node_state(post_checkpoint_payload["nodes"], first_flow_node_id) == "done"

            next_continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert next_continue_response.status_code == 200
            next_continue_payload = next_continue_response.json()
            assert next_continue_payload["status"] == "blocked"
            waiting_nodes = [
                node for node in next_continue_payload["nodes"] if node["state"] == "waiting"
            ]
            assert waiting_nodes
            assert waiting_nodes[0]["id"] != first_flow_node_id

            next_manifest_response = await client.get(f"/flows/{flow_id}/context-manifests")
            assert next_manifest_response.status_code == 200
            next_manifests_payload = next_manifest_response.json()
            assert len(next_manifests_payload) == 2
            assert any(manifest["status"] == "projected" for manifest in next_manifests_payload)

            cancel_response = await client.post(f"/flows/{flow_id}/cancel")
            assert cancel_response.status_code == 200
            cancel_payload = cancel_response.json()
            assert cancel_payload["status"] == "cancelled"
            paused_nodes = [node for node in cancel_payload["nodes"] if node["state"] == "paused"]
            assert paused_nodes

            checkpoints_response = await client.get(f"/flows/{flow_id}/checkpoints")
            assert checkpoints_response.status_code == 200
            checkpoints_payload = checkpoints_response.json()
            assert len(checkpoints_payload) == 1
            assert checkpoints_payload[0]["summary"] == "first node executed"
    finally:
        app.dependency_overrides.clear()


async def _advance_flow_node_via_api(
    client: AsyncClient,
    *,
    flow_id: str,
    expected_node_key: str,
) -> None:
    continue_response = await client.post(f"/flows/{flow_id}/continue")
    assert continue_response.status_code == 200
    assert continue_response.json()["status"] == "blocked"

    manifests_response = await client.get(f"/flows/{flow_id}/context-manifests")
    assert manifests_response.status_code == 200
    projected_manifest = next(
        manifest for manifest in manifests_response.json() if manifest["status"] == "projected"
    )

    inspect_response = await client.get(f"/flows/{flow_id}")
    assert inspect_response.status_code == 200
    inspect_payload = inspect_response.json()
    projected_node = _find_node(inspect_payload["nodes"], projected_manifest["flow_node_id"])
    assert projected_node is not None
    assert projected_node["node_key"] == expected_node_key

    ack_response = await client.post(f"/flows/context-manifests/{projected_manifest['id']}/ack")
    assert ack_response.status_code == 200
    ack_payload = ack_response.json()
    running_node = _find_node(ack_payload["nodes"], projected_manifest["flow_node_id"])
    assert running_node is not None
    assert running_node["state"] == "running"
    assert running_node["current_attempt"] is not None

    checkpoint_response = await client.post(
        "/flows/checkpoints",
        json={
            "flow_id": flow_id,
            "flow_node_id": projected_manifest["flow_node_id"],
            "node_attempt_id": running_node["current_attempt"]["id"],
            "sequence_no": 1,
            "status": "green",
            "summary": f"{expected_node_key} done",
            "payload": {"node": expected_node_key},
        },
    )
    assert checkpoint_response.status_code == 201


async def test_rejected_approval_fails_flow_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            (
                flow_id,
                _revision_id,
                first_flow_node_id,
                _compiled_plan_id,
            ) = await _bootstrap_compile_start(client)

            continue_response = await client.post(f"/flows/{flow_id}/continue")
            assert continue_response.status_code == 200

            manifest_response = await client.get(f"/flows/{flow_id}/context-manifests")
            assert manifest_response.status_code == 200
            manifests_payload = manifest_response.json()
            assert len(manifests_payload) == 1

            ack_response = await client.post(
                f"/flows/context-manifests/{manifests_payload[0]['id']}/ack"
            )
            assert ack_response.status_code == 200

            approval_response = await client.post(
                "/approvals",
                json={
                    "flow_id": flow_id,
                    "flow_node_id": first_flow_node_id,
                    "reason": "operator rejection path",
                    "request_payload": {"action": "review"},
                },
            )
            assert approval_response.status_code == 201
            approval_id = approval_response.json()["id"]

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

            continue_after_reject = await client.post(f"/flows/{flow_id}/continue")
            assert continue_after_reject.status_code == 409
    finally:
        app.dependency_overrides.clear()


async def test_ack_missing_context_manifest_returns_404_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/flows/context-manifests/00000000-0000-0000-0000-000000000000/ack"
            )
            assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_flow_operator_read_models_and_pause_retry_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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
            assert len(operator_payload["manifests"]) == 1
            assert operator_payload["manifests"][0]["status"] == "projected"
            assert len(operator_payload["sessions"]) == 1
            assert operator_payload["sessions"][0]["status"] == "idle"

            manifests_response = await client.get(f"/flows/{flow_id}/context-manifests")
            manifest_id = manifests_response.json()[0]["id"]

            pause_response = await client.post(f"/flows/{flow_id}/pause")
            assert pause_response.status_code == 200
            pause_payload = pause_response.json()
            assert pause_payload["flow"]["status"] == "paused"
            assert first_flow_node_id in pause_payload["paused_node_ids"]

            continue_after_pause = await client.post(f"/flows/{flow_id}/continue")
            assert continue_after_pause.status_code == 409

            ack_after_pause = await client.post(f"/flows/context-manifests/{manifest_id}/ack")
            assert ack_after_pause.status_code == 409

            (
                retry_flow_id,
                _retry_revision_id,
                retry_flow_node_id,
                _retry_compiled_plan_id,
            ) = await _bootstrap_compile_start(client)
            retry_first_continue = await client.post(f"/flows/{retry_flow_id}/continue")
            assert retry_first_continue.status_code == 200

            retry_manifests_response = await client.get(f"/flows/{retry_flow_id}/context-manifests")
            retry_manifest_id = retry_manifests_response.json()[0]["id"]
            retry_ack_response = await client.post(
                f"/flows/context-manifests/{retry_manifest_id}/ack"
            )
            assert retry_ack_response.status_code == 200

            retry_checkpoint_response = await client.post(
                "/flows/checkpoints",
                json={
                    "flow_id": retry_flow_id,
                    "flow_node_id": retry_flow_node_id,
                    "node_attempt_id": (
                        retry_ack_response.json()["nodes"][0]["current_attempt"]["id"]
                    ),
                    "sequence_no": 1,
                    "status": "blocked",
                    "summary": "operator asked to retry",
                    "payload": {"result": "retry-soon"},
                    "recommended_next_action": "retry",
                    "wait_reason": "operator",
                },
            )
            assert retry_checkpoint_response.status_code == 201

            retry_response = await client.post(
                f"/flows/{retry_flow_id}/nodes/{retry_flow_node_id}/retry"
            )
            assert retry_response.status_code == 200
            retry_payload = retry_response.json()
            assert retry_payload["flow"]["status"] == "blocked"
            assert (
                retry_payload["retried_node_attempt_id"]
                != retry_ack_response.json()["nodes"][0]["current_attempt"]["id"]
            )

            operator_after_retry = await client.get(f"/flows/{retry_flow_id}/operator")
            assert operator_after_retry.status_code == 200
            retry_attempts = [
                attempt
                for attempt in operator_after_retry.json()["attempts"]
                if attempt["flow_node_id"] == retry_flow_node_id
            ]
            assert len(retry_attempts) == 2
    finally:
        app.dependency_overrides.clear()


async def test_max_complexity_workflow_runs_to_completion_via_api(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            bootstrap_response = await client.post("/registry/bootstrap")
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
