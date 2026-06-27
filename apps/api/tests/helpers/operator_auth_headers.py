DEFAULT_OPERATOR_ACTOR_REF = "operator.test"


def current_operator_headers(
    *,
    actor_ref: str = DEFAULT_OPERATOR_ACTOR_REF,
) -> dict[str, str]:
    return {
        "X-AutoClaw-API-Key": "api-test-key",
        "X-AutoClaw-Actor-Ref": actor_ref,
    }


def seeded_runtime_headers(
    _task_id: str,
    *,
    actor_ref: str = DEFAULT_OPERATOR_ACTOR_REF,
) -> dict[str, str]:
    return current_operator_headers(actor_ref=actor_ref)


OPERATOR_HEADERS = current_operator_headers()


__all__ = [
    "DEFAULT_OPERATOR_ACTOR_REF",
    "OPERATOR_HEADERS",
    "current_operator_headers",
    "seeded_runtime_headers",
]
