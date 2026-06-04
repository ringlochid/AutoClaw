"""Temporary Phase 6 shims for the legacy runtime prompt owners."""

from __future__ import annotations

from app.runtime.prompt import (
    ExactPromptBlockAsset,
    get_exact_prompt_block_asset,
    list_exact_prompt_block_assets,
    load_exact_prompt_block,
    render_prompt_bundle,
    render_prompt_instructions,
    render_prompt_sections,
)

__all__ = [
    "ExactPromptBlockAsset",
    "get_exact_prompt_block_asset",
    "list_exact_prompt_block_assets",
    "load_exact_prompt_block",
    "render_prompt_bundle",
    "render_prompt_instructions",
    "render_prompt_sections",
]
