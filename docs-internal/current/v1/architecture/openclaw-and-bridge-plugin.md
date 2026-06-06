# Current OpenClaw and bridge-plugin baseline

Status: Current

Last verified: 2026-05-23

This page captures the repo-visible current OpenClaw boundary.

The current repo does not ship the older bridge-plugin source tree or the old dedicated bridge transport modules. This page therefore documents the controller-side dispatch, prompt, callback, and mounted MCP contract that the external OpenClaw worker boundary is expected to honor.

## Keywords

- current OpenClaw boundary
- dispatch session binding
- callback lane
- node MCP mount
- explicit-arg node-tool boundary

## Current repo-visible transport boundary

Current delegated dispatch and session truth in this repo lives in these controller-authority and mounted-boundary surfaces:

- `apps/api/src/autoclaw/runtime/dispatch/authority.py`
- `apps/api/src/autoclaw/runtime/dispatch/gateway/__init__.py`
- `apps/api/src/autoclaw/runtime/dispatch/gateway_launch_state.py`
- `apps/api/src/autoclaw/runtime/projection/dispatch/prompt.py`
- `apps/api/src/autoclaw/persistence/models/runtime/dispatch/turns.py`
- `apps/api/src/autoclaw/persistence/models/runtime/dispatch/states.py`
- `apps/api/src/autoclaw/interfaces/http/routers/callback.py`
- `apps/api/src/autoclaw/interfaces/mcp/node/server.py`
- `apps/api/src/autoclaw/main.py`

Current helper/bootstrap narration that does not own controller transport authority lives in:

- `apps/api/src/autoclaw/interfaces/mcp/bindings.py`

Current repo-visible facts:

- the controller prepares and accepts dispatch turns before callback or node-tool writes are legal
- callback HTTP writes use the task-scoped path plus explicit `session_key`
- static `node MCP` writes use explicit `session_key` + `task_id` tool arguments
- callback HTTP and static `node MCP` both validate the same presented `session_key` plus `task_id` against live `NodeSession`, current dispatch, current assignment, and current attempt truth
- `bindings.py` is helper glue that derives dispatch-local node-tool context for local wrapper bootstrap and prompt teaching after controller truth already exists; it does not validate writes or define the callback or mounted `node MCP` authority contract
- prompt bundles and persisted transport-request artifacts are materialized under `_runtime/dispatch/<dispatch_id>/`
- dispatch, node-session, delivery-state, continuity-state, watchdog-state, and provider-event rows remain controller truth; prompt files are derived projections

Target contrast:

- current shipped controller truth is implementation truth only
- the target design still wants a cleaner provider, worker, and operator split plus cleaner gateway control surfaces than the current tree exposes locally

## Current callback and plugin lane baseline

The shipped repo proves the callback lane and the mounted MCP wrapper surfaces, not a separate bridge-plugin source tree.

Repo-visible callback HTTP surfaces are:

- `POST /callback/tasks/{task_id}/checkpoint`
- `POST /callback/tasks/{task_id}/boundary`
- `POST /callback/tasks/{task_id}/tools/{tool_name}`

These callback writes require explicit `session_key` input on the request. The current shipped tree does not use a separate callback-binding authority row or hidden callback-only binding secret as the write contract.

Repo-visible static `node MCP` surfaces are mounted under `/node/mcp` when the main app enables MCP mounts and expose:

- `search_definitions(session_key, task_id, ...)`
- `get_definition(session_key, task_id, ...)`
- `record_checkpoint(session_key, task_id, checkpoint)`
- `return_boundary(session_key, task_id, boundary)`
- `assign_child(session_key, task_id, payload, expected_structural_revision_id?)`
- `add_child(session_key, task_id, payload, expected_structural_revision_id?)`
- `update_child(session_key, task_id, payload, expected_structural_revision_id?)`
- `remove_child(session_key, task_id, payload, expected_structural_revision_id?)`
- `release_green(session_key, task_id, expected_structural_revision_id?)`
- `release_blocked(session_key, task_id, expected_structural_revision_id?)`

Current shipped helper note:

- `apps/api/src/autoclaw/interfaces/mcp/bindings.py` loads the current dispatch-local `task_id` and `session_key` for local wrapper bootstrap
- that helper does not validate writes, define mounted tool schemas, or replace the explicit-arg callback or `node MCP` boundary
- `x-session-key` and other hidden-binding paths are not the canonical current v1 `node MCP` interface taught by this tree

Current shipped contrast:

- the mounted node-MCP wrapper surface now preserves the strict typed request and result shapes the runtime expects
- `assign_child`, `add_child`, `update_child`, and `remove_child` each keep their own typed `payload` contract, while `release_green` and `release_blocked` stay payload-free
- node-operation success is surfaced through typed `CheckpointRead`, `BoundaryRead`, `AssignChildSuccess`, `AddChildSuccess`, `UpdateChildSuccess`, `RemoveChildSuccess`, `ReleaseGreenSuccess`, and `ReleaseBlockedSuccess` wrapper contracts
- current contrast remains that this mounted node-MCP surface is implementation truth only, not the design owner surface

That means the current tree locally proves:

- worker, parent, and root writes are session-rooted
- callback HTTP and static `node MCP` share one server-side authority path
- prompt and session continuity are dispatch-bound
- manifest and checkpoint lineage remain controller-owned prompt and runtime truth, not caller-authored write-envelope fields

These are current shipped facts only. They are not the design target if v1 locks the static `node MCP` surface as the canonical external contract rather than as current-tree implementation detail.

The current repo does not contain the old bridge-plugin implementation, so exact plugin capability flags and raw plugin tool inventories are not revalidated here.

## Current prompt-source rule

The current runtime no longer ships one monolithic bridge-only prompt string.

Repo-owned prompt truth is split across:

- exact static blocks in `apps/api/src/autoclaw/runtime/prompt/assets/blocks/*.txt`
- the asset catalog in `apps/api/src/autoclaw/runtime/prompt/assets/catalog.json`
- dynamic prompt assembly in `apps/api/src/autoclaw/runtime/prompt/instructions.py` and `apps/api/src/autoclaw/runtime/prompt/sections/rendering.py`
- persisted dispatch artifacts under `_runtime/dispatch/<dispatch_id>/`

For the current prompt-source owner page, see `../interfaces/current-openclaw-bridge-prompt-strings.md`.

## Evidence

- inspected code in `apps/api/src/autoclaw/runtime/dispatch/authority.py`
- inspected code in `apps/api/src/autoclaw/runtime/dispatch/gateway/__init__.py`
- inspected code in `apps/api/src/autoclaw/runtime/projection/dispatch/prompt.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/dispatch/turns.py`
- inspected code in `apps/api/src/autoclaw/persistence/models/runtime/dispatch/states.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/callback.py`
- inspected code in `apps/api/src/autoclaw/interfaces/mcp/node/server.py`
- inspected code in `apps/api/src/autoclaw/interfaces/mcp/bindings.py` as helper/bootstrap context glue only
- inspected code in `apps/api/src/autoclaw/main.py`
- inspected tests in `apps/api/tests/integration/bootstrap/test_dispatch.py`
- inspected tests in `apps/api/tests/integration/gateway/runtime_dispatch_gateway/test_launch_integration.py`, `apps/api/tests/integration/gateway/runtime_dispatch_gateway/test_cleanup_integration.py`, and `apps/api/tests/integration/gateway/runtime_dispatch_gateway/test_ingest_integration.py`
- inspected tests in `apps/api/tests/integration/mcp/node_server`
- inspected tests in `apps/api/tests/integration/runtime/routes/test_surface_contract.py`

## Safe wording rule

Current docs must not imply that the old bridge-plugin repository is present in this tree.

Current docs must not imply that prompt files or dispatch observability files outrank controller-owned dispatch, node-session, or manifest rows.

Current docs must not imply that a separate callback-binding table still owns callback authority in the shipped tree.

Current docs must not imply that `apps/api/src/autoclaw/interfaces/mcp/bindings.py` owns controller transport authority; it is helper glue for dispatch-local tool context only.

## Design pointer

For the target OpenClaw-first provider, worker, and operator split, see [Provider, worker, and operator boundary](../../../design/v1/architecture/provider-worker-and-operator-boundary.md), [OpenClaw worker and gateway contract](../../../design/v1/architecture/openclaw-worker-and-gateway-contract.md), [Plugin tool reference](../../../design/v1/interfaces/plugin-tool-reference.md), and [Guarded registry and runtime writes](../../../design/v1/interfaces/guarded-registry-and-runtime-writes.md).

For the current manifest model, see [Current workflow-manifest projection](manifest-projection-and-acknowledgement.md).
