from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml
from tests.integration.public_surfaces.support import public_api_context


async def test_definition_authoring_updates_existing_definition_draft(tmp_path: Path) -> None:
    async with public_api_context(tmp_path) as context:
        opened = await context.client.get(
            "/authoring/definitions/workflow/minimal-implement-change/draft",
            headers=context.operator_headers,
        )
        assert opened.status_code == 200
        opened_draft = opened.json()["draft"]
        assert opened_draft["is_saved"] is False
        assert opened_draft["mode"] == "update"
        assert opened_draft["status"] == "clean"

        edited_body = _replace_description(
            cast(str, opened_draft["body"]),
            "Revised workflow description from a flat draft.",
        )
        saved = await context.client.put(
            "/authoring/definitions/workflow/minimal-implement-change/draft",
            headers=context.operator_headers,
            json={"body": edited_body, "body_format": "yaml"},
        )
        assert saved.status_code == 200
        saved_draft = saved.json()["draft"]
        assert saved_draft["is_saved"] is True
        assert saved_draft["status"] == "modified"

        listed = await context.client.get(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
        )
        assert listed.status_code == 200
        assert listed.json()["items"][0]["key"] == "minimal-implement-change"

        validated = await context.client.post(
            "/authoring/definitions/workflow/minimal-implement-change/draft/validate",
            headers=context.operator_headers,
        )
        assert validated.status_code == 200
        assert validated.json()["status"] == "valid"

        published = await context.client.post(
            "/authoring/definitions/workflow/minimal-implement-change/draft/publish",
            headers=context.operator_headers,
        )
        assert published.status_code == 200
        published_json = published.json()
        assert published_json["status"] == "published"
        assert published_json["published_revision"]["kind"] == "workflow"

        detail = await context.client.get(
            "/definitions/workflow/minimal-implement-change",
            headers=context.operator_headers,
        )
        assert detail.status_code == 200
        assert (
            detail.json()["content"]["description"]
            == "Revised workflow description from a flat draft."
        )

        listed_after_publish = await context.client.get(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
        )
        assert listed_after_publish.status_code == 200
        assert listed_after_publish.json()["items"] == []


async def test_definition_authoring_create_rejects_existing_name(tmp_path: Path) -> None:
    async with public_api_context(tmp_path) as context:
        created = await context.client.post(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
            json={
                "kind": "role",
                "key": "engineer",
                "mode": "create",
                "body": _role_body("engineer", "Duplicate engineer role draft."),
                "body_format": "yaml",
            },
        )
        assert created.status_code == 409
        assert created.json()["detail"]["code"] == "name_collision"


async def test_definition_authoring_creates_new_definition_and_blocks_duplicate_draft(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        body = _role_body("local-reviewer", "Review local changes before release.")
        created = await context.client.post(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
            json={
                "kind": "role",
                "key": "local-reviewer",
                "mode": "create",
                "body": body,
                "body_format": "yaml",
            },
        )
        assert created.status_code == 200
        assert created.json()["draft"]["status"] == "new"

        duplicate = await context.client.post(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
            json={
                "kind": "role",
                "key": "local-reviewer",
                "mode": "create",
                "body": body,
                "body_format": "yaml",
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"]["code"] == "name_collision"

        published = await context.client.post(
            "/authoring/definitions/role/local-reviewer/draft/publish",
            headers=context.operator_headers,
        )
        assert published.status_code == 200
        assert published.json()["status"] == "published"
        assert published.json()["published_revision"]["revision_no"] == 1

        detail = await context.client.get(
            "/definitions/role/local-reviewer",
            headers=context.operator_headers,
        )
        assert detail.status_code == 200
        assert detail.json()["content"]["description"] == "Review local changes before release."


async def test_definition_authoring_lists_body_backed_draft_without_metadata(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        body = _role_body("hello", "Draft role stored as a body-only file.")
        draft_path = context.data_dir / "drafts" / "definitions" / "roles" / "hello.yaml"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(body, encoding="utf-8")

        listed = await context.client.get(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
        )
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert [item["key"] for item in items] == ["hello"]
        assert items[0]["kind"] == "role"
        assert items[0]["mode"] == "create"
        assert items[0]["draft_path"] == "roles/hello.yaml"
        assert items[0]["status"] == "new"

        detail = await context.client.get(
            "/authoring/definitions/role/hello/draft",
            headers=context.operator_headers,
        )
        assert detail.status_code == 200
        draft = detail.json()["draft"]
        assert draft["is_saved"] is True
        assert draft["body"] == body
        assert draft["normalized_content"]["id"] == "hello"


async def test_definition_authoring_publish_blocks_stale_update(tmp_path: Path) -> None:
    async with public_api_context(tmp_path) as context:
        created = await context.client.post(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
            json={"kind": "role", "key": "engineer", "mode": "update"},
        )
        assert created.status_code == 200
        draft_body = cast(str, created.json()["draft"]["body"])

        saved = await context.client.put(
            "/authoring/definitions/role/engineer/draft",
            headers=context.operator_headers,
            json={
                "body": _replace_description(
                    draft_body,
                    "Engineer role edited inside a stale flat draft.",
                ),
                "body_format": "yaml",
            },
        )
        assert saved.status_code == 200

        advanced = await context.client.post(
            "/definitions",
            headers=context.operator_headers,
            json={
                "kind": "role",
                "content": {
                    **cast(dict[str, Any], created.json()["draft"]["normalized_content"]),
                    "description": "Registry advanced before flat draft publish.",
                },
            },
        )
        assert advanced.status_code == 201

        validated = await context.client.post(
            "/authoring/definitions/role/engineer/draft/validate",
            headers=context.operator_headers,
        )
        assert validated.status_code == 200
        assert validated.json()["status"] == "stale"

        published = await context.client.post(
            "/authoring/definitions/role/engineer/draft/publish",
            headers=context.operator_headers,
        )
        assert published.status_code == 200
        assert published.json()["status"] == "stale"
        assert published.json()["published_revision"] is None

        detail = await context.client.get(
            "/definitions/role/engineer",
            headers=context.operator_headers,
        )
        assert detail.status_code == 200
        assert (
            detail.json()["content"]["description"]
            == "Registry advanced before flat draft publish."
        )


async def test_definition_authoring_replace_current_refreshes_saved_update_draft(
    tmp_path: Path,
) -> None:
    async with public_api_context(tmp_path) as context:
        created = await context.client.post(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
            json={"kind": "role", "key": "engineer", "mode": "update"},
        )
        assert created.status_code == 200
        draft_body = cast(str, created.json()["draft"]["body"])

        edited = await context.client.put(
            "/authoring/definitions/role/engineer/draft",
            headers=context.operator_headers,
            json={
                "body": _replace_description(
                    draft_body,
                    "Discarded local draft edits.",
                ),
                "body_format": "yaml",
            },
        )
        assert edited.status_code == 200
        assert edited.json()["draft"]["is_saved"] is True
        assert edited.json()["draft"]["status"] == "modified"

        advanced = await context.client.post(
            "/definitions",
            headers=context.operator_headers,
            json={
                "kind": "role",
                "content": {
                    **cast(dict[str, Any], created.json()["draft"]["normalized_content"]),
                    "description": "Current stored revision wins replace-current.",
                },
            },
        )
        assert advanced.status_code == 201
        advanced_revision_no = advanced.json()["revision_no"]

        replaced = await context.client.post(
            "/authoring/definitions/role/engineer/draft/replace-current",
            headers=context.operator_headers,
        )
        assert replaced.status_code == 200
        replaced_draft = replaced.json()["draft"]
        assert replaced_draft["is_saved"] is True
        assert replaced_draft["mode"] == "update"
        assert replaced_draft["status"] == "clean"
        assert replaced_draft["based_on"]["revision_no"] == advanced_revision_no
        assert "Current stored revision wins replace-current." in replaced_draft["body"]
        assert "Discarded local draft edits." not in replaced_draft["body"]

        listed = await context.client.get(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
        )
        assert listed.status_code == 200
        assert [item["key"] for item in listed.json()["items"]] == ["engineer"]


async def test_definition_authoring_publish_blocks_create_race_collision(tmp_path: Path) -> None:
    async with public_api_context(tmp_path) as context:
        body = _role_body("race-reviewer", "Draft created before another writer wins.")
        created = await context.client.post(
            "/authoring/definition-drafts",
            headers=context.operator_headers,
            json={
                "kind": "role",
                "key": "race-reviewer",
                "mode": "create",
                "body": body,
                "body_format": "yaml",
            },
        )
        assert created.status_code == 200

        advanced = await context.client.post(
            "/definitions",
            headers=context.operator_headers,
            json={
                "kind": "role",
                "content": {
                    "id": "race-reviewer",
                    "title": "race-reviewer",
                    "description": "Another writer published first.",
                    "instruction": "Review the assigned scope.",
                    "allowed_node_kinds": ["worker"],
                    "labels": ["authoring"],
                },
            },
        )
        assert advanced.status_code == 201

        published = await context.client.post(
            "/authoring/definitions/role/race-reviewer/draft/publish",
            headers=context.operator_headers,
        )
        assert published.status_code == 200
        assert published.json()["status"] == "name_collision"
        assert published.json()["published_revision"] is None


def _role_body(key: str, description: str) -> str:
    return yaml.safe_dump(
        {
            "kind": "role",
            "id": key,
            "title": key,
            "description": description,
            "instruction": "Review the assigned scope.",
            "allowed_node_kinds": ["worker"],
            "labels": ["authoring"],
        },
        sort_keys=False,
    )


def _replace_description(body: str, description: str) -> str:
    payload = cast(dict[str, Any], yaml.safe_load(body))
    payload["description"] = description
    return yaml.safe_dump(payload, sort_keys=False)
