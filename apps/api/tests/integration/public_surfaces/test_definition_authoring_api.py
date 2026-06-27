from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import autoclaw.definitions.authoring.service as definition_authoring_service
import pytest
import yaml
from autoclaw.runtime.contracts.operation_failure import OperationFailureCode
from autoclaw.runtime.errors import RuntimeOperationError
from tests.integration.public_surfaces.support import public_api_context, task_start_payload


async def test_definition_authoring_end_to_end_apply_and_start_task(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        listed = await context.client.get(
            "/authoring/definition-draft-sets",
            headers=context.operator_headers,
        )
        assert listed.status_code == 200
        assert listed.json()["items"] == []

        created = await context.client.post(
            "/authoring/definition-draft-sets",
            headers=context.operator_headers,
            json={
                "title": "Workflow editor draft",
                "materialize": [{"kind": "workflow", "key": "minimal-implement-change"}],
                "preview_task_compose": yaml.safe_dump(
                    task_start_payload("minimal-implement-change").model_dump(mode="json"),
                    sort_keys=False,
                ),
            },
        )
        assert created.status_code == 200
        created_json = created.json()["draft_set"]
        draft_set_id = created_json["draft_set_id"]
        workflow_file = created_json["files"][0]
        assert workflow_file["body_format"] == "yaml"
        assert workflow_file["status"] == "clean"
        assert workflow_file["body"]
        assert workflow_file["normalized_content"]["id"] == "minimal-implement-change"
        assert workflow_file["baseline_body"] == workflow_file["body"]
        assert created_json["preview_task_compose_path"] == "task-compose.preview.yaml"
        assert "minimal-implement-change" in created_json["preview_task_compose_body"]

        edited_body = _replace_workflow_description(
            workflow_file["body"],
            "Revised workflow description for authoring apply coverage.",
        )
        saved = await context.client.put(
            f"/authoring/definition-draft-sets/{draft_set_id}/files/workflow/minimal-implement-change",
            headers=context.operator_headers,
            json={"body": edited_body, "body_format": "yaml"},
        )
        assert saved.status_code == 200
        saved_workflow_file = saved.json()["draft_set"]["files"][0]
        assert saved_workflow_file["status"] == "modified"
        assert saved_workflow_file["body"] == edited_body
        assert (
            saved_workflow_file["normalized_content"]["description"]
            == "Revised workflow description for authoring apply coverage."
        )

        validated = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/validate",
            headers=context.operator_headers,
        )
        assert validated.status_code == 200
        assert validated.json()["status"] == "valid"
        assert validated.json()["errors"] == []

        previewed = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/preview-task-compose",
            headers=context.operator_headers,
            json={
                "body": yaml.safe_dump(
                    task_start_payload("minimal-implement-change").model_dump(mode="json"),
                    sort_keys=False,
                ),
                "body_format": "yaml",
            },
        )
        assert previewed.status_code == 200
        assert previewed.json()["status"] == "valid"

        applied = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/apply",
            headers=context.operator_headers,
            json={"should_start_task_after_apply": True},
        )
        assert applied.status_code == 200
        applied_json = applied.json()
        assert applied_json["status"] == "applied"
        assert applied_json["published_revisions"]
        assert applied_json["published_revisions"][0]["kind"] == "workflow"
        started_task_id = applied_json["started_task_id"]
        assert isinstance(started_task_id, str)

        runtime_read = await context.client.get(
            f"/runtime/tasks/{started_task_id}",
            headers=context.operator_headers,
        )
        assert runtime_read.status_code == 200

        reopened = await context.client.get(
            f"/authoring/definition-draft-sets/{draft_set_id}",
            headers=context.operator_headers,
        )
        assert reopened.status_code == 200
        reopened_json = reopened.json()["draft_set"]
        assert reopened_json["state"] == "applied"
        assert reopened_json["files"][0]["status"] == "clean"

        deleted = await context.client.delete(
            f"/authoring/definition-draft-sets/{draft_set_id}",
            headers=context.operator_headers,
        )
        assert deleted.status_code == 204

        missing = await context.client.get(
            f"/authoring/definition-draft-sets/{draft_set_id}",
            headers=context.operator_headers,
        )
        assert missing.status_code == 404
        assert missing.json()["detail"]["code"] == "missing_resource"


async def test_definition_authoring_reset_and_rematerialize_current_handle_staleness(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        created = await context.client.post(
            "/authoring/definition-draft-sets",
            headers=context.operator_headers,
            json={"materialize": [{"kind": "role", "key": "engineer"}]},
        )
        assert created.status_code == 200
        draft_set = created.json()["draft_set"]
        draft_set_id = draft_set["draft_set_id"]
        role_file = draft_set["files"][0]
        original_body = cast(str, role_file["body"])
        original_revision_no = role_file["based_on"]["revision_no"]

        edited_body = _replace_role_description(
            original_body,
            "Locally edited engineer role description.",
        )
        saved = await context.client.put(
            f"/authoring/definition-draft-sets/{draft_set_id}/files/role/engineer",
            headers=context.operator_headers,
            json={"body": edited_body, "body_format": "yaml"},
        )
        assert saved.status_code == 200
        assert saved.json()["draft_set"]["files"][0]["status"] == "modified"

        reset = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/files/role/engineer/reset",
            headers=context.operator_headers,
            json={"discard_local_changes": True},
        )
        assert reset.status_code == 200
        reset_file = reset.json()["draft_set"]["files"][0]
        assert reset_file["status"] == "clean"
        assert reset_file["body"] == original_body

        uploaded = await context.client.post(
            "/definitions",
            headers=context.operator_headers,
            json={
                "kind": "role",
                "content": {
                    **cast(dict[str, Any], role_file["normalized_content"]),
                    "description": "Registry advanced engineer role baseline.",
                },
            },
        )
        assert uploaded.status_code == 201

        stale = await context.client.get(
            f"/authoring/definition-draft-sets/{draft_set_id}",
            headers=context.operator_headers,
        )
        assert stale.status_code == 200
        stale_file = stale.json()["draft_set"]["files"][0]
        assert stale.json()["draft_set"]["state"] == "stale"
        assert stale_file["status"] == "stale"

        stale_validation = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/validate",
            headers=context.operator_headers,
        )
        assert stale_validation.status_code == 200
        assert stale_validation.json()["status"] == "stale"
        assert any(error["kind"] == "stale" for error in stale_validation.json()["errors"])

        rematerialized = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/files/role/engineer/rematerialize-current",
            headers=context.operator_headers,
            json={"discard_local_changes": True},
        )
        assert rematerialized.status_code == 200
        rematerialized_file = rematerialized.json()["draft_set"]["files"][0]
        assert rematerialized.json()["draft_set"]["state"] == "open"
        assert rematerialized_file["status"] == "clean"
        assert (
            rematerialized_file["normalized_content"]["description"]
            == "Registry advanced engineer role baseline."
        )
        assert rematerialized_file["based_on"]["revision_no"] == original_revision_no + 1


async def test_definition_authoring_create_rolls_back_partial_materialization_failure(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        created = await context.client.post(
            "/authoring/definition-draft-sets",
            headers=context.operator_headers,
            json={
                "title": "Should not leave a ghost draft set",
                "materialize": [
                    {"kind": "workflow", "key": "minimal-implement-change"},
                    {"kind": "workflow", "key": "missing-workflow"},
                ],
                "preview_task_compose": yaml.safe_dump(
                    task_start_payload("minimal-implement-change").model_dump(mode="json"),
                    sort_keys=False,
                ),
            },
        )
        assert created.status_code == 404
        assert created.json()["detail"]["code"] == "missing_resource"

        listed = await context.client.get(
            "/authoring/definition-draft-sets",
            headers=context.operator_headers,
        )
        assert listed.status_code == 200
        assert listed.json()["items"] == []

        drafts_root = context.data_dir / "drafts" / "definitions"
        assert not drafts_root.exists() or list(drafts_root.iterdir()) == []


async def test_definition_authoring_materialize_rolls_back_partial_file_writes_on_failure(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        created = await context.client.post(
            "/authoring/definition-draft-sets",
            headers=context.operator_headers,
            json={"title": "Existing draft set"},
        )
        assert created.status_code == 200
        draft_set_id = created.json()["draft_set"]["draft_set_id"]

        materialized = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/materialize",
            headers=context.operator_headers,
            json={
                "definitions": [
                    {"kind": "workflow", "key": "minimal-implement-change"},
                    {"kind": "workflow", "key": "missing-workflow"},
                ]
            },
        )
        assert materialized.status_code == 404
        assert materialized.json()["detail"]["code"] == "missing_resource"

        detail = await context.client.get(
            f"/authoring/definition-draft-sets/{draft_set_id}",
            headers=context.operator_headers,
        )
        assert detail.status_code == 200
        assert detail.json()["draft_set"]["files"] == []

        draft_set_root = context.data_dir / "drafts" / "definitions" / draft_set_id
        assert not (draft_set_root / "workflows" / "minimal-implement-change.yaml").exists()
        assert not (
            draft_set_root / "_normalized" / "workflows" / "minimal-implement-change.json"
        ).exists()


async def test_definition_authoring_apply_allows_invalid_saved_preview_without_task_start(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        created = await context.client.post(
            "/authoring/definition-draft-sets",
            headers=context.operator_headers,
            json={
                "materialize": [{"kind": "workflow", "key": "minimal-implement-change"}],
                "preview_task_compose": "not: [valid",
            },
        )
        assert created.status_code == 200
        draft_set_id = created.json()["draft_set"]["draft_set_id"]

        validated = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/validate",
            headers=context.operator_headers,
        )
        assert validated.status_code == 200
        assert validated.json()["status"] == "valid"
        assert validated.json()["errors"] == []
        assert len(validated.json()["warnings"]) == 1
        warning = validated.json()["warnings"][0]
        assert warning["code"] == "preview_task_compose_invalid"
        assert warning["path"] == "task-compose.preview.yaml"
        assert warning["kind"] == "preview"
        assert "invalid YAML:" in warning["message"]

        applied = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/apply",
            headers=context.operator_headers,
            json={"should_start_task_after_apply": False},
        )
        assert applied.status_code == 200
        applied_json = applied.json()
        assert applied_json["status"] == "applied"
        assert applied_json["task_start_status"] == "not_requested"
        assert applied_json["started_task_id"] is None
        assert applied_json["task_start_failure"] is None
        assert applied_json["validation"]["status"] == "valid"
        assert applied_json["validation"]["errors"] == []
        assert applied_json["validation"]["warnings"][0]["code"] == "preview_task_compose_invalid"


async def test_definition_authoring_apply_reports_task_start_failure_after_successful_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with public_api_context(tmp_path) as context:
        created = await context.client.post(
            "/authoring/definition-draft-sets",
            headers=context.operator_headers,
            json={
                "title": "Workflow editor draft",
                "materialize": [{"kind": "workflow", "key": "minimal-implement-change"}],
                "preview_task_compose": yaml.safe_dump(
                    task_start_payload("minimal-implement-change").model_dump(mode="json"),
                    sort_keys=False,
                ),
            },
        )
        assert created.status_code == 200
        created_json = created.json()["draft_set"]
        draft_set_id = created_json["draft_set_id"]
        workflow_file = created_json["files"][0]

        edited_body = _replace_workflow_description(
            workflow_file["body"],
            "Published even when the follow-on task start fails.",
        )
        saved = await context.client.put(
            f"/authoring/definition-draft-sets/{draft_set_id}/files/workflow/minimal-implement-change",
            headers=context.operator_headers,
            json={"body": edited_body, "body_format": "yaml"},
        )
        assert saved.status_code == 200

        async def fail_task_start(_request: object) -> object:
            raise RuntimeOperationError(
                code=OperationFailureCode.INVALID_REQUEST_SHAPE,
                summary="simulated post-apply task start failure",
                is_retryable=False,
                suggested_next_step="Repair the saved preview task-start body before retrying.",
            )

        monkeypatch.setattr(
            definition_authoring_service,
            "start_task_from_definition",
            fail_task_start,
        )

        applied = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/apply",
            headers=context.operator_headers,
            json={"should_start_task_after_apply": True},
        )
        assert applied.status_code == 200
        applied_json = applied.json()
        assert applied_json["status"] == "applied"
        assert applied_json["published_revisions"]
        assert applied_json["started_task_id"] is None
        assert applied_json["task_start_status"] == "failed"
        assert applied_json["task_start_failure"] == {
            "code": "invalid_request_shape",
            "summary": "simulated post-apply task start failure",
            "is_retryable": False,
            "suggested_next_step": "Repair the saved preview task-start body before retrying.",
        }

        detail = await context.client.get(
            "/definitions/workflow/minimal-implement-change",
            headers=context.operator_headers,
        )
        assert detail.status_code == 200
        assert (
            detail.json()["content"]["description"]
            == "Published even when the follow-on task start fails."
        )

        reopened = await context.client.get(
            f"/authoring/definition-draft-sets/{draft_set_id}",
            headers=context.operator_headers,
        )
        assert reopened.status_code == 200
        reopened_json = reopened.json()["draft_set"]
        assert reopened_json["state"] == "applied"
        assert reopened_json["files"][0]["status"] == "clean"


async def test_definition_authoring_local_changes_reopen_applied_draft_set(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        created = await context.client.post(
            "/authoring/definition-draft-sets",
            headers=context.operator_headers,
            json={
                "materialize": [{"kind": "workflow", "key": "minimal-implement-change"}],
                "preview_task_compose": yaml.safe_dump(
                    task_start_payload("minimal-implement-change").model_dump(mode="json"),
                    sort_keys=False,
                ),
            },
        )
        assert created.status_code == 200
        draft_set = created.json()["draft_set"]
        draft_set_id = draft_set["draft_set_id"]
        original_body = cast(str, draft_set["files"][0]["body"])

        applied = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/apply",
            headers=context.operator_headers,
            json={"should_start_task_after_apply": False},
        )
        assert applied.status_code == 200
        assert applied.json()["status"] == "applied"

        previewed = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/preview-task-compose",
            headers=context.operator_headers,
            json={
                "body": yaml.safe_dump(
                    task_start_payload("minimal-implement-change").model_dump(mode="json")
                    | {"operator_notes": "reopened after preview edit"},
                    sort_keys=False,
                ),
                "body_format": "yaml",
            },
        )
        assert previewed.status_code == 200

        preview_reopened = await context.client.get(
            f"/authoring/definition-draft-sets/{draft_set_id}",
            headers=context.operator_headers,
        )
        assert preview_reopened.status_code == 200
        assert preview_reopened.json()["draft_set"]["state"] == "open"

        reapplied = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/apply",
            headers=context.operator_headers,
            json={"should_start_task_after_apply": False},
        )
        assert reapplied.status_code == 200
        assert reapplied.json()["status"] == "applied"

        edited_body = _replace_workflow_description(
            original_body,
            "Applied draft reopened after a local workflow edit.",
        )
        saved = await context.client.put(
            f"/authoring/definition-draft-sets/{draft_set_id}/files/workflow/minimal-implement-change",
            headers=context.operator_headers,
            json={"body": edited_body, "body_format": "yaml"},
        )
        assert saved.status_code == 200
        assert saved.json()["draft_set"]["state"] == "open"
        assert saved.json()["draft_set"]["files"][0]["status"] == "modified"

        uploaded = await context.client.post(
            "/definitions",
            headers=context.operator_headers,
            json={
                "kind": "workflow",
                "content": {
                    **cast(
                        dict[str, Any],
                        saved.json()["draft_set"]["files"][0]["normalized_content"],
                    ),
                    "description": "Registry advanced workflow baseline before rematerialize.",
                },
            },
        )
        assert uploaded.status_code == 201

        rematerialized = await context.client.post(
            f"/authoring/definition-draft-sets/{draft_set_id}/files/workflow/minimal-implement-change/rematerialize-current",
            headers=context.operator_headers,
            json={"discard_local_changes": True},
        )
        assert rematerialized.status_code == 200
        rematerialized_json = rematerialized.json()["draft_set"]
        assert rematerialized_json["state"] == "open"
        assert rematerialized_json["files"][0]["status"] == "clean"
        assert (
            rematerialized_json["files"][0]["normalized_content"]["description"]
            == "Registry advanced workflow baseline before rematerialize."
        )


def _replace_workflow_description(body: str, description: str) -> str:
    payload = cast(dict[str, Any], yaml.safe_load(body))
    payload["description"] = description
    return yaml.safe_dump(payload, sort_keys=False)


def _replace_role_description(body: str, description: str) -> str:
    payload = cast(dict[str, Any], yaml.safe_load(body))
    payload["description"] = description
    return yaml.safe_dump(payload, sort_keys=False)
