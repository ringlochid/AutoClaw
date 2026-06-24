from __future__ import annotations

import asyncio
from pathlib import Path

from autoclaw.definitions.contracts.registry import RoleDefinitionInput
from autoclaw.definitions.registry import load_current_workflow, upsert_workflow_definition
from autoclaw.persistence.models import CompiledPlanModel, TaskModel
from sqlalchemy import select
from tests.integration.public_surfaces.support import public_api_context, task_start_payload


async def test_public_definition_routes_require_operator_auth_and_validate_queries(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        unauthorized = await context.client.get("/definitions/roles")
        assert unauthorized.status_code == 401
        assert unauthorized.json()["detail"]["code"] == "illegal_caller"

        invalid_limit = await context.client.get(
            "/definitions/roles",
            headers=context.operator_headers,
            params={"limit": 0},
        )
        assert invalid_limit.status_code == 400
        assert invalid_limit.json()["code"] == "invalid_request_shape"

        invalid_cursor = await context.client.get(
            "/definitions/workflow/minimal-implement-change/versions",
            headers=context.operator_headers,
            params={"cursor": "bad-offset"},
        )
        assert invalid_cursor.status_code == 400
        assert invalid_cursor.json()["detail"]["code"] == "invalid_request_shape"


async def test_public_definition_routes_list_filter_and_page_by_kind(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        roles = await context.client.get(
            "/definitions/roles",
            headers=context.operator_headers,
            params={"q": "planning", "allowed_node_kind": "parent", "sort": "key_asc"},
        )
        assert roles.status_code == 200
        roles_json = roles.json()
        assert roles_json["kind"] == "role"
        assert roles_json["items"]
        assert roles_json["items"][0]["key"] == "planning_lead"
        assert roles_json["items"][0]["title"] == "Planning Lead"
        assert "parent" in roles_json["items"][0]["allowed_node_kinds"]
        assert roles_json["items"][0]["applies_to"] is None
        assert roles_json["items"][0]["labels"] == []

        policies = await context.client.get(
            "/definitions/policies",
            headers=context.operator_headers,
            params={"applies_to": "worker", "sort": "key_asc"},
        )
        assert policies.status_code == 200
        policies_json = policies.json()
        assert policies_json["kind"] == "policy"
        assert policies_json["items"]
        assert "worker" in policies_json["items"][0]["applies_to"]
        assert policies_json["items"][0]["allowed_node_kinds"] is None

        first_page = await context.client.get(
            "/definitions/workflows",
            headers=context.operator_headers,
            params={"sort": "key_asc", "limit": 1},
        )
        assert first_page.status_code == 200
        first_page_json = first_page.json()
        assert first_page_json["kind"] == "workflow"
        assert len(first_page_json["items"]) == 1
        assert first_page_json["next_cursor"] == "1"

        second_page = await context.client.get(
            "/definitions/workflows",
            headers=context.operator_headers,
            params={"sort": "key_asc", "limit": 1, "cursor": "1"},
        )
        assert second_page.status_code == 200
        assert second_page.json()["items"]


async def test_public_definition_routes_surface_current_detail_and_history(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        async with context.session_factory() as session:
            current = await load_current_workflow(session, "minimal-implement-change")
            updated = current.definition.model_copy(
                update={"description": f"{current.definition.description} v2"}
            )
            await upsert_workflow_definition(
                session,
                updated,
                source_path="test://public-workflow-v2",
            )
            await session.commit()

        detail = await context.client.get(
            "/definitions/workflow/minimal-implement-change",
            headers=context.operator_headers,
        )
        assert detail.status_code == 200
        detail_json = detail.json()
        assert detail_json["key"] == "minimal-implement-change"
        assert detail_json["revision_no"] == 2
        assert "recorded_by" in detail_json
        assert detail_json["recorded_by"] is None
        assert detail_json["content"]["description"].endswith("v2")

        history = await context.client.get(
            "/definitions/workflow/minimal-implement-change/versions",
            headers=context.operator_headers,
            params={"sort": "revision_no_desc", "limit": 1},
        )
        assert history.status_code == 200
        history_json = history.json()
        assert history_json["kind"] == "workflow"
        assert history_json["current_revision_no"] == 2
        assert "recorded_by" in history_json["items"][0]
        assert history_json["items"][0]["recorded_by"] is None
        assert [item["revision_no"] for item in history_json["items"]] == [2]
        assert history_json["next_cursor"] == "1"

        second_page = await context.client.get(
            "/definitions/workflow/minimal-implement-change/versions",
            headers=context.operator_headers,
            params={"sort": "revision_no_desc", "limit": 1, "cursor": "1"},
        )
        assert second_page.status_code == 200
        assert [item["revision_no"] for item in second_page.json()["items"]] == [1]


async def test_public_definition_upload_creates_noops_and_new_revisions(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        role = RoleDefinitionInput.model_validate(
            {
                "id": "public-reviewer",
                "title": "Public Reviewer",
                "description": "Review worker for the public upload test.",
                "allowed_node_kinds": ["worker"],
                "labels": ["public-surface"],
                "instruction": "Review only the surfaced evidence.",
            }
        )

        created = await context.client.post(
            "/definitions",
            headers=context.operator_headers,
            json={"kind": "role", "content": role.model_dump(mode="json")},
        )
        assert created.status_code == 201
        assert created.json()["key"] == "public-reviewer"
        assert created.json()["revision_no"] == 1

        unchanged = await context.client.post(
            "/definitions",
            headers=context.operator_headers,
            json={"kind": "role", "content": role.model_dump(mode="json")},
        )
        assert unchanged.status_code == 200
        assert unchanged.json()["revision_no"] == 1

        updated_role = role.model_copy(update={"description": f"{role.description} v2"})
        updated = await context.client.post(
            "/definitions",
            headers=context.operator_headers,
            json={"kind": "role", "content": updated_role.model_dump(mode="json")},
        )
        assert updated.status_code == 201
        assert updated.json()["revision_no"] == 2

        searched = await context.client.get(
            "/definitions/roles",
            headers=context.operator_headers,
            params={"q": "public-surface"},
        )
        assert searched.status_code == 200
        searched_json = searched.json()
        assert [item["key"] for item in searched_json["items"]] == ["public-reviewer"]
        assert searched_json["items"][0]["title"] == "Public Reviewer"
        assert searched_json["items"][0]["labels"] == ["public-surface"]


async def test_public_task_start_launches_runtime_and_returns_manifest_readback(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        response = await context.client.post(
            "/tasks/start",
            headers=context.operator_headers,
            json=task_start_payload().model_dump(mode="json"),
        )
        assert response.status_code == 200
        payload = response.json()
        manifest_path = Path(payload["workflow_manifest_ref"]["path"])

        assert payload["task_id"]
        assert payload["compiled_plan_id"]
        assert payload["active_flow_revision_id"]
        assert payload["flow_status"] == "running"
        assert await asyncio.to_thread(manifest_path.is_file)

        runtime_read = await context.client.get(
            f"/runtime/tasks/{payload['task_id']}",
            headers=context.operator_headers,
        )
        assert runtime_read.status_code == 200
        runtime_json = runtime_read.json()
        assert runtime_json["task_id"] == payload["task_id"]
        assert runtime_json["active_flow_revision_id"] == payload["active_flow_revision_id"]
        assert Path(runtime_json["workflow_manifest_ref"]["path"]) == manifest_path

        async with context.session_factory() as session:
            task = await session.scalar(
                select(TaskModel).where(TaskModel.task_id == payload["task_id"])
            )
            compiled_plan = await session.scalar(
                select(CompiledPlanModel).where(
                    CompiledPlanModel.compiled_plan_id == payload["compiled_plan_id"]
                )
            )

        assert task is not None
        assert compiled_plan is not None
        assert task.task_root_path.startswith(str(context.data_dir))


async def test_public_task_start_generates_unique_task_ids_for_repeated_task_keys(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        first = await context.client.post(
            "/tasks/start",
            headers=context.operator_headers,
            json=task_start_payload().model_dump(mode="json"),
        )
        second = await context.client.post(
            "/tasks/start",
            headers=context.operator_headers,
            json=task_start_payload().model_dump(mode="json"),
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["task_id"] != second.json()["task_id"]
