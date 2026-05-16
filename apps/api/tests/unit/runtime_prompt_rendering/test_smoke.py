from __future__ import annotations

from pathlib import Path

from app.runtime import PromptSendMode
from app.runtime.prompt.bundle import render_prompt_bundle

from .samples import (
    parent_request,
    worker_request,
)


def test_worker_prompt_rendering_smoke(tmp_path: Path) -> None:
    bundle = render_prompt_bundle(worker_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT))

    assert bundle.instructions_text is not None
    assert "## Current Assignment" in bundle.full_markdown
    assert "## Allowed Actions Now" in bundle.full_markdown


def test_parent_prompt_rendering_smoke(tmp_path: Path) -> None:
    bundle = render_prompt_bundle(parent_request(tmp_path, send_mode=PromptSendMode.FULL_PROMPT))

    assert bundle.instructions_text is not None
    assert "## Current Dispatch" in bundle.input_text
    assert "## Operating Model" in bundle.input_text
