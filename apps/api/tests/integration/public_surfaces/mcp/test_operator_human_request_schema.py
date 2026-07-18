from __future__ import annotations

from typing import cast

from autoclaw.interfaces.mcp.operator.server import create_operator_mcp_server
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]


async def test_operator_human_resolution_schema_uses_typed_response_map() -> None:
    tools = await create_operator_mcp_server().list_tools()
    tool = next(tool for tool in tools if tool.name == "resolve_human_request")
    schema = cast(dict[str, object], tool.inputSchema)
    properties = cast(dict[str, object], schema["properties"])
    item_responses_schema = cast(dict[str, object], properties["item_responses"])

    assert item_responses_schema["type"] == "object"
    assert "additionalProperties" in item_responses_schema
    assert "items" not in item_responses_schema

    validator = Draft202012Validator(schema)
    validator.validate(
        {
            "task_id": "task.operator-schema",
            "request_id": "human-request.operator-schema.01",
            "item_responses": {"review_choice": "approve"},
        }
    )
    legacy_response_errors = tuple(
        validator.iter_errors(
            {
                "task_id": "task.operator-schema",
                "request_id": "human-request.operator-schema.01",
                "item_responses": [
                    {
                        "item_id": "review_choice",
                        "selected_option": "approve",
                    }
                ],
            }
        )
    )
    assert legacy_response_errors
