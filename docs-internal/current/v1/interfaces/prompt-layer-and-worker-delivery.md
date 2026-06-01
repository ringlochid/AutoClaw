# Current prompt delivery and persisted request

Status: Current

Last verified: 2026-05-13

This page owns the current prompt-delivery shape for the shipped runtime:

- exact prompt block assets
- dynamic instruction and section rendering
- persisted dispatch prompt artifacts

It is the canonical current prompt-delivery contract page. It is contrast-only and does not redefine the design target prompt canon.

For the legacy filename that used to track OpenClaw bridge strings, see `current-openclaw-bridge-prompt-strings.md`.

## Ownership map

Current prompt-related ownership is:

| Concern                    | Current owner |
| -------------------------- | ------------- |
| exact static block bytes   | `apps/api/app/runtime/prompt/assets/**` via `app.runtime.prompt.assets`, loaded byte-for-byte |
| block catalog              | `apps/api/app/runtime/prompt/assets/catalog.json` and `prompt/asset_catalog.py` |
| instruction assembly       | `apps/api/app/runtime/prompt/instructions.py::render_prompt_instructions()` |
| markdown section assembly  | `apps/api/app/runtime/prompt/sections/rendering.py::render_prompt_sections()` |
| prompt rendering and hash  | `apps/api/app/runtime/prompt/bundle.py::render_prompt_bundle()` |
| persisted prompt artifact  | `apps/api/app/runtime/projection/dispatch/prompt.py::render_dispatch_prompt()` plus `apps/api/app/runtime/projection/dispatch/materialization.py::materialize_dispatch_files()` as the synchronous dispatch projection writer |
| prompt artifact path       | `apps/api/app/runtime/task_root/paths.py::prompt_markdown_path()` |
| persisted transport request path | `apps/api/app/runtime/task_root/paths.py::prompt_request_json_path()` |

This page owns the current shipped prompt source map only. It does not define the design target prompt canon.

## Current shape

Current prompt delivery is a rendered prompt plus persisted transport-request split, not an OpenClaw bridge envelope.

Each dispatch render is built from:

- `PromptRenderRequest`
- exact static block assets
- dynamic node/task/manifest/assignment/checkpoint sections

Each render returns:

- `instructions_text`
- `input_text`
- `full_markdown`
- `content_hash`

The full markdown prompt artifact is persisted to:

- `_runtime/dispatch/<dispatch_id>/prompt.md`

The persisted transport request envelope is persisted separately to:

- `_runtime/dispatch/<dispatch_id>/prompt-request.json`

## Current prompt families

Current prompt families are:

- `worker_dispatch_prompt`
- `parent_root_dispatch_prompt`

Current send modes are:

- `full_prompt`

Current shipped launch and continue paths open real dispatches as `full_prompt` only. The old `same_session_continue` renderer and persisted-request residue has been removed from the shipped prompt/runtime path. The Phase 2 target keeps the same prompt content contract but writes the dispatch-local prompt artifact through synchronous task-root helpers after commit instead of teaching a queued refresh as the normal model.

## Current section contract

Current rendered markdown sections are ordered as:

1. `Operating Model`
2. `Task Identity`
3. `Node Purpose`
4. `Current Dispatch`
5. `Workflow Manifest`
6. `Current Assignment`
7. `Latest Checkpoint Context`
8. `Consumed Durable Refs` when present
9. `Transient Refs` when present
10. `Task Memory` when present
11. `Allowed Actions Now`
12. `Publication Rule`

Current manifest-backed prompt inputs now rely on these live manifest payload fields:

- `manifest_version`
- top-level `structural_edit_palette`
- `current_context.latest_checkpoint_path`
- `current_context.latest_relevant_checkpoint_path`
- per-node `policy` when one exists in workflow truth

Current shipped checkpoint-handoff split is:

- `latest_checkpoint_path` remains the current attempt's own checkpoint path when one exists
- `latest_relevant_checkpoint_path` is optional and carries the parent/root redispatch handoff checkpoint when that differs
- prompt rendering reads that dedicated field directly and does not infer a handoff checkpoint by scanning surfaced refs in list order
- dispatch-scoped renders use the explicit controller-selected handoff already projected onto the current dispatch
- stable-manifest renders without an open dispatch reuse the most recent controller-selected handoff for the same attempt when one exists; prompt rendering still consumes the projected field directly rather than inferring checkpoint context from surfaced-ref order
- `Latest Checkpoint Context` renders from `latest_relevant_checkpoint_path` when present, otherwise from `latest_checkpoint_path`

Current instruction text is assembled from:

- system block
- provider continuity block
- parent/worker split block
- runtime boundary block
- runtime legality block for the current node kind
- dynamic node guidance lines, including current node policy guidance when present and the compact structural-edit palette for parent/root turns

## Current task-root inputs

Prompt rendering reads current runtime projections and refs such as:

- `_runtime/workflow-manifest.md`
- the manifest payload fields `manifest_version`, `structural_edit_palette`, and per-node `policy` rendered through that stable manifest and the dynamic node-guidance block
- `_runtime/attempts/<attempt_id>/assignment.md`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md` for the current attempt when present
- a surfaced `latest_relevant_checkpoint_path` when controller-selected parent/root redispatch truth needs a different durable handoff
- exact current child artifact refs resolved from controller-owned current pointers when the current parent/root turn depends on child durable evidence
- controller-staged descendant checkpoint and artifact refs when a parent/root release reread depends on evidence beyond the current direct-child set
- current criteria, artifact, checkpoint, wiki, doc, and transient refs carried in assignment or checkpoint projections
- localized external surfaced files under `tmp/transfers/localized/` when runtime imported them from outside the task root

Observability projections such as:

- `_runtime/dispatch/<dispatch_id>/delivery-state.json`
- `_runtime/dispatch/<dispatch_id>/continuity-state.json`
- `_runtime/dispatch/<dispatch_id>/watchdog-state.json`
- `_runtime/dispatch/<dispatch_id>/provider-events.ndjson`

are controller-generated runtime projections. They are not prompt source or runtime truth by themselves.

This page does not treat `delivery-state.json` as the owner of prompt legality or controller control-state meaning. Its role here is observability only.

## Current limits

- current code does not ship a monolithic OpenClaw bridge prompt string
- current code does not ship the older manifest-ack callback step
- current code does not ship the older bundle-read route
- current exact static block source of truth is `apps/api/app/runtime/prompt/assets/**`
- current dynamic prompt assembly still lives in `apps/api/app/runtime/prompt/instructions.py`, `apps/api/app/runtime/prompt/sections/*.py`, and `apps/api/app/runtime/prompt/bundle.py`
- there is no remaining `app.runtime.prompt_assets` compatibility package in the current tree

## Evidence

- inspected code in `apps/api/app/runtime/prompt/asset_catalog.py`
- inspected code in `apps/api/app/runtime/prompt/instructions.py`
- inspected code in `apps/api/app/runtime/prompt/sections/rendering.py`
- inspected code in `apps/api/app/runtime/prompt/bundle.py`
- inspected code in `apps/api/app/runtime/projection/dispatch/prompt.py`
- inspected code in `apps/api/app/runtime/projection/dispatch/materialization.py`
- inspected code in `apps/api/app/runtime/task_root/paths.py`
- inspected tests in `apps/api/tests/unit/runtime_prompt_rendering/test_smoke.py`
- inspected tests in `apps/api/tests/unit/runtime_prompt_rendering/test_dispatch.py`
- inspected tests in `apps/api/tests/integration/phase2/bootstrap/test_dispatch.py`
