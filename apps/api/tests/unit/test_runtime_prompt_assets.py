from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
PROMPT_ASSET_ROOT = REPO_ROOT / "apps" / "api" / "app" / "runtime" / "prompt" / "assets"
PROMPT_LAYER_ROOT = REPO_ROOT / "docs" / "redesign" / "prompt-layer"
ASSET_CATALOG_PATH = REPO_ROOT / "apps" / "api" / "app" / "runtime" / "prompt" / "asset_catalog.py"
PROMPT_CATALOG_TOOLS_PATH = REPO_ROOT / "scripts" / "docs" / "prompt_catalog_tools.py"


class ExactPromptBlockAssetLike(Protocol):
    id: str
    asset_path: str
    mirror_doc: str


ExtractExactBlockText = Callable[[Path, str], str]
GetExactPromptBlockAsset = Callable[[str], ExactPromptBlockAssetLike]
ListExactPromptBlockAssets = Callable[[], tuple[ExactPromptBlockAssetLike, ...]]
LoadExactPromptBlock = Callable[[str], str]


def _load_module(module_name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_asset_catalog_functions() -> tuple[
    ListExactPromptBlockAssets,
    GetExactPromptBlockAsset,
    LoadExactPromptBlock,
]:
    module = cast(Any, _load_module("runtime_prompt_asset_catalog_test", ASSET_CATALOG_PATH))
    return (
        cast(ListExactPromptBlockAssets, module.list_exact_prompt_block_assets),
        cast(GetExactPromptBlockAsset, module.get_exact_prompt_block_asset),
        cast(LoadExactPromptBlock, module.load_exact_prompt_block),
    )


def _load_exact_mirror_extractor() -> ExtractExactBlockText:
    module = cast(Any, _load_module("prompt_catalog_tools_test", PROMPT_CATALOG_TOOLS_PATH))
    return cast(ExtractExactBlockText, module._extract_exact_block_text_from_mirror_doc)


list_exact_prompt_block_assets, get_exact_prompt_block_asset, load_exact_prompt_block = (
    _load_asset_catalog_functions()
)
extract_exact_block_text_from_mirror_doc = _load_exact_mirror_extractor()


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
