from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import autoclaw.interfaces.http.routers.control as control_router_module
import autoclaw.interfaces.http.routers.tasks as tasks_router_module
import httpx
import pytest
from autoclaw.main import create_app
from autoclaw.persistence.session import get_db_session
from autoclaw.runtime.contracts import (
    FlowStatus,
    HumanRequestResolution,
    HumanRequestResolutionKind,
    HumanRequestResolutionSurface,
    HumanRequestResolveResponse,
    TaskStartResponse,
    WorkflowManifestRef,
)
from sqlalchemy.ext.asyncio import AsyncSession

_API_HEADERS = {"X-AutoClaw-API-Key": "autoclaw-operator-test-key"}


async def _fake_session() -> AsyncIterator[AsyncSession]:
    yield cast(AsyncSession, object())


async def test_task_start_route_injects_app_owned_effect_publishers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(should_enable_mcp_mounts=False)
    app.dependency_overrides[get_db_session] = _fake_session
    captured: dict[str, object] = {}

    async def fake_start_task(
        request: object,
        *,
        data_dir: Path | None = None,
        session: AsyncSession | None = None,
        runtime_effect_publisher: object = None,
        support_projection_publisher: object = None,
    ) -> TaskStartResponse:
        del request, data_dir, session
        captured["runtime"] = runtime_effect_publisher
        captured["projection"] = support_projection_publisher
        return TaskStartResponse(
            task_id="task.http-injection",
            compiled_plan_id="compiled-plan.task.http-injection",
            active_flow_revision_id="flow-revision.http-injection.1",
            flow_status=FlowStatus.RUNNING,
            workflow_manifest_ref=WorkflowManifestRef(
                path=Path("_runtime/workflow-manifest.md"),
                description="Committed workflow manifest support projection.",
            ),
        )

    monkeypatch.setattr(
        tasks_router_module,
        "start_task_from_definition",
        fake_start_task,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/tasks/start",
            headers=_API_HEADERS,
            json={
                "task": {
                    "key": "http-injection",
                    "title": "HTTP publisher injection",
                    "summary": "Keep task-start effects explicit.",
                },
                "workflow": {"key": "bounded-change"},
            },
        )

    assert response.status_code == 200
    assert captured == {
        "runtime": app.state.runtime_effect_publisher,
        "projection": app.state.support_projection_publisher,
    }


async def test_human_resolution_route_injects_app_owned_runtime_publisher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(should_enable_mcp_mounts=False)
    app.dependency_overrides[get_db_session] = _fake_session
    captured: dict[str, object] = {}

    async def fake_resolve_human_request(
        session: AsyncSession,
        *,
        task_id: str,
        request_id: str,
        request: object,
        actor_ref: str | None = None,
        resolved_by_surface: object = None,
        runtime_effect_publisher: object = None,
    ) -> HumanRequestResolveResponse:
        del session, request, resolved_by_surface
        captured["runtime"] = runtime_effect_publisher
        captured["actor_ref"] = actor_ref
        return HumanRequestResolveResponse(
            task_id=task_id,
            resolution=HumanRequestResolution(
                request_id=request_id,
                task_id=task_id,
                resolution_kind=HumanRequestResolutionKind.ANSWERED,
                item_responses={"direction": "a"},
                policy_basis={"policy_basis": "test"},
                summary="Human answered the controller-owned request.",
                resolved_at=datetime.now(UTC),
                resolved_by_actor_ref=actor_ref,
                resolved_by_surface=HumanRequestResolutionSurface.CONTROL_API,
            ),
        )

    monkeypatch.setattr(
        control_router_module,
        "resolve_human_request",
        fake_resolve_human_request,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/control/tasks/task.http-injection/human-requests/request.http-injection/resolve",
            headers={**_API_HEADERS, "X-AutoClaw-Actor-Ref": "operator.http"},
            json={"item_responses": {"direction": "a"}},
        )

    assert response.status_code == 200
    assert captured == {
        "runtime": app.state.runtime_effect_publisher,
        "actor_ref": "operator.http",
    }
