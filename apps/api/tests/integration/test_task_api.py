from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.models.runtime import TaskCompose, TaskResourceBinding
from app.db.session import get_db_session
from app.main import app
from tests.helpers import internal_api_key_headers


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


async def test_create_task_bootstraps_compose_and_default_bindings(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            response = await client.post(
                "/internal/tasks",
                json={
                    "title": "Upload demo",
                    "description": "Create a task with bootstrap resources",
                    "input_payload": {"topic": "demo"},
                },
            )
        assert response.status_code == 201
        payload = response.json()
        task_id = UUID(payload["id"])

        session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False, autoflush=False)
        async with session_factory() as session:
            task_compose = await session.scalar(select(TaskCompose).where(TaskCompose.task_id == task_id))
            assert task_compose is not None
            assert task_compose.status == "ready"
            assert task_compose.context_root_uri == f"task://{task_id}/context"
            assert task_compose.workspace_root_uri == f"task://{task_id}/workspace"
            assert task_compose.manifest_root_uri == f"task://{task_id}/manifests"
            assert Path(task_compose.metadata_["materialized_paths"]["context"]).exists()

            bindings = list(
                (
                    await session.scalars(
                        select(TaskResourceBinding).where(TaskResourceBinding.task_id == task_id)
                    )
                ).all()
            )
            binding_roles = {binding.binding_role.value for binding in bindings}
            assert {"primary_workspace", "primary_context", "manifest_root"} <= binding_roles
    finally:
        app.dependency_overrides.clear()


async def test_upload_task_file_materializes_into_task_owned_context(test_engine: AsyncEngine) -> None:
    _set_db_override(test_engine)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            create_response = await client.post(
                "/internal/tasks",
                json={
                    "title": "Upload demo",
                    "description": "Upload files into task bindings",
                },
            )
            assert create_response.status_code == 201
            task_id = create_response.json()["id"]

            upload_response = await client.post(
                f"/internal/tasks/{task_id}/uploads",
                data={
                    "target_slot": "context_docs",
                    "relative_path": "incoming/brief.txt",
                },
                files={"file": ("brief.txt", b"hello task context", "text/plain")},
            )
        assert upload_response.status_code == 201
        payload = upload_response.json()
        assert payload["target_slot"] == "context_docs"
        assert payload["relative_path"] == "incoming/brief.txt"
        assert payload["size_bytes"] == len(b"hello task context")

        session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False, autoflush=False)
        async with session_factory() as session:
            task_compose = await session.scalar(
                select(TaskCompose).where(TaskCompose.task_id == UUID(task_id))
            )
            assert task_compose is not None
            context_path = (
                Path(task_compose.metadata_["materialized_paths"]["context"]) / "incoming/brief.txt"
            )
            assert context_path.read_text() == "hello task context"
    finally:
        app.dependency_overrides.clear()
