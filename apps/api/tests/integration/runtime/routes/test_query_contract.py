from __future__ import annotations

from pathlib import Path

import pytest
from tests.integration.runtime.routes.support import (
    Phase3RouteContext,
    SeededRouteTask,
    assert_operator_current_paths,
    assign_child,
    build_route_task_compose,
    launch_route_task,
    phase3_route_context,
    yield_boundary,
)

pytestmark = [pytest.mark.requires_openclaw_gateway, pytest.mark.gateway_wait_timeout_default]

async def test_phase3_runtime_routes_sort_and_page_runtime_lists(tmp_path: Path) -> None:
    async with phase3_route_context(tmp_path) as context:
        await launch_alpha_and_zulu_routes(context)

        runtime_list = await context.client.get(
            "/runtime/tasks",
            headers=context.operator_headers,
            params={"sort": "task_title_desc", "limit": 2},
        )
        assert runtime_list.status_code == 200
        assert [item["task_title"] for item in runtime_list.json()["items"]] == [
            "Zulu runtime",
            "Alpha runtime",
        ]

        first_page = await context.client.get(
            "/runtime/tasks",
            headers=context.operator_headers,
            params={"sort": "task_title_asc", "limit": 1},
        )
        assert first_page.status_code == 200
        assert first_page.json()["items"][0]["task_id"] == "task_alpha"
        assert first_page.json()["next_cursor"] == "1"

        second_page = await context.client.get(
            "/runtime/tasks",
            headers=context.operator_headers,
            params={"sort": "task_title_asc", "limit": 1, "cursor": "1"},
        )
        assert second_page.status_code == 200
        assert second_page.json()["items"][0]["task_id"] == "task_zulu"
        assert second_page.json()["next_cursor"] is None


async def test_phase3_runtime_routes_filter_runtime_lists_by_query_and_status(
    tmp_path: Path,
) -> None:
    async with phase3_route_context(tmp_path) as context:
        await launch_alpha_and_zulu_routes(context)

        filtered = await context.client.get(
            "/runtime/tasks",
            headers=context.operator_headers,
            params={"q": "alpha", "status": "running", "sort": "task_title_asc", "limit": 1},
        )
        assert filtered.status_code == 200
        assert filtered.json()["items"][0]["task_id"] == "task_alpha"


async def test_phase3_runtime_routes_trace_boundary_queries(tmp_path: Path) -> None:
    async with phase3_route_context(tmp_path) as context:
        alpha_task, _ = await launch_alpha_and_zulu_routes(context)
        await stage_waiting_child_dispatch(context, alpha_task)

        boundary_trace = await context.client.get(
            f"/operator/tasks/{alpha_task.task_id}/trace",
            headers=context.operator_headers,
            params={"scope": "whole", "q": "yield", "sort": "occurred_at_asc"},
        )
        assert boundary_trace.status_code == 200
        boundary_trace_json = boundary_trace.json()
        assert boundary_trace_json["boundary_history"][0]["boundary"] == "yield"
        assert_operator_current_paths(boundary_trace_json["current_paths"])

        paged_trace = await context.client.get(
            f"/operator/tasks/{alpha_task.task_id}/trace",
            headers=context.operator_headers,
            params={"scope": "whole", "limit": 1, "sort": "occurred_at_asc"},
        )
        assert paged_trace.status_code == 200
        assert paged_trace.json()["next_cursor"] is None


async def test_phase3_runtime_routes_trace_delivery_queries(tmp_path: Path) -> None:
    async with phase3_route_context(tmp_path) as context:
        alpha_task, _ = await launch_alpha_and_zulu_routes(context)
        await stage_waiting_child_dispatch(context, alpha_task)

        delivery_trace = await context.client.get(
            f"/operator/tasks/{alpha_task.task_id}/trace",
            headers=context.operator_headers,
            params={"scope": "whole", "q": "accepted"},
        )
        assert delivery_trace.status_code == 200
        delivery_trace_json = delivery_trace.json()
        assert delivery_trace_json["dispatch_history"]
        assert delivery_trace_json["dispatch_history"][0]["delivery_status"] == "accepted"
        assert_operator_current_paths(delivery_trace_json["current_paths"])


async def launch_alpha_and_zulu_routes(
    context: Phase3RouteContext,
) -> tuple[SeededRouteTask, SeededRouteTask]:
    alpha_task = await launch_route_task(
        context,
        task_id="task_alpha",
        task_root_name="task-alpha-root",
        task_compose=build_route_task_compose(
            task_key="alpha-runtime",
            task_title="Alpha runtime",
            task_summary="Alpha implementation subtree.",
        ),
    )
    zulu_task = await launch_route_task(
        context,
        task_id="task_zulu",
        task_root_name="task-zulu-root",
        task_compose=build_route_task_compose(
            task_key="zulu-runtime",
            task_title="Zulu runtime",
            task_summary="Zulu implementation subtree.",
        ),
    )
    return alpha_task, zulu_task


async def stage_waiting_child_dispatch(
    context: Phase3RouteContext,
    task: SeededRouteTask,
) -> None:
    assign_response = await assign_child(context, task)
    assert assign_response.status_code == 200
    yielded = await yield_boundary(context, task)
    assert yielded.status_code == 200
