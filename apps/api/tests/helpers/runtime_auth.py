def current_operator_headers() -> dict[str, str]:
    return {
        "X-AutoClaw-API-Key": "api-test-key",
    }


OPERATOR_HEADERS = current_operator_headers()


__all__ = ["OPERATOR_HEADERS", "current_operator_headers"]
