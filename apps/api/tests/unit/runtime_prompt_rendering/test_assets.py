from __future__ import annotations

import importlib
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
PROMPT_ASSET_ROOT = REPO_ROOT / "apps" / "api" / "app" / "runtime" / "prompt" / "assets"
PROMPT_LAYER_ROOT = REPO_ROOT / "docs" / "redesign" / "prompt-layer"


class ExactPromptBlockAssetLike(Protocol):
    id: str
    asset_path: str
    mirror_doc: str


GetExactPromptBlockAsset = Callable[[str], ExactPromptBlockAssetLike]
ListExactPromptBlockAssets = Callable[[], tuple[ExactPromptBlockAssetLike, ...]]
LoadExactPromptBlock = Callable[[str], str]


def _load_asset_catalog_functions() -> tuple[
    ListExactPromptBlockAssets,
    GetExactPromptBlockAsset,
    LoadExactPromptBlock,
]:
    module = cast(Any, importlib.import_module("app.runtime.prompt.asset_catalog"))
    return (
        cast(ListExactPromptBlockAssets, module.list_exact_prompt_block_assets),
        cast(GetExactPromptBlockAsset, module.get_exact_prompt_block_asset),
        cast(LoadExactPromptBlock, module.load_exact_prompt_block),
    )


list_exact_prompt_block_assets, get_exact_prompt_block_asset, load_exact_prompt_block = (
    _load_asset_catalog_functions()
)


def extract_exact_block_text_from_mirror_doc(path: Path, block_id: str) -> str:
    heading = f"## `{block_id}`"
    mirror_text = path.read_text(encoding="utf-8")
    if heading not in mirror_text:
        raise ValueError(f"missing exact block heading {block_id} in {path}")
    code_block_match = re.search(
        r"```text\r?\n(.*?)^```",
        mirror_text.split(heading, maxsplit=1)[1],
        re.MULTILINE | re.DOTALL,
    )
    if code_block_match is None:
        raise ValueError(f"missing exact block code fence {block_id} in {path}")
    return code_block_match.group(1)


@pytest.mark.parametrize(
    "asset",
    list_exact_prompt_block_assets(),
    ids=lambda asset: asset.id,
)
def test_load_exact_prompt_block_matches_packaged_asset_bytes(
    asset: ExactPromptBlockAssetLike,
) -> None:
    expected_text = (PROMPT_ASSET_ROOT / asset.asset_path).read_bytes().decode("utf-8")

    assert load_exact_prompt_block(asset.id) == expected_text


def test_load_exact_prompt_block_preserves_trailing_newline() -> None:
    asset = get_exact_prompt_block_asset("autoclaw_system_block_v1")

    assert load_exact_prompt_block(asset.id).endswith("\n")


@pytest.mark.parametrize(
    "asset",
    list_exact_prompt_block_assets(),
    ids=lambda asset: asset.id,
)
def test_exact_prompt_block_mirror_matches_asset_bytes(
    asset: ExactPromptBlockAssetLike,
) -> None:
    mirror_text = extract_exact_block_text_from_mirror_doc(
        PROMPT_LAYER_ROOT / asset.mirror_doc,
        asset.id,
    )
    expected_text = (PROMPT_ASSET_ROOT / asset.asset_path).read_bytes().decode("utf-8")

    assert mirror_text == expected_text
