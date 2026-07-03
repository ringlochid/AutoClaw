from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from autoclaw.definitions.contracts import (
    DefinitionKind,
    DefinitionListQuery,
    DefinitionRevisionDetailResponse,
    DefinitionRevisionHistoryQuery,
    DefinitionSummaryListResponse,
    DefinitionUploadRequest,
    RoleDefinitionInput,
)
from autoclaw.runtime import FlowStatus
from autoclaw.runtime.contracts import TaskStartRequest, TaskStartResponse, WorkflowManifestRef
from pydantic import ValidationError

from tests.unit.definition_schemas.support import bounded_workflow_payload


def test_definition_upload_request_requires_kind_to_match_content() -> None:
    request = DefinitionUploadRequest.model_validate(
        {
            "kind": "role",
            "content": {
                "id": "reviewer",
                "title": "Reviewer",
                "description": "Ordinary review worker.",
                "allowed_node_kinds": ["worker"],
                "instruction": "Review the bounded patch and report evidence only.",
            },
        }
    )

    assert request.kind == DefinitionKind.ROLE
    assert isinstance(request.content, RoleDefinitionInput)

    with pytest.raises(ValidationError, match="does not match content type 'workflow'"):
        DefinitionUploadRequest.model_validate(
            {
                "kind": "policy",
                "content": bounded_workflow_payload(),
            }
        )


def test_definition_list_query_rejects_both_route_specific_filters() -> None:
    query = DefinitionListQuery.model_validate({})

    assert query.limit == 50
    assert query.sort.value == "updated_at_desc"

    with pytest.raises(ValidationError, match="cannot be combined"):
        DefinitionListQuery.model_validate(
            {
                "allowed_node_kind": "worker",
                "applies_to": "worker",
            }
        )


def test_definition_summary_list_response_enforces_kind_specific_fields() -> None:
    timestamp = datetime.now(UTC)

    response = DefinitionSummaryListResponse.model_validate(
        {
            "kind": "role",
            "items": [
                {
                    "key": "reviewer",
                    "title": "Reviewer",
                    "description": "Ordinary review worker.",
                    "current_revision_no": 3,
                    "allowed_node_kinds": ["worker"],
                    "labels": ["review"],
                    "updated_at": timestamp,
                }
            ],
        }
    )

    assert response.kind == DefinitionKind.ROLE
    assert response.items[0].title == "Reviewer"
    assert response.items[0].allowed_node_kinds == ("worker",)
    assert response.items[0].labels == ("review",)

    with pytest.raises(ValidationError, match="workflow summaries must not expose"):
        DefinitionSummaryListResponse.model_validate(
            {
                "kind": "workflow",
                "items": [
                    {
                        "key": "reviewed-change-release",
                        "description": "Normal launch workflow.",
                        "current_revision_no": 2,
                        "allowed_node_kinds": ["root"],
                        "updated_at": timestamp,
                    }
                ],
            }
        )

    existing_response = DefinitionSummaryListResponse.model_validate(
        {
            "kind": "role",
            "items": [
                {
                    "key": "reviewer",
                    "description": "Existing review worker.",
                    "current_revision_no": 3,
                    "allowed_node_kinds": ["worker"],
                    "updated_at": timestamp,
                }
            ],
        }
    )
    assert existing_response.items[0].title is None


def test_definition_revision_detail_response_requires_key_to_match_content_id() -> None:
    timestamp = datetime.now(UTC)

    detail = DefinitionRevisionDetailResponse.model_validate(
        {
            "key": "reviewer",
            "revision_no": 2,
            "content": {
                "id": "reviewer",
                "title": "Reviewer",
                "description": "Ordinary review worker.",
                "allowed_node_kinds": ["worker"],
            },
            "updated_at": timestamp,
        }
    )

    assert detail.content.id == "reviewer"

    with pytest.raises(ValidationError, match=r"key must match content\.id"):
        DefinitionRevisionDetailResponse.model_validate(
            {
                "key": "reviewer",
                "revision_no": 2,
                "content": {
                    "id": "planner",
                    "title": "Planner",
                    "description": "Planning lead.",
                    "allowed_node_kinds": ["root", "parent"],
                },
                "updated_at": timestamp,
            }
        )


def test_definition_revision_history_query_uses_canonical_defaults() -> None:
    query = DefinitionRevisionHistoryQuery.model_validate({})

    assert query.limit == 50
    assert query.sort.value == "revision_no_desc"
    assert query.cursor is None


def test_task_start_request_accepts_minimal_body_and_rejects_unsupported_fields() -> None:
    request = TaskStartRequest.model_validate(
        {
            "task": {
                "key": "auth-refresh-hardening",
                "title": "Harden auth refresh flow",
                "summary": "Investigate and fix the auth refresh regression.",
            },
            "workflow": {"key": "reviewed-change-release"},
        }
    )

    assert request.task.key == "auth-refresh-hardening"
    assert request.roots is None

    with pytest.raises(ValidationError):
        TaskStartRequest.model_validate(
            {
                "task": {
                    "key": "auth-refresh-hardening",
                    "title": "Harden auth refresh flow",
                    "summary": "Investigate and fix the auth refresh regression.",
                },
                "workflow": {"key": "reviewed-change-release"},
                "roots": {
                    "outputs": {
                        "mode": "ensure_task_default",
                    }
                },
            }
        )

    with pytest.raises(ValidationError):
        TaskStartRequest.model_validate(
            {
                "task": {
                    "key": "auth-refresh-hardening",
                    "title": "Harden auth refresh flow",
                    "summary": "Investigate and fix the auth refresh regression.",
                },
                "workflow": {"key": "reviewed-change-release"},
                "initial_assignment": {
                    "summary": "This field is not part of the public task-start contract.",
                },
            }
        )


def test_task_start_response_uses_the_canonical_public_fields() -> None:
    response = TaskStartResponse(
        task_id="task.auth-refresh-hardening",
        compiled_plan_id="compiled-plan.auth-refresh-hardening",
        active_flow_revision_id="flow-revision.auth-refresh-hardening.001",
        flow_status=FlowStatus.RUNNING,
        workflow_manifest_ref=WorkflowManifestRef(
            path=Path("/tmp/task/_runtime/workflow-manifest.json"),
            description="Whole-workflow visible contract for the current task.",
        ),
    )

    dumped = response.model_dump(mode="json")

    assert set(dumped) == {
        "task_id",
        "compiled_plan_id",
        "active_flow_revision_id",
        "flow_status",
        "workflow_manifest_ref",
    }
    assert "dispatch_id" not in dumped
    assert "flow_id" not in dumped
