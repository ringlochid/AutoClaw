from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.errors import ConflictError
from app.runtime.callback_bindings import CallbackBindingInput, extract_callback_binding


class _Payload:
    def __init__(
        self,
        *,
        manifest_id: object = None,
        manifest_hash: object = None,
        node_session_key: object = None,
        ack_checkpoint_id: object = None,
    ) -> None:
        self.manifest_id = manifest_id
        self.manifest_hash = manifest_hash
        self.node_session_key = node_session_key
        self.ack_checkpoint_id = ack_checkpoint_id


def test_extract_callback_binding_returns_none_when_optional_and_missing() -> None:
    payload = _Payload()

    assert extract_callback_binding(payload, required=False, operation="Approval callback") is None


def test_extract_callback_binding_raises_when_required_and_missing() -> None:
    payload = _Payload()

    with pytest.raises(ConflictError) as exc_info:
        extract_callback_binding(payload, required=True, operation="Checkpoint callback")

    assert "Checkpoint callback requires manifest, session, and ack lineage binding" in str(
        exc_info.value
    )


def test_extract_callback_binding_raises_on_partial_binding() -> None:
    payload = _Payload(manifest_id=uuid4(), manifest_hash="hash-only")

    with pytest.raises(ConflictError) as exc_info:
        extract_callback_binding(payload, required=False, operation="Replan callback")

    assert "Replan callback requires manifest, session, and ack lineage binding" in str(
        exc_info.value
    )


def test_extract_callback_binding_returns_typed_binding() -> None:
    binding = extract_callback_binding(
        _Payload(
            manifest_id=uuid4(),
            manifest_hash="manifest-hash",
            node_session_key="session-key",
            ack_checkpoint_id=uuid4(),
        ),
        required=False,
        operation="Approval callback",
    )

    assert isinstance(binding, CallbackBindingInput)
    assert binding.manifest_hash == "manifest-hash"
    assert binding.node_session_key == "session-key"
