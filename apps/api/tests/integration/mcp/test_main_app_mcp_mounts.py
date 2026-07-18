from __future__ import annotations

from collections.abc import Mapping

import autoclaw.main as main_module
import autoclaw.runtime.node_operations.executor as executor_module
import httpx
import pytest
from autoclaw.main import create_app
from autoclaw.runtime.node_mcp import DispatchMcpBindingRegistry
from autoclaw.runtime.node_operations import NodeOperationName
from starlette.routing import Mount

_INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "autoclaw-main-mount-test", "version": "1"},
    },
}
_MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def test_sync_app_construction_defers_loop_scoped_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_resolved_during_construction() -> None:
        raise AssertionError("session factory resolved before async Node operation")

    monkeypatch.setattr(
        executor_module,
        "get_session_factory",
        fail_if_resolved_during_construction,
    )

    app = create_app(should_enable_mcp_mounts=True)

    assert isinstance(app.state.dispatch_mcp_binding_registry, DispatchMcpBindingRegistry)
    assert len(app.state.mcp_lifespan_apps) == 3


async def _post_initialize(
    client: httpx.AsyncClient,
    path: str,
    *,
    headers: Mapping[str, str] | None = None,
) -> httpx.Response:
    return await client.post(
        path,
        headers={**_MCP_HEADERS, **dict(headers or {})},
        json=_INITIALIZE_REQUEST,
    )


async def test_main_app_mounts_one_managed_and_one_compatibility_node_mcp_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    startup_calls: list[str] = []

    async def ensure_schema() -> None:
        startup_calls.append("schema")

    async def dispose_engine() -> None:
        startup_calls.append("dispose")

    monkeypatch.setattr(main_module, "ensure_database_schema", ensure_schema)
    monkeypatch.setattr(main_module, "dispose_db_engine", dispose_engine)

    app = create_app(should_enable_mcp_mounts=True)
    registry = app.state.dispatch_mcp_binding_registry
    assert isinstance(registry, DispatchMcpBindingRegistry)
    issued = registry.issue_binding(
        task_id="task.main-managed-mount",
        dispatch_id="dispatch.main-managed-mount",
        provider_start_revision=0,
        exposure_ceiling=(NodeOperationName.GET_CURRENT_CONTEXT,),
    )

    mounts = {route.path: route.app for route in app.routes if isinstance(route, Mount)}
    assert {"/operator", "/_internal/node", "/node"} <= set(mounts)
    assert len({id(mounts["/_internal/node"]), id(mounts["/node"])}) == 2
    assert app.state.mcp_lifespan_apps == (
        mounts["/operator"],
        mounts["/_internal/node"],
        mounts["/node"],
    )

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 43125)),
            base_url="http://127.0.0.1",
        ) as client:
            operator = await _post_initialize(
                client,
                "/operator/mcp",
                headers={"Authorization": "Bearer autoclaw-operator-test-key"},
            )
            managed = await _post_initialize(
                client,
                "/_internal/node/mcp",
                headers={"Authorization": f"Bearer {issued.credential}"},
            )
            compatibility = await _post_initialize(client, "/node/mcp")

            assert operator.status_code == 200
            assert managed.status_code == 200
            assert compatibility.status_code == 200
            assert registry.authenticate(issued.credential) == issued.binding

    assert startup_calls == ["schema", "dispose"]
    assert registry.authenticate(issued.credential) is None


async def test_main_app_openapi_and_http_routes_exclude_private_mcp_and_callback_lanes() -> None:
    app = create_app(should_enable_mcp_mounts=True)

    openapi_paths = set(app.openapi()["paths"])
    route_paths = {getattr(route, "path", "") for route in app.routes}

    assert "/_internal/node/mcp" not in openapi_paths
    assert "/node/mcp" not in openapi_paths
    assert not any(path.startswith("/callback") for path in openapi_paths)
    assert not any(path.startswith("/callback") for path in route_paths)
