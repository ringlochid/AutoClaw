from __future__ import annotations

from collections.abc import AsyncIterator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.session import get_db_session
from app.main import app
from tests.helpers import (
    definition_write_audit_headers,
    internal_api_key_headers,
    public_api_key_headers,
)


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


async def test_internal_registry_snapshot_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            bootstrap_response = await client.post("/internal/registry/bootstrap")
            assert bootstrap_response.status_code == 200

            snapshot_response = await client.get("/internal/registry/snapshot")
            assert snapshot_response.status_code == 200
            snapshot = snapshot_response.json()
            assert snapshot["roles"]
            assert snapshot["policies"]
            assert snapshot["workflows"]
            assert snapshot["skills"]
    finally:
        app.dependency_overrides.clear()


async def test_registry_workflow_authoring_round_trip_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as internal_client:
            bootstrap_response = await internal_client.post("/internal/registry/bootstrap")
            assert bootstrap_response.status_code == 200

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=public_api_key_headers(),
        ) as client:
            draft_seed = {
                "id": "operator-registry-smoke",
                "description": "Operator registry smoke workflow",
                "defaults": {
                    "metadata": {"goal": "smoke-test"},
                    "skill_refs": [
                        {
                            "provider": "openclaw",
                            "key": "contract-checker",
                            "state": "required",
                        }
                    ],
                },
                "nodes": [
                    {
                        "id": "root",
                        "role": "planner-supervisor",
                        "mode": "plan",
                        "description": "Plan the fix",
                        "metadata": {"lane": "root"},
                    },
                    {
                        "id": "root.execute",
                        "role": "main-loop-worker",
                        "mode": "persistent_execute",
                        "description": "Execute the plan",
                    },
                ],
                "edges": [{"from": "root", "to": "root.execute"}],
            }

            validate_response = await client.post("/registry/workflows/validate", json=draft_seed)
            assert validate_response.status_code == 200
            normalized_plan = validate_response.json()["normalized_plan"]
            assert normalized_plan["nodes"][0]["effective_payload"]["metadata"] == {
                "replan_style": "balanced",
                "prefers_local_retry_first": True,
                "goal": "smoke-test",
                "lane": "root",
            }

            put_response = await client.put(
                "/registry/workflows/operator-registry-smoke/draft",
                params={"expected_draft_version": 0},
                json=draft_seed,
            )
            assert put_response.status_code == 201
            draft_payload = put_response.json()
            assert draft_payload["status"] == "draft"
            assert draft_payload["version"] == 1

            list_response = await client.get("/registry/workflows")
            assert list_response.status_code == 200
            summaries = {item["key"]: item for item in list_response.json()}
            assert summaries["operator-registry-smoke"]["draft_version"] == 1
            assert summaries["operator-registry-smoke"]["published_version"] is None

            versions_response = await client.get(
                "/registry/workflows/operator-registry-smoke/versions"
            )
            assert versions_response.status_code == 200
            versions_payload = versions_response.json()
            assert [item["version"] for item in versions_payload] == [1]
            assert versions_payload[0]["status"] == "draft"

            stale_draft_response = await client.put(
                "/registry/workflows/operator-registry-smoke/draft",
                params={"expected_draft_version": 0},
                json=draft_seed,
            )
            assert stale_draft_response.status_code == 409

            publish_response = await client.post(
                "/registry/workflows/operator-registry-smoke/versions/1/publish",
                params={"expected_published_version": 0},
            )
            assert publish_response.status_code == 200
            published_payload = publish_response.json()
            assert published_payload["status"] == "published"
            assert published_payload["version"] == 1

            published_versions_response = await client.get(
                "/registry/workflows/operator-registry-smoke/versions"
            )
            assert published_versions_response.status_code == 200
            assert published_versions_response.json()[0]["status"] == "published"

            next_draft_response = await client.put(
                "/registry/workflows/operator-registry-smoke/draft",
                params={"expected_draft_version": 0},
                json=draft_seed,
            )
            assert next_draft_response.status_code == 201
            assert next_draft_response.json()["status"] == "draft"
            assert next_draft_response.json()["version"] == 2

            stale_publish_response = await client.post(
                "/registry/workflows/operator-registry-smoke/versions/1/publish",
                params={"expected_published_version": 0},
            )
            assert stale_publish_response.status_code == 409
    finally:
        app.dependency_overrides.clear()


async def test_registry_workflow_internal_write_routes_capture_audit_metadata(
    test_engine: AsyncEngine,
) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as internal_client:
            bootstrap_response = await internal_client.post("/internal/registry/bootstrap")
            assert bootstrap_response.status_code == 200

            draft_seed = {
                "id": "operator-registry-audit",
                "description": "Operator registry audit workflow",
                "nodes": [
                    {
                        "id": "root",
                        "role": "planner-supervisor",
                        "mode": "plan",
                        "description": "Plan the audited change",
                    }
                ],
                "edges": [],
            }
            audit_headers = {
                **internal_api_key_headers(),
                **definition_write_audit_headers(
                    requested_by="orin/operator",
                    source_session="telegram:5528907529",
                    source_agent="orin",
                    source_node_attempt="attempt-123",
                    reason="promote audited registry change",
                ),
            }

            put_response = await internal_client.put(
                "/internal/registry/workflows/operator-registry-audit/draft",
                params={"expected_draft_version": 0},
                headers=audit_headers,
                json=draft_seed,
            )
            assert put_response.status_code == 201
            draft_payload = put_response.json()
            assert draft_payload["requested_by"] == "orin/operator"
            assert draft_payload["audit"] == {
                "actor": "orin/operator",
                "source_session": "telegram:5528907529",
                "source_agent": "orin",
                "source_node_attempt": "attempt-123",
                "reason": "promote audited registry change",
            }

            publish_response = await internal_client.post(
                "/internal/registry/workflows/operator-registry-audit/versions/1/publish",
                params={"expected_published_version": 0},
                headers={
                    **audit_headers,
                    **definition_write_audit_headers(
                        requested_by="orin/operator",
                        source_session="telegram:5528907529",
                        source_agent="orin",
                        source_node_attempt="attempt-123",
                        reason="publish audited registry change",
                    ),
                },
            )
            assert publish_response.status_code == 200
            published_payload = publish_response.json()
            assert published_payload["status"] == "published"
            assert published_payload["requested_by"] == "orin/operator"
            assert published_payload["audit"]["reason"] == "publish audited registry change"

            versions_response = await internal_client.get(
                "/registry/workflows/operator-registry-audit/versions"
            )
            assert versions_response.status_code == 200
            versions_payload = versions_response.json()
            assert versions_payload[0]["requested_by"] == "orin/operator"
            assert versions_payload[0]["audit"]["source_node_attempt"] == "attempt-123"
            assert versions_payload[0]["audit"]["reason"] == "publish audited registry change"
    finally:
        app.dependency_overrides.clear()


async def test_registry_role_cas_round_trip_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as internal_client:
            bootstrap_response = await internal_client.post("/internal/registry/bootstrap")
            assert bootstrap_response.status_code == 200

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=public_api_key_headers(),
        ) as client:
            draft_seed = {
                "id": "operator-role-smoke",
                "kind": "worker",
                "description": "Operator role smoke test",
                "allowed_modes": ["review"],
                "default_policy": "default",
                "checkpoint_schema": "review_result_v1",
            }

            put_response = await client.put(
                "/registry/roles/operator-role-smoke/draft",
                params={"expected_draft_version": 0},
                json=draft_seed,
            )
            assert put_response.status_code == 201
            assert put_response.json()["version"] == 1

            stale_draft_response = await client.put(
                "/registry/roles/operator-role-smoke/draft",
                params={"expected_draft_version": 0},
                json=draft_seed,
            )
            assert stale_draft_response.status_code == 409

            publish_response = await client.post(
                "/registry/roles/operator-role-smoke/versions/1/publish",
                params={"expected_published_version": 0},
            )
            assert publish_response.status_code == 200
            assert publish_response.json()["status"] == "published"

            next_draft_response = await client.put(
                "/registry/roles/operator-role-smoke/draft",
                params={"expected_draft_version": 0},
                json=draft_seed,
            )
            assert next_draft_response.status_code == 201
            assert next_draft_response.json()["status"] == "draft"
            assert next_draft_response.json()["version"] == 2

            stale_publish_response = await client.post(
                "/registry/roles/operator-role-smoke/versions/1/publish",
                params={"expected_published_version": 0},
            )
            assert stale_publish_response.status_code == 409
    finally:
        app.dependency_overrides.clear()


async def test_registry_policy_cas_round_trip_via_api(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as internal_client:
            bootstrap_response = await internal_client.post("/internal/registry/bootstrap")
            assert bootstrap_response.status_code == 200

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=public_api_key_headers(),
        ) as client:
            draft_seed = {
                "id": "operator-policy-smoke",
                "description": "Operator policy smoke test",
                "rules": {"allow": True},
            }

            put_response = await client.put(
                "/registry/policies/operator-policy-smoke/draft",
                params={"expected_draft_version": 0},
                json=draft_seed,
            )
            assert put_response.status_code == 201
            assert put_response.json()["version"] == 1

            stale_draft_response = await client.put(
                "/registry/policies/operator-policy-smoke/draft",
                params={"expected_draft_version": 0},
                json=draft_seed,
            )
            assert stale_draft_response.status_code == 409

            publish_response = await client.post(
                "/registry/policies/operator-policy-smoke/versions/1/publish",
                params={"expected_published_version": 0},
            )
            assert publish_response.status_code == 200
            assert publish_response.json()["status"] == "published"

            next_draft_response = await client.put(
                "/registry/policies/operator-policy-smoke/draft",
                params={"expected_draft_version": 0},
                json=draft_seed,
            )
            assert next_draft_response.status_code == 201
            assert next_draft_response.json()["status"] == "draft"
            assert next_draft_response.json()["version"] == 2

            stale_publish_response = await client.post(
                "/registry/policies/operator-policy-smoke/versions/1/publish",
                params={"expected_published_version": 0},
            )
            assert stale_publish_response.status_code == 409
    finally:
        app.dependency_overrides.clear()
