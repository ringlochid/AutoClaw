# Current exact OpenClaw bridge prompt strings

Status: Current appendix

Last verified: 2026-05-12

Legacy filename retained for searchability.

This page no longer preserves a live shipped OpenClaw bridge prompt string,
because the current runtime no longer ships one.

The owner page for the current prompt-delivery contract is
`prompt-layer-and-worker-delivery.md`.

## Current truth

The current shipped prompt source is split across:

- exact static block assets in `apps/api/app/runtime/prompt/assets/blocks/*.txt`
- the asset catalog in `apps/api/app/runtime/prompt/assets/catalog.json`
- dynamic instruction assembly in `apps/api/app/runtime/prompt/instructions.py`
- dynamic section assembly in `apps/api/app/runtime/prompt/sections/rendering.py`
- full prompt persistence in `_runtime/dispatch/<dispatch_id>/prompt.md`
- persisted transport request in `_runtime/dispatch/<dispatch_id>/prompt-request.json`

There is no current manifest-ack bootstrap string, no current bundle-read
envelope, and no single bridge-only text block that replaces the older
OpenClaw prompt pages 1:1.

## Compatibility note

There is no remaining `app.runtime.prompt_assets` compatibility package in the
current tree.

Do not treat old `prompt_assets` references from historical docs or stale local
memory as part of the current shipped prompt asset source.

## Verification

- inspected code in `apps/api/app/runtime/prompt/asset_catalog.py`
- inspected code in `apps/api/app/runtime/prompt/instructions.py`
- inspected code in `apps/api/app/runtime/prompt/sections/rendering.py`
- inspected code in `apps/api/app/runtime/prompt/bundle.py`
- inspected code in `apps/api/app/runtime/projection/dispatch/prompt.py`
- inspected code in `apps/api/app/runtime/task_root/paths.py`
- inspected tests in `apps/api/tests/unit/runtime_prompt_rendering/test_smoke.py`

## Target contrast note

The redesign target still treats exact prompt blocks as shipped app-owned text
assets plus mirrored docs, but the current live package path is
`apps/api/app/runtime/prompt/assets/**`.
