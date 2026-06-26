from __future__ import annotations

from typing import Any


def review_request_payload() -> dict[str, Any]:
    return {
        "kind": "review",
        "title": "Review implementation patch",
        "summary": "The node needs a human review before continuing.",
        "items": [
            {
                "item_id": "review_choice",
                "prompt": "Should the node proceed with this patch?",
                "options": [
                    {"id": "approve", "title": "Approve"},
                    {"id": "revise", "title": "Revise"},
                ],
                "recommended_option": "approve",
            }
        ],
        "timeout": {"due_at": None, "default_behavior": None},
        "suggested_human_instruction": "Inspect the patch before answering.",
    }


def input_request_payload() -> dict[str, Any]:
    return {
        "kind": "input",
        "title": "Provide launch details",
        "summary": "The node needs structured launch inputs before continuing.",
        "items": [
            {
                "item_id": "launch_details",
                "prompt": "Provide the launch name and retry limit.",
                "input_payload_schema": {
                    "type": "object",
                    "required": ["name", "retry_limit"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "retry_limit": {"type": "integer", "minimum": 0},
                    },
                    "additionalProperties": False,
                },
            }
        ],
        "timeout": {"due_at": None, "default_behavior": None},
        "suggested_human_instruction": "Fill in the structured launch input.",
    }


def answer_payload(*, item_id: str = "review_choice", option_id: str = "approve") -> dict[str, Any]:
    return {
        "item_responses": [
            {
                "item_id": item_id,
                "selected_option": option_id,
                "freeform_answer": None,
                "extra_notes": "Looks good.",
                "response_payload": None,
            }
        ]
    }


def structured_input_answer_payload(
    response_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "item_responses": [
            {
                "item_id": "launch_details",
                "selected_option": None,
                "freeform_answer": None,
                "extra_notes": "Use these launch values.",
                "response_payload": response_payload
                if response_payload is not None
                else {"name": "alpha", "retry_limit": 2},
            }
        ]
    }
