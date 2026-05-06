# Current prompt delivery and dispatch bundle

Status: Current

Last verified: 2026-05-05

This page owns the current prompt-delivery shape for the shipped runtime:

- exact prompt block assets
- dynamic instruction and section rendering
- persisted dispatch prompt artifacts

It is the canonical current prompt-delivery contract page.

For the legacy filename that used to track OpenClaw bridge strings, see
`current-openclaw-bridge-prompt-strings.md`.

## Ownership map

Current prompt-related ownership is:

| Concern                    | Current owner |
| -------------------------- | ------------- |
| exact static block bytes   | `apps/api/app/runtime/prompt/assets/**` via `app.runtime.prompt.assets` |
| block catalog              | `apps/api/app/runtime/prompt/assets/catalog.json` and `prompt/asset_catalog.py` |
| instruction assembly       | `apps/api/app/runtime/prompt/instructions.py::render_prompt_instructions()` |
| markdown section assembly  | `apps/api/app/runtime/prompt/sections.py::render_prompt_sections()` |
| bundle rendering and hash  | `apps/api/app/runtime/prompt/bundle.py::render_prompt_bundle()` |
| persisted prompt artifact  | `apps/api/app/runtime/projection/materialize.py::build_dispatch_prompt()` and `render_dispatch_prompt()` |
| prompt artifact path       | `apps/api/app/runtime/resources.py::prompt_markdown_path()` |
| persisted transport request | `apps/api/app/runtime/resources.py::prompt_request_json_path()` |

This page owns the current shipped prompt source map only. It does not define
the redesign target prompt canon.

## Current shape

Current prompt delivery is a rendered prompt bundle, not an OpenClaw bridge
envelope.

Each dispatch render is built from:

- `PromptRenderRequest`
- exact static block assets
- dynamic node/task/manifest/assignment/checkpoint sections

Each render returns:

- `instructions_text`
- `input_text`
- `full_markdown`
- `content_hash`

The full markdown prompt is persisted to:

- `_runtime/dispatch/<dispatch_id>/prompt.md`
- `_runtime/dispatch/<dispatch_id>/prompt-request.json`

## Current prompt families

Current prompt families are:

- `worker_dispatch_prompt`
- `parent_root_dispatch_prompt`

Current send modes are:

- `full_prompt`
- `same_session_continue`

`same_session_continue` still renders the full prompt for persistence, but the
transport-facing `input_text` omits the static sections
`Operating Model`, `Task Identity`, and `Node Purpose`.

Current shipped launch and continue paths still open real dispatches as
`full_prompt`. On the current tree, `same_session_continue` is proven only at
the renderer and persisted transport-request layer when continuity state already
supplies a `previous_response_id`; it is not current proof that dispatch
opening selects that send mode automatically.

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

Current instruction text is assembled from:

- system block
- provider continuity block
- parent/worker split block
- runtime boundary block
- runtime legality block for the current node kind
- dynamic node guidance lines

## Current task-root inputs

Prompt rendering reads current runtime projections and refs such as:

- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.md`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md` when present
- current criteria, artifact, checkpoint, wiki, doc, and transient refs carried
  in assignment or checkpoint projections

Observability projections such as:

- `_runtime/dispatch/<dispatch_id>/delivery-state.json`
- `_runtime/dispatch/<dispatch_id>/continuity-state.json`
- `_runtime/dispatch/<dispatch_id>/watchdog-state.json`
- `_runtime/dispatch/<dispatch_id>/provider-events.ndjson`

are controller-generated runtime projections. They are not prompt source or
runtime truth by themselves.

## Current limits

- current code does not ship a monolithic OpenClaw bridge prompt string
- current code does not ship the older manifest-ack callback step
- current code does not ship the older bundle-read route
- current prompt source of truth is `apps/api/app/runtime/prompt/assets/**`
- there is no remaining `app.runtime.prompt_assets` compatibility package in
  the current tree

## Evidence

- inspected code in `apps/api/app/runtime/prompt/asset_catalog.py`
- inspected code in `apps/api/app/runtime/prompt/instructions.py`
- inspected code in `apps/api/app/runtime/prompt/sections.py`
- inspected code in `apps/api/app/runtime/prompt/bundle.py`
- inspected code in `apps/api/app/runtime/projection/materialize.py`
- inspected code in `apps/api/app/runtime/resources.py`
- inspected tests in `apps/api/tests/unit/test_runtime_prompt_rendering.py`
- inspected tests in `apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
