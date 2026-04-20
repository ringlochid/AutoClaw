from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

import anyio
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.models.runtime import TaskCompose, TaskResourceBinding
from app.db.session import get_db_session
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


async def test_create_task_bootstraps_compose_and_default_bindings(
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

        session_factory = async_sessionmaker(
            bind=test_engine, expire_on_commit=False, autoflush=False
        )
        async with session_factory() as session:
            task_compose = await session.scalar(
                select(TaskCompose).where(TaskCompose.task_id == task_id)
            )
            assert task_compose is not None
            assert task_compose.status == "ready"
            assert task_compose.context_root_uri == f"task://{task_id}/context"
            assert task_compose.workspace_root_uri == f"task://{task_id}/workspace"
            assert task_compose.manifest_root_uri == f"task://{task_id}/manifests"
            context_path = task_compose.metadata_["materialized_paths"]["context"]
            assert await anyio.Path(context_path).exists()

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


async def test_upload_task_file_materializes_into_task_owned_context(
    test_engine: AsyncEngine,
) -> None:
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

        session_factory = async_sessionmaker(
            bind=test_engine, expire_on_commit=False, autoflush=False
        )
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


async def test_upload_task_file_rejects_symlink_escape_from_task_root(
    test_engine: AsyncEngine,
    tmp_path: Path,
) -> None:
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
                    "description": "Reject symlink escapes",
                },
            )
            assert create_response.status_code == 201
            task_id = UUID(create_response.json()["id"])

        session_factory = async_sessionmaker(
            bind=test_engine, expire_on_commit=False, autoflush=False
        )
        async with session_factory() as session:
            task_compose = await session.scalar(
                select(TaskCompose).where(TaskCompose.task_id == task_id)
            )
            assert task_compose is not None
            context_root = Path(task_compose.metadata_["materialized_paths"]["context"])

        escape_root = tmp_path / "escaped"
        escape_root.mkdir(parents=True)
        (context_root / "incoming").symlink_to(escape_root, target_is_directory=True)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as client:
            upload_response = await client.post(
                f"/internal/tasks/{task_id}/uploads",
                data={
                    "target_slot": "context_docs",
                    "relative_path": "incoming/brief.txt",
                },
                files={"file": ("brief.txt", b"hello task context", "text/plain")},
            )

        assert upload_response.status_code == 400
        assert "escapes the task-owned root" in upload_response.json()["detail"]
        assert not (escape_root / "brief.txt").exists()
    finally:
        app.dependency_overrides.clear()


async def test_upload_refresh_preserves_task_compose_launch_binding_and_dependencies(
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

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=operator_api_key_headers(),
        ) as operator_client:
            start_response = await operator_client.post(
                "/tasks/composes/start",
                json={
                    "metadata": {
                        "key": "preserve-compose",
                        "title": "Preserve compose launch state",
                        "description": "Task compose start",
                        "labels": {"kind": "bugfix", "priority": "urgent"},
                    },
                    "workflow": {"key": "default-bugfix"},
                    "input": {"repo": "acme/webapp", "issue": "UPLOAD-999"},
                    "roots": {"workspace": True, "context": True, "manifests": True},
                    "context_refs": ["repo://acme/webapp", "file://uploads/log.txt"],
                    "skill_dependencies": [
                        {
                            "key": "contract-checker",
                            "runtime_name": "autoclaw-contract-checker",
                            "required": True,
                        }
                    ],
                },
            )
            assert start_response.status_code == 201
            task_id = start_response.json()["task"]["id"]

        session_factory = async_sessionmaker(
            bind=test_engine, expire_on_commit=False, autoflush=False
        )
        async with session_factory() as session:
            original_task_compose = await session.scalar(
                select(TaskCompose).where(TaskCompose.task_id == UUID(task_id))
            )
            assert original_task_compose is not None
            original_workflow_version_id = original_task_compose.workflow_version_id
            original_compiled_plan_id = original_task_compose.compiled_plan_id
            original_entrypoint = original_task_compose.entrypoint

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=internal_api_key_headers(),
        ) as internal_client:
            upload_response = await internal_client.post(
                f"/internal/tasks/{task_id}/uploads",
                data={
                    "target_slot": "context_docs",
                    "relative_path": "incoming/brief.txt",
                },
                files={"file": ("brief.txt", b"preserve compose", "text/plain")},
            )
            assert upload_response.status_code == 201

        session_factory = async_sessionmaker(
            bind=test_engine, expire_on_commit=False, autoflush=False
        )
        async with session_factory() as session:
            task_compose = await session.scalar(
                select(TaskCompose).where(TaskCompose.task_id == UUID(task_id))
            )
            assert task_compose is not None
            assert task_compose.workflow_version_id == original_workflow_version_id
            assert task_compose.compiled_plan_id == original_compiled_plan_id
            assert task_compose.entrypoint == original_entrypoint
            assert task_compose.context_refs == [
                "repo://acme/webapp",
                "file://uploads/log.txt",
            ]
            assert task_compose.skill_dependencies[0]["runtime_name"] == (
                "autoclaw-contract-checker"
            )
            assert task_compose.metadata_["labels"] == {
                "kind": "bugfix",
                "priority": "urgent",
            }
    finally:
        app.dependency_overrides.clear()


async def test_start_task_compose_rejects_unsupported_workflow_entrypoint(
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

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=operator_api_key_headers(),
        ) as client:
            start_response = await client.post(
                "/tasks/composes/start",
                json={
                    "metadata": {
                        "key": "entrypoint-reject",
                        "title": "Reject unsupported entrypoint",
                        "description": "Task compose start",
                    },
                    "workflow": {"key": "default-bugfix", "entrypoint": "root.discovery"},
                    "input": {"repo": "acme/webapp", "issue": "ENTRYPOINT-1"},
                    "roots": {"workspace": True, "context": True, "manifests": True},
                    "context_refs": [],
                    "skill_dependencies": [],
                },
            )

        assert start_response.status_code == 422
        assert "workflow.entrypoint is not supported yet" in start_response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("roots", "expected_roles"),
    [
        (
            {"workspace": False, "context": False, "manifests": False},
            set(),
        ),
        (
            {"workspace": False, "context": True, "manifests": False},
            {"primary_context"},
        ),
        (
            {"workspace": True, "context": False, "manifests": True},
            {"primary_workspace", "manifest_root"},
        ),
    ],
)
async def test_start_task_compose_respects_roots_matrix(
    test_engine: AsyncEngine,
    roots: dict[str, bool],
    expected_roles: set[str],
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

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=operator_api_key_headers(),
        ) as client:
            start_response = await client.post(
                "/tasks/composes/start",
                json={
                    "metadata": {
                        "key": (
                            f"roots-{int(roots['workspace'])}"
                            f"{int(roots['context'])}"
                            f"{int(roots['manifests'])}"
                        ),
                        "title": "Roots matrix",
                        "description": "Task compose start",
                    },
                    "workflow": {"key": "default-bugfix"},
                    "input": {"repo": "acme/webapp", "issue": "ROOTS-1"},
                    "roots": roots,
                    "context_refs": [],
                    "skill_dependencies": [],
                },
            )
            assert start_response.status_code == 201
            task_id = UUID(start_response.json()["task"]["id"])

        session_factory = async_sessionmaker(
            bind=test_engine, expire_on_commit=False, autoflush=False
        )
        async with session_factory() as session:
            bindings = list(
                (
                    await session.scalars(
                        select(TaskResourceBinding).where(TaskResourceBinding.task_id == task_id)
                    )
                ).all()
            )
            roles = {binding.binding_role.value for binding in bindings}
            assert roles == expected_roles
    finally:
        app.dependency_overrides.clear()


async def test_start_task_compose_route_materializes_task_and_flow(
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

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=operator_api_key_headers(),
        ) as client:
            start_response = await client.post(
                "/tasks/composes/start",
                json={
                    "metadata": {
                        "key": "fix-upload-flow",
                        "title": "Fix upload flow regression",
                        "description": "Task compose start",
                    },
                    "workflow": {"key": "default-bugfix"},
                    "input": {"repo": "acme/webapp", "issue": "UPLOAD-421"},
                    "roots": {"workspace": True, "context": True, "manifests": True},
                    "context_refs": ["repo://acme/webapp", "file://uploads/auth-refresh.log"],
                    "skill_dependencies": [
                        {
                            "key": "contract-checker",
                            "runtime_name": "autoclaw-contract-checker",
                            "required": True,
                        }
                    ],
                },
            )
            assert start_response.status_code == 201
            payload = start_response.json()
            assert payload["task"]["title"] == "Fix upload flow regression"
            assert payload["task_compose"]["context_refs"] == [
                "repo://acme/webapp",
                "file://uploads/auth-refresh.log",
            ]
            assert payload["task_compose"]["skill_dependencies"][0]["runtime_name"] == (
                "autoclaw-contract-checker"
            )
            assert payload["flow_id"]
            assert payload["active_flow_revision_id"]
    finally:
        app.dependency_overrides.clear()
