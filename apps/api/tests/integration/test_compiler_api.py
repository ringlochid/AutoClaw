from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DefinitionVersionStatus
from app.db.models.registry import WorkflowDefinition, WorkflowVersion
from app.db.session import get_db_session
from app.main import app
from app.services.registry_service import bootstrap_registry
from tests.helpers import internal_api_key_headers, operator_api_key_headers


def _set_db_override(db_session: AsyncSession) -> None:
    async def override_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session


async def _insert_workflow_version(
    db_session: AsyncSession,
    *,
    key: str,
    content: dict[str, Any],
) -> None:
    definition = WorkflowDefinition(key=key, description=content.get("description"))
    db_session.add(definition)
    await db_session.flush()

    db_session.add(
        WorkflowVersion(
            workflow_definition_id=definition.id,
            version=1,
            status=DefinitionVersionStatus.PUBLISHED,
            description=content.get("description"),
            content=content,
            published_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    await db_session.commit()


async def test_compile_missing_workflow_returns_404(db_session: AsyncSession) -> None:
    _set_db_override(db_session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            compile_response = await client.post("/internal/workflows/missing-workflow/compile")
            assert compile_response.status_code == 404
            assert compile_response.json() == {
                "detail": "No published workflow version found for 'missing-workflow'"
            }

            client.headers.update(operator_api_key_headers())
            start_response = await client.post(
                "/tasks/composes/start",
                json={
                    "metadata": {"title": "missing workflow", "description": "route error mapping"},
                    "workflow": {"key": "missing-workflow"},
                    "input": {},
                    "roots": {"workspace": True, "context": True, "manifests": True},
                    "context_refs": [],
                    "skill_dependencies": [],
                },
            )
            assert start_response.status_code == 404
            assert start_response.json() == {
                "detail": "No published workflow version found for 'missing-workflow'"
            }
    finally:
        app.dependency_overrides.clear()


async def test_compile_invalid_workflow_returns_422(db_session: AsyncSession) -> None:
    await bootstrap_registry(db_session, publish=True)
    await db_session.commit()
    await _insert_workflow_version(
        db_session,
        key="bad-edge",
        content={
            "id": "bad-edge",
            "description": "invalid edge target",
            "nodes": [
                {
                    "id": "root",
                    "role": "planner-supervisor",
                    "mode": "plan",
                }
            ],
            "edges": [
                {
                    "from": "root",
                    "to": "missing-node",
                }
            ],
            "skill_refs": [],
        },
    )

    _set_db_override(db_session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            compile_response = await client.post("/internal/workflows/bad-edge/compile")
            assert compile_response.status_code == 422
            assert compile_response.json() == {
                "detail": "Edge target 'missing-node' does not exist"
            }

            client.headers.update(operator_api_key_headers())
            start_response = await client.post(
                "/tasks/composes/start",
                json={
                    "metadata": {"title": "bad workflow", "description": "route error mapping"},
                    "workflow": {"key": "bad-edge"},
                    "input": {},
                    "roots": {"workspace": True, "context": True, "manifests": True},
                    "context_refs": [],
                    "skill_dependencies": [],
                },
            )
            assert start_response.status_code == 422
            assert start_response.json() == {"detail": "Edge target 'missing-node' does not exist"}
    finally:
        app.dependency_overrides.clear()


async def test_compile_malformed_workflow_content_returns_422(db_session: AsyncSession) -> None:
    await _insert_workflow_version(
        db_session,
        key="bad-shape",
        content={
            "id": "bad-shape",
            "description": "malformed workflow",
            "nodes": "not-a-list",
            "edges": [],
            "skill_refs": [],
        },
    )

    _set_db_override(db_session)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            compile_response = await client.post("/internal/workflows/bad-shape/compile")
            assert compile_response.status_code == 422
            assert "Invalid workflow definition content:" in compile_response.json()["detail"]

            client.headers.update(operator_api_key_headers())
            start_response = await client.post(
                "/tasks/composes/start",
                json={
                    "metadata": {
                        "title": "bad workflow shape",
                        "description": "route error mapping",
                    },
                    "workflow": {"key": "bad-shape"},
                    "input": {},
                    "roots": {"workspace": True, "context": True, "manifests": True},
                    "context_refs": [],
                    "skill_dependencies": [],
                },
            )
            assert start_response.status_code == 422
            assert "Invalid workflow definition content:" in start_response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
