from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.api.errors import operation_failure, runtime_exception_failure
from app.schemas.operation_failure import OperationFailure, OperationFailureCode
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools.base import Tool
from mcp.server.fastmcp.tools.tool_manager import ToolManager
from mcp.shared.exceptions import UrlElicitationRequiredError
from mcp.types import CallToolResult, Icon, TextContent, ToolAnnotations
from pydantic import ValidationError as PydanticValidationError


class ContractFastMCP(FastMCP[Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._tool_manager = ContractToolManager(
            warn_on_duplicate_tools=self.settings.warn_on_duplicate_tools
        )


class ContractToolManager(ToolManager):
    def add_tool(
        self,
        fn: Callable[..., Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        icons: list[Icon] | None = None,
        meta: dict[str, Any] | None = None,
        structured_output: bool | None = None,
    ) -> Tool:
        tool = ContractTool.from_function(
            fn,
            name=name,
            title=title,
            description=description,
            annotations=annotations,
            icons=icons,
            meta=meta,
            structured_output=structured_output,
        )
        existing = self.get_tool(tool.name)
        if existing is not None:
            return existing
        self._tools[tool.name] = tool
        return tool


class ContractTool(Tool):
    async def run(
        self,
        arguments: dict[str, Any],
        context: Any = None,
        convert_result: bool = False,
    ) -> Any:
        try:
            result = await self.fn_metadata.call_fn_with_arg_validation(
                self.fn,
                self.is_async,
                arguments,
                {self.context_kwarg: context} if self.context_kwarg is not None else None,
            )
            if convert_result:
                return _convert_mcp_result(self, result)
            return result
        except UrlElicitationRequiredError:
            raise
        except PydanticValidationError as exc:
            return operation_failure_tool_result(_validation_failure(exc))
        except Exception as exc:
            return operation_failure_tool_result(_runtime_failure(exc))


def operation_failure_tool_result(failure: OperationFailure) -> CallToolResult:
    payload = failure.model_dump(mode="json")
    return CallToolResult(
        content=[TextContent(type="text", text=failure.summary)],
        structuredContent=payload,
        isError=True,
    )


def _convert_mcp_result(tool: Tool, result: Any) -> Any:
    if isinstance(result, CallToolResult):
        return result
    return tool.fn_metadata.convert_result(result)


def _runtime_failure(exc: Exception) -> OperationFailure:
    _status_code, failure = runtime_exception_failure(exc)
    return failure


def _validation_failure(exc: PydanticValidationError) -> OperationFailure:
    first_error = exc.errors()[0] if exc.errors() else None
    loc = first_error.get("loc", ()) if first_error is not None else ()
    field_path = ".".join(str(part) for part in loc) or None
    return operation_failure(
        code=OperationFailureCode.INVALID_REQUEST_SHAPE,
        summary="request shape does not match the canonical runtime surface",
        retryable=False,
        field_path=field_path,
        suggested_next_step=(
            "Reread the canonical request shape and resend the request with only the live "
            "required fields."
        ),
    )


__all__ = ["ContractFastMCP", "operation_failure_tool_result"]
