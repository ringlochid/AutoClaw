from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def add_operator_auth_middleware(app: Starlette, *, expected_token: str) -> None:
    app.add_middleware(
        cast(Any, _OperatorAuthMiddleware),
        expected_token=expected_token,
    )


class _OperatorAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Starlette, *, expected_token: str) -> None:
        super().__init__(app)
        self._expected_token = expected_token

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        expected = f"Bearer {self._expected_token}"
        if request.headers.get("authorization", "") != expected:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized operator MCP request"},
            )
        return await call_next(request)
