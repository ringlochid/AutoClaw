from __future__ import annotations

from pathlib import Path

from autoclaw.openclaw.operator_server import create_operator_mcp_app
from tests.integration.phase3.runtime_support import prepare_runtime_db
from tests.integration.phase4b.mcp.support import (
    assert_tool_result_matches_output_schema,
    call_tool_result,
    default_transport_security,
    mcp_client_session,
    phase3_runtime_api,
    tool_failure,
    tool_output_schema,
)


async def test_phase4b_operator_mcp_rejects_validation_failures_with_operation_failure_shape() -> (
    None
):
    app = create_operator_mcp_app(transport_security=default_transport_security(host="127.0.0.1"))

    async with mcp_client_session(app) as session:
        tools = await session.list_tools()
        result = await call_tool_result(
            session,
            "list_runtime_tasks",
            {"limit": "not-an-integer"},
        )

    schema = tool_output_schema(tools, "list_runtime_tasks")
    assert schema is not None
    assert schema["type"] == "object"
    assert schema["oneOf"]
    failure = tool_failure(result)
    assert_tool_result_matches_output_schema(tools, "list_runtime_tasks", result)
    assert failure == {
        "ok": False,
        "code": "invalid_request_shape",
        "summary": "request shape does not match the canonical runtime surface",
        "retryable": False,
        "field_path": "limit",
        "suggested_next_step": (
            "Reread the canonical request shape and resend the request with only the live "
            "required fields."
        ),
    }
    assert result.content[0].text == failure["summary"]


async def test_phase4b_operator_mcp_rejects_semantic_failures_with_operation_failure_shape(
    tmp_path: Path,
) -> None:
    config_path = await prepare_runtime_db(tmp_path)

    async with phase3_runtime_api(config_path):
        app = create_operator_mcp_app(
            transport_security=default_transport_security(host="127.0.0.1")
        )
        async with mcp_client_session(app) as session:
            tools = await session.list_tools()
            result = await call_tool_result(
                session,
                "get_runtime_task",
                {"task_id": "task.phase4b.operator-mcp-missing"},
            )

    schema = tool_output_schema(tools, "get_runtime_task")
    assert schema is not None
    assert schema["type"] == "object"
    assert schema["oneOf"]
    failure = tool_failure(result)
    assert_tool_result_matches_output_schema(tools, "get_runtime_task", result)
    assert failure == {
        "ok": False,
        "code": "missing_resource",
        "summary": "unknown task_id 'task.phase4b.operator-mcp-missing'",
        "retryable": False,
        "field_path": None,
        "suggested_next_step": (
            "Verify the task, flow, or dispatch id and reread the current runtime "
            "surface before retrying this request."
        ),
    }
    assert result.content[0].text == failure["summary"]
