from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict

PROMPT_ASSET_PACKAGE = "app.runtime.prompt.assets"
PROMPT_ASSET_CATALOG = "catalog.json"


class ExactPromptBlockAsset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    asset_path: str
    mirror_doc: str


def _read_prompt_asset_catalog_payload() -> dict[str, Any]:
    catalog_path = files(PROMPT_ASSET_PACKAGE).joinpath(PROMPT_ASSET_CATALOG)
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("prompt asset catalog must be a mapping")
    return payload


@cache
def list_exact_prompt_block_assets() -> tuple[ExactPromptBlockAsset, ...]:
    payload = _read_prompt_asset_catalog_payload()
    blocks = payload.get("blocks")
    if not isinstance(blocks, list):
        raise ValueError("prompt asset catalog blocks must be a list")
    return tuple(ExactPromptBlockAsset.model_validate(block) for block in blocks)


@cache
def _exact_prompt_block_asset_index() -> dict[str, ExactPromptBlockAsset]:
    return {block.id: block for block in list_exact_prompt_block_assets()}


def get_exact_prompt_block_asset(block_id: str) -> ExactPromptBlockAsset:
    try:
        return _exact_prompt_block_asset_index()[block_id]
    except KeyError as exc:
        raise ValueError(f"unknown exact prompt block `{block_id}`") from exc


@cache
def load_exact_prompt_block(block_id: str) -> str:
    asset = get_exact_prompt_block_asset(block_id)
    asset_path = files(PROMPT_ASSET_PACKAGE).joinpath(*PurePosixPath(asset.asset_path).parts)
    return asset_path.read_text(encoding="utf-8").strip()
