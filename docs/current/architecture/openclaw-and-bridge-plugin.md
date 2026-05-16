# Current OpenClaw and bridge-plugin baseline

Status: Current

Last verified: 2026-05-12

This page captures the repo-visible current OpenClaw boundary.

The current repo does not ship the older bridge-plugin source tree or the old
dedicated bridge transport modules. This page therefore documents the
controller-side dispatch, prompt, and callback contract that the external
OpenClaw worker boundary is expected to honor.

## Keywords

- current OpenClaw boundary
- dispatch session binding
- callback lane
- prompt bundle persistence
- controller-owned transport truth

## Current repo-visible transport boundary

Current delegated dispatch/session truth in this repo lives in:

- `apps/api/app/runtime/control/dispatch/opening.py`
- `apps/api/app/runtime/projection/dispatch/prompt.py`
- `apps/api/app/db/models/runtime/dispatch/turns.py`
- `apps/api/app/db/models/runtime/dispatch/states.py`
- `apps/api/app/api/routes/callback.py`

Current repo-visible facts:

- the controller prepares and accepts dispatch turns before callback writes are
  legal
- callback access is bound to a live dispatch session key plus current
  assignment and attempt lineage
- prompt bundles and persisted transport-request artifacts are materialized
  under `_runtime/dispatch/<dispatch_id>/`
- manifest, dispatch, and callback-binding rows remain controller truth;
  prompt files are derived projections

Target contrast:

- current shipped controller truth is implementation truth only
- the target redesign still wants a cleaner provider/worker/operator split and
  cleaner gateway control surfaces than the current tree exposes locally

## Current callback and plugin lane baseline

The shipped repo proves the callback lane, not a repo-local plugin source
tree.

Repo-visible callback surfaces are:

- `POST /callback/tasks/{task_id}/checkpoint`
- `POST /callback/tasks/{task_id}/boundary`
- `POST /callback/tasks/{task_id}/tools/{tool_name}`

That means the current tree locally proves:

- worker, parent, and root writes are callback-bound
- prompt/session continuity is dispatch-bound
- manifest acknowledgement and checkpoint lineage remain controller-owned

These are current shipped facts only. They are not the redesign target if v1
locks a static `node MCP` surface with explicit `session_key` + `task_id` tool
arguments instead of header-bound or plugin/harness-bound node authority.

The current repo does not contain the old bridge-plugin implementation, so
exact plugin capability flags and raw plugin tool inventories are not
revalidated here.

## Current prompt-source rule

The current runtime no longer ships one monolithic bridge-only prompt string.

Repo-owned prompt truth is split across:

- exact static blocks in `apps/api/app/runtime/prompt/assets/blocks/*.txt`
- the asset catalog in `apps/api/app/runtime/prompt/assets/catalog.json`
- dynamic prompt assembly in `apps/api/app/runtime/prompt/instructions.py`
  and `apps/api/app/runtime/prompt/sections/rendering.py`
- persisted dispatch artifacts under `_runtime/dispatch/<dispatch_id>/`

For the current prompt-source owner page, see
`../interfaces/current-openclaw-bridge-prompt-strings.md`.

## Evidence

Inspected code:

- `apps/api/app/runtime/control/dispatch/opening.py`
- `apps/api/app/runtime/projection/dispatch/prompt.py`
- `apps/api/app/db/models/runtime/dispatch/turns.py`
- `apps/api/app/db/models/runtime/dispatch/states.py`
- `apps/api/app/api/routes/callback.py`
- `apps/api/tests/integration/phase2/bootstrap/test_dispatch.py`
- `apps/api/tests/integration/phase3/routes/test_surface_contract.py`

## Safe wording rule

Current docs must not imply that the old bridge-plugin repository is present in
this tree.

Current docs must not imply that prompt files or dispatch observability files
outrank controller-owned dispatch, callback-binding, or manifest rows.

## Redesign pointer

For the target OpenClaw-first provider/worker/operator split, see [Provider,
worker, and operator boundary](../../redesign/architecture/provider-worker-and-operator-boundary.md),
[OpenClaw worker and gateway contract](../../redesign/architecture/openclaw-worker-and-gateway-contract.md),
[Plugin tool reference](../../redesign/interfaces/plugin-tool-reference.md), and
[Guarded registry and runtime writes](../../redesign/interfaces/guarded-registry-and-runtime-writes.md).

For the current manifest model, see
[Manifest projection and acknowledgement](manifest-projection-and-acknowledgement.md).
