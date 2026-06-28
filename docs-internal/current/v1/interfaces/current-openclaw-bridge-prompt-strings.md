# Current exact OpenClaw bridge prompt strings

Status: Current

Last verified: 2026-05-13

Legacy filename retained for searchability.

This page no longer preserves a live shipped OpenClaw bridge prompt string, because the current runtime no longer ships one.

The owner page for the current prompt-delivery contract is [Prompt Layer And Worker Delivery](prompt-layer-and-worker-delivery.md).

## Current truth

The current shipped prompt source is split across:

- exact static block assets in `apps/api/src/autoclaw/runtime/prompt/assets/blocks/*.md`
- the asset catalog in `apps/api/src/autoclaw/runtime/prompt/assets/catalog.json`
- dynamic instruction assembly in `apps/api/src/autoclaw/runtime/prompt/instructions.py`
- dynamic section assembly in `apps/api/src/autoclaw/runtime/prompt/sections/rendering.py`
- full prompt persistence in `_runtime/dispatch/<dispatch_id>/prompt.md`
- persisted transport request in `_runtime/dispatch/<dispatch_id>/prompt-request.json`

Those dynamic layers now surface the live manifest/prompt payload split rather than one bridge-only string:

- `manifest_version` and the stable manifest path come from the persisted workflow manifest
- top-level `structural_edit_palette` comes from the manifest payload and is rendered for parent/root structural-edit turns
- current node `policy` guidance is rendered in the dynamic instruction block
- `latest_relevant_checkpoint_path` is a dedicated handoff field rendered into checkpoint context instead of being reconstructed from a monolithic bridge string

There is no current manifest-ack bootstrap string, no current bundle-read envelope, and no single bridge-only text block that replaces the older OpenClaw prompt pages 1:1.

## Compatibility note

There is no remaining `app.runtime.prompt_assets` compatibility package in the current tree.

Do not treat old `prompt_assets` references from historical docs or stale local memory as part of the current shipped prompt asset source.

## Verification

- inspected code in `apps/api/src/autoclaw/runtime/prompt/asset_catalog.py`
- inspected code in `apps/api/src/autoclaw/runtime/prompt/instructions.py`
- inspected code in `apps/api/src/autoclaw/runtime/prompt/sections/rendering.py`
- inspected code in `apps/api/src/autoclaw/runtime/prompt/bundle.py`
- inspected code in `apps/api/src/autoclaw/runtime/projection/dispatch/prompt.py`
- inspected code in `apps/api/src/autoclaw/runtime/task_root/paths.py`
- inspected tests in `apps/api/tests/unit/runtime_prompt_rendering/test_smoke.py`

## Target contrast note

The design target still treats exact prompt blocks as shipped app-owned text assets plus mirrored docs, but the current live package path is `apps/api/src/autoclaw/runtime/prompt/assets/**`.
